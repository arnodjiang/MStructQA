---
name: multilingual-visual-benchmark
description: Reconstruct chart images as Python, translate chart labels and linked QA, or translate table cells and render multilingual images for benchmarks. Preserve numeric structure, provenance, and original plus translated rendering code. Use for multilingual chart/table dataset construction and reproducible localization pipelines.
---

# Multilingual visual benchmark

Use the bundled harness for deterministic translation, rendering, validation, and code export. Use model judgment to recover a new chart or extract an image-only table. The harness does not autonomously infer arbitrary chart data from pixels. It executes a reviewed Python chart adapter or a structured table specification.

## Route and recover

- **Chart input:** inspect the original image; prefer available source data and plotting code. Otherwise identify panels, axes and scales, marks, series, legends, annotations and visible text. Recover numeric data without using reference QA answers as reconstruction targets. Write a Python adapter `render(data, labels)` and a JSON specification. Keep visible language strings in a stable label dictionary, numeric values in data, and record pixel calibration, uncertainties and recovery method. First compare the English/source-language reconstruction against the input; retain approximate or ambiguous reconstructions as candidates.
- **Table input:** prefer original HTML/CSV/structured cells over OCR. Run `prepare-table` for one HTML table or CSV/TSV, or construct the JSON cell grid directly. For Markdown, parse cells while retaining the full raw text. For images, extract cells and spans, then check them against the image before translation. Preserve numeric cell strings, row/column order, row spans, column spans, blanks and original raw input. Translate each language-bearing cell through its `label_key`; do not replace numerical cells with model output.

Read [the adapter and schema contract](references/contract.md) when preparing an input. Runnable chart and merged-table examples are in `examples/`.

## Translate and render

Keep original labels and translations separate. For a QA that refers to a visible label, use a protected `[[label_key]]` in the question template and bind it to the same translated dictionary used by the image. Visible identifiers such as `hopper:stand` should be translated semantically when their chart is localized; retain the original identifier in provenance. Preserve numerical answers and units; do not ask the translator to solve or correct the QA.

Default to the user's language set; if unspecified, this project uses en, zh, ja, ko, fr, de, es, pt, ru, ar, hi. Preserve the source language as the reconstruction baseline. The translation provider can be replaced through `CachedTranslator.translate`, or supplied via reviewed `--translations` JSON. Live translation reads environment credentials and caches validated responses by request fingerprint. Use existing authorization and configured provider; do not expose credentials or copy env files into artifacts. No automatic retries after malformed/truncated output; correct the cause before an intentional retry.

From this skill's directory, for example:

```sh
python scripts/visual_harness.py run --spec examples/chart.json --output /tmp/chart-pilot --languages en,zh --translations examples/chart_locales.json --font /path/to/Unicode.ttf
python scripts/visual_harness.py prepare-table --input table.html --output /tmp/table.json
python scripts/visual_harness.py run --spec /tmp/table.json --output /tmp/table-pilot --env-file /path/to/.env --font /path/to/Unicode.ttf
```

Generated chart adapters are executable Python: inspect their imports and side effects before running. Keep adapters self-contained, deterministic, and free of API calls. Use the bundled `put`, `wrap`, and `mask` helpers for shaped multilingual text, including Arabic and Devanagari; an equivalent renderer is acceptable when validated. Configure a font that covers the chosen languages; do not redistribute a system font without rights.

## Preserve and verify

The harness retains source/render specs, dictionaries, SHA256 manifests, original-language code, each translated code file, PNGs, same-language QA JSONL and an HTML gallery in content-addressed run directories. Each code file embeds its numerical data and translated labels and can run without the original project or translation cache. Do not call reconstructed code the upstream author's original source. Keep previous runs when data, translations, code, or fonts change.

Before delivery:

- Check source versus reconstruction, then translated images; all languages share the same numeric data and table geometry.
- Check missing glyphs, canvas/cell bounds, label distinctions, QA references, numeric answer meaning and translated units. Automated geometry checks do not establish semantic correctness.
- Execute representative exported code and compare the resulting images. Include Latin, CJK and complex scripts when present.
- Report uncertainty honestly. Do not invent a scoring tolerance to approve a reconstruction or adjust recovered data to match an answer. Mark acceptance pending where source fidelity or translation meaning is unresolved.
- Preserve base identity across languages and group variants of one source figure in the same benchmark split. Language variants are not independent source questions.

Open the HTML and provide the code archive and validation links. For broader benchmark evaluation or research claims, consult [method and evaluation guidance](references/method.md); this implementation by itself does not demonstrate novelty or benchmark validity.
