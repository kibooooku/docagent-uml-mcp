"""Deterministic architecture tests; these do not measure LLM answer quality."""

import asyncio
import copy

import pytest

from docagent.core import (
    Event,
    EventBus,
    EvidenceGate,
    GuardedGateway,
    MemoryStore,
    TaskState,
    ToolBudgetExceeded,
    ToolExecutionError,
    WorkflowEngine,
    transition_state,
)


def evidence(text="Release requires two approvals.", **overrides):
    return {
        "id": "atlas:text:release", "doc_id": "atlas", "page": 2,
        "section_id": "release", "text": text, "source_type": "text", **overrides,
    }


def answer(text="Two approvals are required.", citation=None):
    return {"answer": text, "evidence": [citation or evidence()], "status": "answered"}


def review(draft, verdict="accept", candidate=None):
    return {
        "verdict": verdict, "answer": copy.deepcopy(draft),
        "reason": "The release rule states two approvals.", "memory_candidate": candidate,
    }


class SourceGateway:
    def __init__(self):
        self.calls = []
        self.source = evidence()

    async def list_tools(self):
        return [{"name": "get_section_content", "inputSchema": {"type": "object"}}]

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        if arguments.get("doc_id") != "atlas" or arguments.get("section_id", "release") != "release":
            raise ValueError("Unknown document or section")
        return {"evidence": [copy.deepcopy(self.source)]}


async def actor(question, doc_id, tools, memory):
    return answer()


async def reviewer(question, doc_id, draft, tools):
    return review(draft)


@pytest.mark.asyncio
async def test_event_bus_delivery_is_queue_driven_and_deduplicated():
    bus = EventBus()
    delivered = []

    async def listener(event):
        delivered.append(event.type)
        if event.type == "submitted":
            bus.publish(Event("finished", "t", "completed"))

    bus.subscribe("submitted", listener)
    bus.subscribe("finished", listener)
    event = Event("submitted", "t", "pending", payload={"draft": "PRIVATE DRAFT"})
    assert bus.publish(event)
    assert not bus.publish(event)
    assert delivered == []  # Recording the event does not execute the listener.
    bus.start()
    await asyncio.wait_for(bus.wait_idle(), timeout=1)
    await bus.close()
    assert delivered == ["submitted", "finished"]
    assert bus.duplicates == 1
    assert "PRIVATE DRAFT" not in str(bus.events)


@pytest.mark.parametrize("current,target", [
    (TaskState.PENDING, TaskState.COMPLETED),
    (TaskState.ACTING, TaskState.VALIDATING),
    (TaskState.COMPLETED, TaskState.ACTING),
    (TaskState.CANCELLED, TaskState.COMPLETED),
])
def test_state_machine_rejects_impossible_or_terminal_transitions(current, target):
    with pytest.raises(ValueError, match="Invalid task transition"):
        transition_state(current, target)


@pytest.mark.asyncio
async def test_retries_count_physical_attempts_and_obey_budget():
    class Flaky(SourceGateway):
        async def call(self, name, arguments):
            self.calls.append((name, arguments))
            if len(self.calls) == 1:
                raise ConnectionError("Transient failure")
            return {"evidence": [evidence()]}

    source = Flaky()
    tools = GuardedGateway(source, max_calls=2, max_retries=2)
    result = await tools.call("search", {"doc_id": "atlas", "keyword": "release"})
    assert result["evidence"]
    assert tools.metrics["tool_calls"] == 2
    assert tools.metrics["retries"] == 1
    with pytest.raises(ToolBudgetExceeded):
        await tools.call("search", {"doc_id": "atlas", "keyword": "another"})
    assert len(source.calls) == 2
    await tools.close()


@pytest.mark.asyncio
async def test_timeout_is_bounded_and_cancels_underlying_call():
    cancelled = []

    class Slow(SourceGateway):
        async def call(self, name, arguments):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(True)

    tools = GuardedGateway(Slow(), timeout=0.01, max_retries=1)
    with pytest.raises(ToolExecutionError, match="2 attempt"):
        await tools.call("search", {"doc_id": "atlas", "keyword": "release"})
    assert len(cancelled) == 2
    assert tools.metrics["tool_timeouts"] == 2
    assert tools.metrics["retries"] == 1
    await tools.close()


