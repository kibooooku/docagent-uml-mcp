"""A generated 120-page integration fixture, not an accuracy benchmark."""
import json

import fitz

from docagent.documents import DocumentStore, import_pdf
from docagent.gateway import MCPGateway


async def test_120_page_import_search_and_final_page_mcp_render(tmp_path):
    original = tmp_path / "long.pdf"
    doc = fitz.open()
    for index in range(1, 121):
        page = doc.new_page()
        text = f"Section {index}: neutral operational notes. Page number {index}."
        if index == 7:
            text += "\nSAIL_NODE_FAILOVER_THRESHOLD is 45 seconds."
        if index == 113:
            text += "\nSAIL_NODE_INSPECTION_INTERVAL is 8 hours."
        page.insert_text((50, 70), text)
    doc.save(original)
    doc.close()
    data_dir = tmp_path / "documents"
    imported = import_pdf(original, data_dir, "long120")
    document = json.loads(imported.read_text(encoding="utf-8"))
    assert len(document["sections"]) == 120
    store = DocumentStore(data_dir)
    assert store.call("get_outline", {"doc_id": "long120"})["page_count"] == 120
    async with MCPGateway(data_dir) as gateway:
        first = await gateway.call("search", {"doc_id": "long120", "keyword": "SAIL_NODE_FAILOVER"})
        second = await gateway.call("search", {"doc_id": "long120", "keyword": "SAIL_NODE_INSPECTION"})
        assert [e["page"] for e in first["evidence"]] == [7]
        assert [e["page"] for e in second["evidence"]] == [113]
        last = await gateway.call("get_page_images", {"doc_id": "long120", "start_page_num": 120, "end_page_num": 120})
        assert len(last["images"]) == 1
