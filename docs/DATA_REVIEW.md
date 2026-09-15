# Dataset inspection and human review

## Start

```bash
python scripts/review_dataset.py --dataset /path/to/finalized/dataset --port 8765
```

Open http://127.0.0.1:8765. No credentials or generation API are needed. The required export is `validation_release/val.candidates.jsonl`; selection and case manifests provide expected coverage and original-image locations. Keep these manifests with the export. Restart the server after a new finalization or artifact change: checks and records are snapshotted at startup.

## Workflow

1. Check the summary and filter **完整性异常** for missing configurations, invalid locale JSON, missing images/code, duplicate IDs, missing or conflicting numerical-data metadata hashes, image hash mismatches, empty QA or unresolved placeholders.
2. Choose a case and visual language. The language buttons show reviewed/available QA configurations. Select the question language independently from the available same-language, Chinese and English configurations.
3. Compare the original and localized images. Click either image to open its full resolution. Check series, values, units, categories, table structure and readability, then compare source and localized QA. Label dictionaries and automated evidence are expandable.
4. Record **通过**, **不通过** or **待确认**, with specific evidence in the notes. A verdict applies only to the displayed QA configuration. Save before moving to the next unreviewed configuration. Unfinished edits trigger a navigation warning.
5. Export the annotations JSON for adjudication. A later release-building step must explicitly reconcile human decisions with automated gates; this tool never changes admission or reference answers.

## Persistence and boundaries

Annotations are atomically saved in `<dataset>/manual_review/annotations.json`. Back up this file alongside the dataset. The optional reviewer name is remembered in the browser. Each annotation includes variant ID, case ID, verdict, notes, reviewer, UTC timestamp and a SHA-256 fingerprint of the complete candidate record. A changed candidate is displayed as stale and excluded from reviewed counts.

Use one server process per dataset. The tool stores the latest verdict per variant, not independent multi-rater ballots or an immutable review history. For independent raters, use separate dataset copies and adjudicate exported annotations externally. Only explicit asset IDs are served; the server does not expose arbitrary workspace files. It listens on loopback and is intended for local use, not public deployment.

Image bytes are hashed at startup. Numerical-data hashes are compared across candidate metadata; the UI does not re-execute renderers, independently recover numerical truth, or automatically establish answer equivalence. Semantic source fidelity, translated terminology and reference correctness require inspection of the source. Missing source images are shown explicitly; they are not reconstructed by this UI. A zero completeness-issue count is not a semantic quality certificate.
