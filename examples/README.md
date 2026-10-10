# Synthetic examples

`documents/` contains three fictional Chinese specifications, their 3-page PDFs,
table images, and vector-drawn charts. No file contains a real person's details.
All quantities and charts are invented design targets, not measured outcomes.

`questions.json` contains 30 manually specified labels: 12 text questions,
6 table questions, 6 questions requiring multiple source entries, and 6
unanswerable questions. The JSON expected answers are evaluation labels only;
the document tool process and model adapters must not read them when answering.
Evidence identifiers are `doc_id:source_type:entry_id`.

Regenerate the fixtures with `python examples/build_examples.py`. The manually
structured JSON is authoritative for these examples; it is not the output of an
automatic layout parser. The separate PDF importer uses a page-text heuristic
without OCR or table/figure detection.

Tool examples:

```json
{"name":"get_section_content","arguments":{"doc_id":"harbor","section_id":"s2"}}
{"name":"get_table_image","arguments":{"doc_id":"orchard","table_id":"t1"}}
{"name":"get_image","arguments":{"doc_id":"atlas","image_id":"fig1"}}
{"name":"get_page_images","arguments":{"doc_id":"harbor","start_page_num":1,"end_page_num":2}}
```

Question categories measure answer coverage in a small controlled teaching set.
They are not representative of a full document QA benchmark, and text-only model
runs cannot establish visual reasoning quality.