@pytest.mark.asyncio
async def test_validation_errors_are_not_retried_and_unknown_tools_rejected():
    tools = GuardedGateway(SourceGateway(), max_retries=3)
    with pytest.raises(ValueError):
        await tools.call("get_section_content", {"doc_id": "missing", "section_id": "release"})
    assert tools.metrics["tool_calls"] == 1
    assert tools.metrics["retries"] == 0
    with pytest.raises(ValueError, match="allowed read-only"):
        await tools.call("delete_document", {"doc_id": "atlas"})
    assert tools.metrics["tool_calls"] == 1
    await tools.close()


@pytest.mark.asyncio
async def test_identical_reads_coalesce_but_independent_reads_run_concurrently():
    both_started = asyncio.Event()
    active = 0

    class Concurrent(SourceGateway):
        async def call(self, name, arguments):
            nonlocal active
            self.calls.append((name, arguments))
            active += 1
            if active == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=1)
            return {"evidence": [evidence()]}

    source = Concurrent()
    tools = GuardedGateway(source)
    first = {"doc_id": "atlas", "keyword": "release"}
    second = {"doc_id": "atlas", "keyword": "approval"}
    results = await asyncio.gather(
        tools.call("search", first), tools.call("search", first), tools.call("search", second)
    )
    assert len(source.calls) == 2
    assert tools.metrics["cache_hits"] == 1
    results[0]["evidence"][0]["text"] = "Forged source"
    assert results[1]["evidence"][0]["text"] != "Forged source"
    cached = await tools.call("search", first)
    assert cached["evidence"][0]["text"] == evidence()["text"]
    await tools.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides,expected", [
    ({"doc_id": "other"}, "wrong_document"),
    ({"id": "made-up"}, "reference_identity_mismatch"),
    ({"page": 99}, "reference_identity_mismatch"),
    ({"page": True}, "invalid_page"),
    ({"section_id": "missing"}, "source_unavailable"),
    ({"text": "Release requires one approval."}, "excerpt_not_in_source"),
    ({"text": ""}, "missing_reference_fields"),
    ({"source_type": "unknown"}, "invalid_source_type"),
])
async def test_evidence_gate_rejects_forged_provenance_and_excerpt(overrides, expected):
    checked = await EvidenceGate().validate(answer(citation=evidence(**overrides)), "atlas", SourceGateway())
    assert not checked.valid
    assert expected in " ".join(checked.failures)


@pytest.mark.asyncio
async def test_gate_checks_verbatim_excerpts_but_cannot_prove_answer_entailment():
    checked = await EvidenceGate().validate(
        answer("Incorrect semantic answer: three approvals.", evidence(text="two approvals")),
        "atlas", SourceGateway(),
    )
    # This explicit limitation prevents source checks being presented as an
    # automatic factual correctness or semantic entailment guarantee.
    assert checked.valid
    missing = await EvidenceGate().validate(
        {"answer": "Unsupported claim", "evidence": [], "status": "answered"}, "atlas", SourceGateway()
    )
    assert missing.failures == ["answered_without_evidence"]


@pytest.mark.asyncio
@pytest.mark.parametrize("source_type,tool", [("table", "get_table_image"), ("image", "get_image")])
async def test_gate_routes_table_and_image_metadata_to_original_tool(source_type, tool):
    source = SourceGateway()
    source.source.update({"source_type": source_type, "id": f"atlas:{source_type}:release"})
    checked = await EvidenceGate().validate(answer(citation=source.source), "atlas", source)
    assert checked.valid
    assert source.calls[0][0] == tool


