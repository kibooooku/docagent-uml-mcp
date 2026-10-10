"""Real SDK stdio integration, source validation, and safe-path regressions."""

import base64
import json
from pathlib import Path

import fitz
import pytest

from docagent.documents import TOOL_DEFINITIONS, DocumentStore, import_pdf
from docagent.gateway import LocalGateway, MCPGateway, ToolError

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "documents"


@pytest.mark.asyncio
async def test_real_stdio_negotiation_tool_discovery_and_all_six_tools():
    """No fake transport: __aenter__ starts python -m docagent.mcp_server."""
    async with MCPGateway(EXAMPLES) as remote, LocalGateway(EXAMPLES) as local:
        definitions = await remote.list_tools()
        assert {tool["name"] for tool in definitions} == {tool["name"] for tool in TOOL_DEFINITIONS}
        assert remote.metadata["protocol_version"] == "2025-06-18"
        assert remote.metadata["server"] == "docagent-document-tools"
        requests = [
            ("get_outline", {"doc_id": "harbor"}),
            ("search", {"doc_id": "harbor", "keyword": "借阅"}),
            ("get_section_content", {"doc_id": "harbor", "section_id": "s2"}),
            ("get_image", {"doc_id": "harbor", "image_id": "fig1"}),
            ("get_page_images", {"doc_id": "harbor", "start_page_num": 1, "end_page_num": 2}),
            ("get_table_image", {"doc_id": "harbor", "table_id": "t1"}),
        ]
        for name, arguments in requests:
            actual = await remote.call(name, arguments)
            assert actual == await local.call(name, arguments)
            for image in actual.get("images", []):
                assert image["mimeType"] == "image/png"
                assert base64.b64decode(image["data"]).startswith(b"\x89PNG\r\n\x1a\n")
        outline = await remote.call("get_outline", {"doc_id": "harbor"})
        assert outline["page_count"] == 3
        assert len(outline["figures"]) == 1
        assert "C:" not in json.dumps(remote.metadata)


@pytest.mark.asyncio
async def test_real_stdio_returns_errors_and_stays_usable():
    async with MCPGateway(EXAMPLES) as gateway:
        requests = [
            ("unknown", {"doc_id": "harbor"}),
            ("get_outline", {"doc_id": "../outside"}),
            ("get_outline", {"doc_id": "missing"}),
            ("get_outline", {"doc_id": "harbor", "extra": True}),
            ("get_section_content", {"doc_id": "harbor", "section_id": "missing"}),
            ("search", {"doc_id": "harbor", "keyword": " "}),
            ("get_page_images", {"doc_id": "harbor", "start_page_num": 0, "end_page_num": 1}),
            ("get_page_images", {"doc_id": "harbor", "start_page_num": 2, "end_page_num": 1}),
            ("get_page_images", {"doc_id": "harbor", "start_page_num": 1, "end_page_num": 4}),
            ("get_page_images", {"doc_id": "harbor", "start_page_num": True, "end_page_num": 2}),
        ]
        for name, arguments in requests:
            with pytest.raises(ToolError):
                await gateway.call(name, arguments)
        result = await gateway.call("get_section_content", {"doc_id": "harbor", "section_id": "s1"})
        assert result["evidence"][0]["id"] == "harbor:text:s1"


@pytest.mark.parametrize("bad_id", ["../secret", "..\\secret", "C:\\secret", "/tmp/secret", "", ".", "a/b"])
def test_document_identifiers_cannot_escape_data_root(bad_id):
    with pytest.raises(ToolError):
        DocumentStore(EXAMPLES).call("get_outline", {"doc_id": bad_id})


@pytest.mark.asyncio
async def test_asset_paths_cannot_escape_data_root_through_mcp(tmp_path):
    data = tmp_path / "documents"
    data.mkdir()
    outside = tmp_path / "private.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\nDO_NOT_READ")
    document = {"doc_id": "bad", "title": "Unsafe path fixture", "sections": [], "tables": [],
                "images": [{"id": "fig1", "page": 1, "path": "../private.png", "caption": "Test"}]}
    (data / "bad.json").write_text(json.dumps(document), encoding="utf-8")
    async with MCPGateway(data) as gateway:
        with pytest.raises(ToolError, match="escapes") as error:
            await gateway.call("get_image", {"doc_id": "bad", "image_id": "fig1"})
        assert "DO_NOT_READ" not in str(error.value)
        assert str(tmp_path) not in str(error.value)


def test_pdf_import_is_page_heuristic_and_preserves_renderable_source(tmp_path):
    source = tmp_path / "original.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 40), "Page one has readable text.")
        pdf.new_page()  # No OCR claim or fabricated text for a blank page.
        pdf.save(source)
    target = tmp_path / "imported"
    json_path = import_pdf(source, target, "sample")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["parser"]["ocr"] is False
    assert payload["page_count"] == 2
    assert payload["sections"][0]["page"] == 1
    assert payload["sections"][1]["text"] == ""
    store = DocumentStore(target)
    text = store.call("get_section_content", {"doc_id": "sample", "section_id": "p1"})
    assert "readable text" in text["evidence"][0]["text"]
    rendered = store.call("get_page_images", {"doc_id": "sample", "start_page_num": 1, "end_page_num": 2})
    assert rendered["pages"] == [1, 2]
    assert len(rendered["images"]) == 2
    with pytest.raises(ToolError, match="already exists"):
        import_pdf(source, target, "sample")
    with pytest.raises(ToolError):
        import_pdf(source, target, "../escape")


def test_all_question_labels_reference_real_full_source_evidence():
    questions = json.loads((EXAMPLES.parent / "questions.json").read_text(encoding="utf-8"))
    assert len(questions) == 30
    assert len({question["id"] for question in questions}) == 30
    store = DocumentStore(EXAMPLES)
    observed_categories = set()
    for question in questions:
        observed_categories.add(question["category"])
        assert question["answerable"] == bool(question["expected_evidence_ids"])
        for identity in question["expected_evidence_ids"]:
            doc_id, kind, entry = identity.split(":")
            assert doc_id == question["doc_id"]
            tool, argument = {"text": ("get_section_content", "section_id"), "table": ("get_table_image", "table_id")}[kind]
            result = store.call(tool, {"doc_id": doc_id, argument: entry})
            assert result["evidence"][0]["id"] == identity
            assert result["evidence"][0]["text"]
    assert observed_categories == {"text", "table", "cross_section", "unanswerable"}


@pytest.mark.asyncio
async def test_gateway_requires_connection():
    with pytest.raises(ToolError, match="context manager"):
        await MCPGateway(EXAMPLES).call("get_outline", {"doc_id": "harbor"})
