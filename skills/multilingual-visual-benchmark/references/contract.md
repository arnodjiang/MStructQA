# Harness contract

Dependencies are in `requirements.txt`. Commands run from the skill directory; output may be any writable directory. The CLI does not assume the MVisQA project path or a specific provider URL/model. Use `OPENAI_API_KEY`, `OPENAI_MODEL`, optional `OPENAI_BASE_URL`, and a covering Unicode font supplied by `--font` / `MVISQA_FONT`. API uses an OpenAI-compatible Responses endpoint; compatible providers must support `responses.create`, image input, and `max_output_tokens`. `--translations` bypasses API and reads reviewed translations. No provider credentials are included in archives.

## Specification v1

```json
{
  "schema_version": 1,
  "kind": "chart",
  "base_id": "stable-source-identity",
  "source_language": "en",
  "source": {"sha256": "hash-of-source", "dataset": "name", "revision": "revision", "row": 0},
  "renderer": "chart_adapter.py",
  "data": {"values": [2, 5]},
  "labels": {"a": "Category A", "b": "Category B"},
  "qas": {"qa-1": {"question": "What is the value for [[b]]?", "answer": "5"}},
  "recovery": {"method": "source_data_or_pixel_estimate", "review_status": "pending", "uncertainties": []}
}
```

`base_id` must come from source provenance; retain upstream figure and QA identifiers as appropriate. The run ID includes numeric data, translations, code, font hash and harness hash; variant IDs incorporate the run. Never use translated text as the source identity. Optional additional source/provenance fields are retained. Source image bytes should be preserved alongside the input by the caller; JSON stores the source path/hash, not a copy of that image.

### Chart adapter

A trusted Python file defines `render(data, labels) -> (PIL.Image, boxes)`. It may import installed packages, but must not depend on project files, call APIs, execute CLI operations, or contain language-specific figure text outside `labels`. It must render from `data`, without reading QA answers. `put`, `wrap`, `mask`, and `MISSING_GLYPHS` from the bundled text helper are available in the generated script. `put` returns a box with `inside_canvas`. Return all label boxes; native library tick labels are the adapter author's responsibility to inspect.

Use conventional plotting libraries for numeric marks. Recover scales (linear/log), series membership, legends and annotations carefully; preserve source uncertainty. Hand-calibrated recovery is supported, not concealed. The harness does not execute the original adapter directly: it copies the adapter with frozen labels, data and the font helper into each standalone code file and executes that file. Inspect adapter code before use.

### Table data

Set `kind` to `table`, omit `renderer`, and supply:

```json
{"rows": [[{"text":"Product","label_key":"cell_0_0","rowspan":1,"colspan":1},{"text":"2002"}], [{"text":"Diapers","label_key":"cell_1_0"},{"text":"3.0"}]]}
```

The original `text` remains immutable; `labels[label_key]` equals that original source text. Absent `label_key` means render the original cell string directly. Omit covered cells under spans; include explicit empty uncovered cells. Geometry validation rejects ragged grids, overlapping spans, or spans past the last row. Layout is sized across all locales, then frozen identically across languages. Width currently grows with column count; extremely wide tables need a custom adapter/layout policy.

`prepare-table` parses a single non-nested HTML table or CSV/TSV and retains original raw text. It labels language-bearing cells by row and cell ordinal. It is not a general HTML layout engine and does not preserve source CSS styling. For Markdown and OCR, provide an explicitly checked cell spec. Inputs containing scientific notation or codes should be checked when choosing which cells to translate; do not interpret numerical notation as language.

### Translator interface

Source and translated output:

```json
{"labels":{"a":"Category A"},"qas":{"q":{"question":"Value of [[a]]?","answer":"2"}}}
```

A fixture file maps target language codes to this structure. Source language is always copied. `CachedTranslator.translate(source, language)` is the provider boundary; it validates labels, QA keys and protected references. Numeric answer equivalence and translation quality require an additional review; placeholders passing validation are not proof of semantic validity. Batching is per input/language; very large tables may require a provider adapter that chunks labels and reassembles a fully validated dictionary. Duplicate labels can be ambiguous; preserve category distinctions and review collisions.

## Outputs

`runs/<content-hash>/` contains:

- `source_spec.json`, `render_spec.json`, `locales.json`: raw source and frozen rendering input.
- `code/original/<source-language>/render.py`, `code/translated/<language>/render.py`.
- `images/<language>.png` and label geometry reports.
- `benchmark.jsonl`: same-language QA variants; cross-language combinations can be assembled from the same dictionaries without generating additional images.
- `manifest.json`: artifact hashes, run ID, source ID and font hash.
- `validation.json`, `index.html`: mechanical checks and gallery; all outputs remain candidates pending review.

Re-run exported code with `python render.py --output image.png --font /path/to/font.ttf`. There is no API call or dependency on external JSON/project code. Python dependencies and font are still required. Existing completed runs are checked for tampering before reuse. API caches are request-addressed and retain sanitized raw responses; they are not a substitute for final code snapshots.
