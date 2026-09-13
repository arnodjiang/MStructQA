# Dataset card — Work In Progress

**Title:** MStructQA: A Multilingual Benchmark for Chart and Visual Tabular Question Answering in MLLMs.

**Status:** Code/prompt release. The expanded dataset is still under construction and review. No finalized dataset or leaderboard is distributed here.

**Use:** Research on multilingual visual QA and matched-language robustness. Not certified ground truth for high-stakes decisions.

**Languages:** en, zh (Simplified), ja, ko, fr, de, es, pt, ru, ar, hi, it, nl, pl, tr, vi, id, th, sw, fa, ur, bn, ta, te. Only Chinese and English serve as cross-language query/answer pivots.

**Scale:** Current development selection: 128 base QA. Target: 3,072 per-case visual artifacts and 8,960 candidate configurations. Final screened counts depend on audits. Language variants are dependent. The final paper-scale size is undecided.

**Sources:** TableVQA-Bench, CharXiv, ChartQAPro, Visual-TableQA, ChartQA and MMTU. Public pins are in `configs/upstream_manifest.json`; collection and test eligibility are distinct.

**Construction:** API-assisted visual recovery, protected label/QA localization, conservative copyediting, deterministic rendering, mechanical verification and automated semantic/visual review. Generated plotting code is a reconstruction rather than upstream plotting source.

**Schema:** Candidate JSONL includes base/variant IDs, provenance, visual/query/answer languages, question, reference answer, image/code paths and hashes, configuration and review state. Screened outputs include admission and audit fields. `scripts/final_benchmark/val_schema.json` documents the initial validation format; expanded output adds audit provenance and remains WIP.

**Limitations:** Approximate recovery, missing chart elements, specialist-label mistranslation, complex-script rendering, uneven language admission, generator/reviewer correlation, upstream overlap or contamination, heuristic difficulty labels, and nontrivial numeric/list/text scoring.

**Rights:** The MIT code license does not cover upstream/derived datasets or fonts. Obtain upstream data under its applicable terms. No uniform dataset license or redistribution permission is asserted.

**Reproducibility:** Record upstream versions, model/provider, prompt hashes, response IDs, font/code hashes and run manifests. Never commit credentials or raw API logs. Live generations can differ across runs.
