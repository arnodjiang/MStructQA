# Current-only dataset releases

Latest dataset directories are constructed by an explicit allowlist. They are
never recursive copies of a development dataset.

Included artifacts are current QA, localized image PNGs, standalone rendering
code, current translated context, current manifests and small source-identity
records. `benchmark.jsonl` is the root-relative view of the same current rows as
`validation_release/val.candidates.jsonl`. The accepted/needs-review views are
regenerated from those rows. They are not inherited snapshots.

Excluded artifacts include partial/API-reviewed exports, query-polish histories,
raw source QA, per-case `qa.json` and question-bearing locale caches, originals,
pre-repair backups, old labels, API logs, previous predictions, old ZIP archives
and stale quality reports. Historical fields such as `original_query`,
`original_answer` and `upstream_original_answer` are absent from released rows.
The dataset still contains its current reference `answer`, used only for scoring.

`base_id`, `case_id`, source row provenance and hashes remain stable. Original QA
and original images are preserved in the external content-addressed
`data/evaluation/provenance_assets` store. `provenance_index.json` contains only
identifiers and hashes of those external source records; it does not embed their
old question or answer text. Explicit label corrections are checked against a
source-answer hash and the current corrected label. Retired full dataset directories and old release bundles are deleted. Historical
evaluation records and their verified content-addressed input/output archives
remain outside the current dataset for paired ablation studies.

This metadata cleanup does not change model input, so it does not invalidate
otherwise reusable predictions or compatible Judge outcomes. Added prompt
context still invalidates the affected 350 configurations. Judge reuse separately
verifies the old frozen decision and the new current scoring fields.

`scripts/final_benchmark/clean_release.py` rejects unexpected files, historical
question fields, symlinks, missing current assets and disagreement between the
root/evaluation views. The exporter checks this before publishing; evaluation
checks it again with context/source/image validation before starting. A failure
blocks publication/evaluation instead of silently selecting a historical file.

`code/original/en` denotes the current English reconstruction code, not an old QA
version. The code contains the current visual data and labels, not original QA.

Before resuming a context evaluation, `scripts/evaluation/audit_resume.py` checks
the current reference snapshot, image bytes, question and optional source context,
system prompt, selected attempt, and the source binding of every reused result.
A stale result blocks resume and requires explicit migration. Provider failures
can be retried with `context_rerun --run ... --provider token_router --retry-failed`;
previous attempts remain available for usage accounting.