@pytest.mark.asyncio
async def test_event_workflow_preserves_actor_reviewer_dependency_and_trace_privacy():
    order = []

    async def ordered_actor(*args):
        order.append("actor")
        return answer("Private draft text")

    async def ordered_reviewer(question, doc_id, draft, tools):
        assert order == ["actor"]
        assert draft["answer"] == "Private draft text"
        order.append("reviewer")
        return review(answer())

    result = await WorkflowEngine(ordered_actor, ordered_reviewer, SourceGateway()).run("How many?", "atlas")
    assert result["state"] == "completed"
    assert result["answer"]["status"] == "answered"
    kinds = [event["type"] for event in result["events"]]
    assert kinds.index("actor_completed") < kinds.index("review_completed") < kinds.index("validation_completed")
    assert "Private draft text" not in str(result["events"])
    assert result["metrics"]["actor_calls"] == 1
    assert result["metrics"]["reviewer_calls"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["baseline", "engineered", "optimized"])
async def test_three_modes_have_explicitly_different_citation_policies(mode):
    async def wrong_reviewer(question, doc_id, draft, tools):
        return review(answer(citation=evidence(page=55)))

    result = await WorkflowEngine(actor, wrong_reviewer, SourceGateway(), max_revisions=0).run("How many?", "atlas", mode)
    assert result["state"] == "completed"
    assert result["answer"]["status"] == ("insufficient" if mode == "optimized" else "answered")
    assert result["metrics"]["evidence_rejections"] == (1 if mode == "optimized" else 0)


@pytest.mark.asyncio
async def test_optimized_revision_is_bounded_and_failed_gate_never_persists_memory():
    store = MemoryStore()

    async def wrong_reviewer(question, doc_id, draft, tools):
        return review(answer("One approval", evidence(text="One approval")), "revise", "Use one approval")

    result = await WorkflowEngine(actor, wrong_reviewer, SourceGateway(), store, max_revisions=1).run("How many?", "atlas")
    assert result["state"] == "completed"
    assert result["answer"]["status"] == "insufficient"
    assert result["metrics"]["actor_calls"] == 2
    assert result["metrics"]["revisions"] == 1
    assert result["metrics"]["evidence_rejections"] == 2
    assert store.snapshot("atlas") == []


@pytest.mark.asyncio
async def test_validated_correction_can_be_written_and_used_after_revalidation():
    store = MemoryStore()
    memories = []

    async def wrong_actor(question, doc_id, tools, memory):
        memories.append(memory)
        return answer("One approval is required.")

    async def correcting_reviewer(question, doc_id, draft, tools):
        return review(answer(), "revise", "The release rule requires two approvals.")

    engine = WorkflowEngine(wrong_actor, correcting_reviewer, SourceGateway(), store, max_revisions=0)
    first = await engine.run("How many?", "atlas")
    assert first["metrics"]["memory_writes"] == 1
    record = store.snapshot("atlas")[0]
    assert record["validated"] is True
    assert record["version"] == 1
    second = await engine.run("How many?", "atlas")
    assert second["metrics"]["memory_writes"] == 0
    assert memories[0] == []
    assert memories[1][0]["content"] == record["content"]


@pytest.mark.asyncio
async def test_stale_and_legacy_memories_are_not_used_by_optimized_actor():
    store = MemoryStore()
    store.add("atlas", "Old validated rule", [evidence()], "test", validated=True)
    store.add("atlas", "Unchecked legacy rule", [evidence()], "legacy", validated=False)
    store.add("other", "Other document rule", [evidence()], "test", validated=True)
    source = SourceGateway()
    source.source["text"] = "Release now requires three approvals."
    observed = []

    async def current_actor(question, doc_id, tools, memory):
        observed.extend(memory)
        return answer("Three approvals", source.source)

    result = await WorkflowEngine(current_actor, reviewer, source, store).run("How many?", "atlas")
    assert result["state"] == "completed"
    assert result["metrics"]["stale_memories_skipped"] == 1
    assert observed == []


