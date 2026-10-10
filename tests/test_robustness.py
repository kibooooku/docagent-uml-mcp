"""Validate the fault-experiment protocol and independent outcome accounting."""

import json
from pathlib import Path

import pytest
import pytest_asyncio

from docagent.robustness import SCENARIOS, VARIANTS, run_robustness


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def experiment(tmp_path_factory):
    corpus = Path(__file__).resolve().parents[1] / "examples" / "documents"
    output = tmp_path_factory.mktemp("fault-experiment")
    report = await run_robustness(corpus, output)
    return report, output


def _row(report, scenario, variant):
    return next(item for item in report["results"]
                if item["scenario"] == scenario and item["variant"] == variant)


def test_complete_balanced_matrix_and_sanitized_export(experiment):
    report, output = experiment
    assert len(report["results"]) == len(SCENARIOS) * len(VARIANTS) == 55
    pairs = {(item["scenario"], item["variant"]) for item in report["results"]}
    assert len(pairs) == 55
    assert report["configuration"]["model_calls"] == 0
    exported = (output / "robustness.json").read_text(encoding="utf-8")
    assert json.loads(exported) == report
    assert str(output) not in exported
    assert "C:\\" not in exported
    for variant in VARIANTS:
        assert _row(report, "normal", variant)["assessment"]["successful_safe_answer"]
        assert report["summary"][variant]["runs"] == len(SCENARIOS)


def test_no_gate_ablation_is_still_checked_by_independent_source_oracle(experiment):
    report, _ = experiment
    unchecked = _row(report, "forged_page", "optimized_no_gate")
    assert unchecked["workflow"]["answer"]["status"] == "answered"
    assert unchecked["assessment"]["semantic_correct"]
    assert unchecked["assessment"]["provenance_valid"] is False
    assert unchecked["assessment"]["unsafe_answer"]
    for scenario in ("forged_page", "cross_document", "forged_excerpt", "missing_citation"):
        checked = _row(report, scenario, "optimized")
        assert checked["assessment"]["abstained"]
        assert checked["assessment"]["false_refusal"]
        assert checked["assessment"]["safe_response"]
        assert not checked["assessment"]["successful_safe_answer"]
        assert not checked["assessment"]["semantic_correct"]
        assert checked["assessment"]["provenance_valid"] is None


def test_semantic_limitation_and_availability_failures_are_not_hidden(experiment):
    report, _ = experiment
    for variant in VARIANTS:
        semantic = _row(report, "wrong_answer_real_citation", variant)["assessment"]
        assert semantic["provenance_valid"] is True
        assert not semantic["semantic_correct"]
        assert semantic["unsafe_answer"]
        assert not semantic["safe_response"]
        failed = _row(report, "persistent_tool_error", variant)["assessment"]
        assert failed["execution_failed"]
        assert not failed["safe_response"]
        assert not failed["abstained"]
        assert not failed["successful_safe_answer"]


def test_transient_fault_is_recovered_without_oracle_answer_repair(experiment):
    report, _ = experiment
    for variant in VARIANTS:
        row = _row(report, "transient_timeout", variant)
        assert row["fault"]["injected_failures"] == 1
        if variant == "baseline":
            assert row["assessment"]["execution_failed"]
            assert row["workflow"]["metrics"]["retries"] == 0
        else:
            assert row["assessment"]["successful_safe_answer"]
            assert row["workflow"]["metrics"]["retries"] == 1
            assert row["fault"]["underlying_attempts"] == 2


def test_memory_filter_ablation_and_pollution_write_accounting(experiment):
    report, _ = experiment
    for scenario in ("unvalidated_memory", "stale_validated_memory"):
        full = _row(report, scenario, "optimized")
        unfiltered = _row(report, scenario, "optimized_no_memory_filter")
        assert len(full["memory_before"]) == 1
        assert full["workflow"]["metrics"]["memory_writes"] == 0
        assert full["memory_seen_by_actor"] == []
        assert full["assessment"]["successful_safe_answer"]
        assert unfiltered["memory_seen_by_actor"]
        assert unfiltered["assessment"]["provenance_valid"]
        assert unfiltered["assessment"]["unsafe_answer"]
    assert _row(report, "stale_validated_memory", "optimized")["workflow"]["metrics"]["stale_memories_skipped"] == 1
    for variant in VARIANTS:
        row = _row(report, "reviewer_memory_pollution", variant)
        assert row["memory_before"] == []
        wrote = row["workflow"]["metrics"]["memory_writes"]
        assert len(row["memory_after"]) == wrote
        if variant in {"optimized", "optimized_no_memory_filter"}:
            assert wrote == 0
            assert row["assessment"]["abstained"]
        else:
            assert wrote == 1
            assert row["assessment"]["unsafe_answer"]


@pytest.mark.asyncio(loop_scope="module")
async def test_repeated_run_reproduces_outcomes_not_incidental_timestamps(experiment, tmp_path):
    report, _ = experiment
    corpus = Path(__file__).resolve().parents[1] / "examples" / "documents"
    repeated = await run_robustness(corpus, tmp_path)
    assert repeated["summary"] == report["summary"]
    assert repeated["configuration"] == report["configuration"]
    assert [item["assessment"] for item in repeated["results"]] == [item["assessment"] for item in report["results"]]


@pytest.mark.asyncio
async def test_changed_source_cannot_silently_use_old_gold_value(tmp_path):
    source = tmp_path / "harbor.json"
    source.write_text(json.dumps({
        "doc_id": "harbor", "sections": [{"id": "s1", "page": 1,
        "text": "试点规模为3000名读者。"}], "tables": [], "images": [],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="unchanged harbor"):
        await run_robustness(tmp_path, tmp_path / "output")
    assert not (tmp_path / "output" / "robustness.json").exists()
