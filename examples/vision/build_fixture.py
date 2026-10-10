"""Rebuild a tiny image-only synthetic multimodal integration fixture.

Run: python examples/vision/build_fixture.py

The model-visible JSON contains descriptions but no chart values. The PDF embeds
the rendered PNGs, so chart values are also absent from its searchable text layer.
Gold labels live in questions.json, outside the tool server's documents root.
This is an integration smoke test, not a general visual understanding benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parent
DATA = BASE / "documents"
ASSETS = DATA / "assets"
INK = (0.08, 0.16, 0.24)
MUTED = (0.36, 0.43, 0.5)
ACCENT = (0.12, 0.45, 0.63)
LIGHT = (0.93, 0.96, 0.98)


def _text(page, point, text, size=18, color=INK, bold=False):
    page.insert_text(point, text, fontsize=size, fontname="hebo" if bold else "helv", color=color)


def _completed_chart(target: Path) -> None:
    with fitz.open() as drawing:
        page = drawing.new_page(width=900, height=600)
        page.draw_rect(page.rect, fill=(1, 1, 1), color=None)
        _text(page, (50, 62), "COMPLETED TASKS BY REGION", 28, bold=True)
        _text(page, (50, 98), "Fictional operations sample | count of completed tasks", 17, MUTED)
        origin_x, baseline_y, scale = 115, 465, 10
        for tick in range(0, 31, 5):
            y = baseline_y - tick * scale
            page.draw_line((origin_x, y), (835, y), color=(0.84, 0.88, 0.91), width=0.8)
            _text(page, (77, y + 7), str(tick), 17, MUTED)
        _text(page, (61, 147), "Count", 15, MUTED)
        for index, (region, count) in enumerate(zip(("North", "East", "West"), (18, 27, 12))):
            left = 190 + index * 225
            top = baseline_y - count * scale
            page.draw_rect(fitz.Rect(left, top, left + 105, baseline_y), fill=ACCENT, color=None)
            _text(page, (left + 35, top - 17), str(count), 25, bold=True)
            _text(page, (left + 19, 505), region, 22)
        page.draw_line((origin_x, baseline_y), (835, baseline_y), color=INK, width=1.2)
        _text(page, (50, 565), "Synthetic data for an image-input integration check. Not measured project performance.", 14, MUTED)
        page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(target)


def _failed_table(target: Path) -> None:
    with fitz.open() as drawing:
        page = drawing.new_page(width=900, height=600)
        page.draw_rect(page.rect, fill=(1, 1, 1), color=None)
        _text(page, (50, 62), "FAILED TASKS BY REGION", 28, bold=True)
        _text(page, (50, 98), "Same fictional operations sample | count of failed tasks", 17, MUTED)
        left, top, right, row_height = 100, 155, 800, 78
        page.draw_rect(fitz.Rect(left, top, right, top + row_height), color=None, fill=ACCENT)
        _text(page, (137, top + 50), "Region", 24, (1, 1, 1), bold=True)
        _text(page, (595, top + 50), "Failures", 24, (1, 1, 1), bold=True)
        for index, (region, count) in enumerate(zip(("North", "East", "West"), (2, 3, 1)), 1):
            y = top + index * row_height
            page.draw_rect(fitz.Rect(left, y, right, y + row_height), color=(0.8, 0.86, 0.9),
                           fill=LIGHT if index % 2 else (1, 1, 1), width=0.8)
            _text(page, (137, y + 49), region, 25)
            _text(page, (645, y + 49), str(count), 28, bold=True)
        _text(page, (50, 565), "Synthetic data for an image-input integration check. Not measured project performance.", 14, MUTED)
        page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(target)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    _completed_chart(ASSETS / "completed.png")
    _failed_table(ASSETS / "failed.png")
    document = {
        "doc_id": "vision_lab", "title": "Vision Lab: fictional regional operations",
        "page_count": 2, "source_pdf": "vision_lab.pdf",
        "sections": [{
            "id": "s1", "page": 1, "title": "About this image-only sample",
            "text": "This fictional regional operations sample contains a completed-task chart and a failed-task table for North, East, and West. Read the images to find their counts. The text descriptions intentionally do not transcribe the numeric values.",
        }],
        "tables": [],
        "images": [
            {"id": "fig1", "page": 1, "path": "assets/completed.png",
             "caption": "Completed tasks by region: North, East, West. This chart contains synthetic completion counts; read the image for the values."},
            {"id": "fig2", "page": 2, "path": "assets/failed.png",
             "caption": "Failed tasks by region: North, East, West. This table contains synthetic failure counts from the same sample; read the image for the values."},
        ],
        "fixture_notice": "Image-only integration fixture. Numeric chart values are absent from structured text. Not a model benchmark or real operational measurement.",
    }
    with fitz.open() as pdf:
        for index, entry in enumerate(document["images"], 1):
            page = pdf.new_page(width=595, height=842)
            _text(page, (42, 55), "VISION LAB", 26, bold=True)
            _text(page, (42, 86), "Fictional regional operations", 15, MUTED)
            page.draw_line((42, 105), (553, 105), color=(0.75, 0.82, 0.88))
            _text(page, (42, 140), "Completed tasks" if index == 1 else "Failed tasks", 18, bold=True)
            page.insert_image(fitz.Rect(32, 177, 563, 531), filename=str(DATA / entry["path"]))
            page.insert_textbox(fitz.Rect(42, 585, 553, 656), entry["caption"],
                                fontsize=12, fontname="helv", color=INK, lineheight=1.6)
            _text(page, (42, 707), "Values are shown only inside the image, not in the text layer.", 11, MUTED)
            _text(page, (42, 728), "Educational synthetic fixture; no real people or organizations.", 11, MUTED)
            _text(page, (42, 802), "Image-input integration fixture", 10, MUTED)
            _text(page, (505, 802), f"{index} / 2", 10, MUTED)
        pdf.set_metadata({"title": document["title"], "author": "", "subject": "Synthetic image-input integration fixture"})
        pdf.save(DATA / document["source_pdf"], deflate=True)
    (DATA / "vision_lab.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    questions = [
        {"id": "vision-01", "doc_id": "vision_lab",
         "question": "根据图中的 Completed tasks，East 区域的完成数量是多少？",
         "expected_answer": "East完成数量为27", "answerable": True, "category": "image_reading",
         "required_terms": ["27"], "expected_evidence_ids": ["vision_lab:image:fig1"]},
        {"id": "vision-02", "doc_id": "vision_lab",
         "question": "根据 Completed tasks 图，East 区域的完成数量减去 West 区域的完成数量，差值是多少？",
         "expected_answer": "27减12等于15", "answerable": True, "category": "image_arithmetic",
         "required_terms": ["15"], "expected_evidence_ids": ["vision_lab:image:fig1"]},
        {"id": "vision-03", "doc_id": "vision_lab",
         "question": "综合 Completed tasks 图与 Failed tasks 图，North 区域的完成数量减去失败数量，结果是多少？",
         "expected_answer": "18减2等于16", "answerable": True, "category": "cross_image_arithmetic",
         "required_terms": ["16"], "expected_evidence_ids": ["vision_lab:image:fig1", "vision_lab:image:fig2"]},
    ]
    (BASE / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Chart values must not leak into the model-visible structured passages or
    # into searchable PDF text. The low integers in page labels are metadata.
    passages = " ".join([item["text"] for item in document["sections"]] +
                        [item["caption"] for item in document["images"]])
    assert not any(character.isdigit() for character in passages)
    with fitz.open(DATA / "vision_lab.pdf") as pdf:
        assert len(pdf) == 2
        searchable = " ".join(page.get_text() for page in pdf)
        assert all(value not in searchable for value in ("18", "27", "12", "15", "16"))
        assert all(len(page.get_images()) == 1 for page in pdf)
    print("Created vision_lab: image-only source, two PNGs, two-page PDF, three isolated gold labels.")


if __name__ == "__main__":
    main()