@pytest.mark.asyncio
async def test_frozen_store_blocks_baseline_and_optimized_training_leakage():
    store = MemoryStore(frozen=True)

    async def correcting_reviewer(question, doc_id, draft, tools):
        return review(answer("Corrected wording"), "revise", "Remember the release rule")

    for mode in ("baseline", "engineered", "optimized"):
        result = await WorkflowEngine(actor, correcting_reviewer, SourceGateway(), store, max_revisions=0).run("How many?", "atlas", mode)
        assert result["metrics"]["memory_writes"] == 0
    assert store.version == 0
    assert store.snapshot("atlas") == []


def test_memory_persistence_scope_deduplication_and_copy_isolation(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)
    assert store.add("atlas", "Remember rule", [evidence()], "test", validated=True)
    assert not store.add("atlas", "Remember rule", [evidence()], "test", validated=True)
    assert store.add("other", "Remember rule", [evidence()], "test", validated=True)
    restored = MemoryStore(path)
    assert restored.version == 2
    assert len(restored.snapshot("atlas")) == 1
    records = restored.snapshot("atlas")
    records[0]["content"] = "Mutated"
    assert restored.snapshot("atlas")[0]["content"] == "Remember rule"
    restored.freeze()
    assert not restored.add("atlas", "Another", [evidence()], "test")
    assert MemoryStore(path).version == 2


@pytest.mark.asyncio
async def test_cancel_interrupts_worker_and_prevents_reviewer_and_memory_update():
    started, stopped = asyncio.Event(), asyncio.Event()
    reviewer_called = False

    async def waiting_actor(*args):
        started.set()
        try:
            await asyncio.sleep(10)
        finally:
            stopped.set()

    async def unused_reviewer(*args):
        nonlocal reviewer_called
        reviewer_called = True
        raise AssertionError("Reviewer must not run after cancellation")

    engine = WorkflowEngine(waiting_actor, unused_reviewer, SourceGateway())
    running = asyncio.create_task(engine.run("How many?", "atlas", task_id="cancel-me"))
    await asyncio.wait_for(started.wait(), 1)
    assert engine.cancel("cancel-me")
    result = await asyncio.wait_for(running, 1)
    assert stopped.is_set()
    assert not reviewer_called
    assert result["state"] == "cancelled"
    assert result["metrics"]["memory_writes"] == 0
    assert not engine.cancel("cancel-me")


@pytest.mark.asyncio
async def test_agent_timeout_and_budget_fail_with_structured_result():
    async def hanging_actor(*args):
        await asyncio.sleep(10)

    timed = await WorkflowEngine(hanging_actor, reviewer, SourceGateway(), agent_timeout=0.01).run("How many?", "atlas")
    assert timed["state"] == "failed"
    assert timed["error"]["type"] == "TimeoutError"

    async def greedy_actor(question, doc_id, tools, memory):
        await tools.call("search", {"doc_id": doc_id, "keyword": "one"})
        await tools.call("search", {"doc_id": doc_id, "keyword": "two"})
        return answer()

    budget = await WorkflowEngine(greedy_actor, reviewer, SourceGateway(), max_tool_calls=1).run("How many?", "atlas")
    assert budget["state"] == "failed"
    assert budget["error"]["type"] == "ToolBudgetExceeded"
    assert budget["metrics"]["tool_calls"] == 1


@pytest.mark.asyncio
async def test_concurrent_tasks_have_isolated_budgets_and_cancellation():
    started = asyncio.Event()

    async def selective_actor(question, doc_id, tools, memory):
        if question == "wait":
            started.set()
            await asyncio.sleep(10)
        return answer()

    engine = WorkflowEngine(selective_actor, reviewer, SourceGateway())
    waiting = asyncio.create_task(engine.run("wait", "atlas", task_id="first"))
    await started.wait()
    with pytest.raises(ValueError, match="already running"):
        await engine.run("duplicate", "atlas", task_id="first")
    successful = await engine.run("answer", "atlas", task_id="second")
    assert engine.cancel("first")
    cancelled = await waiting
    assert successful["state"] == "completed"
    assert successful["metrics"]["tool_calls"] == 1
    assert cancelled["state"] == "cancelled"
