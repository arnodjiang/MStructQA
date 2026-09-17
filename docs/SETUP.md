# Setup and execution

## Environment

Use Python 3.11+ for a new environment, install root `requirements.txt`, and activate `.venv`. The full builder launches offline rendering workers through `.venv/bin/python`, so retain that environment name. `curl` is required by the downloader. Dependency version ranges support development; exact model responses and binary fonts are not bundled.

Copy `.env.example` to `.env` and set your provider's API key, Responses base URL and image-capable model. `scripts/openai_config.py` reads the local file with environment-variable overrides; a historical model default remains for compatibility, so explicitly set `OPENAI_MODEL` for a new provider. Never commit actual credentials. API output may be incomplete or malformed despite prompt instructions.

## Fonts and platform

The development configuration uses macOS Arial Unicode and system fallback fonts for some Bengali/Persian characters. These fonts are not redistributed. Set `MVISQA_FONT` in the shell to a covering font on your machine; `MVISQA_FALLBACK_FONTS` is a path-separated list for additional fallback coverage. Font files, shaping and layout affect image hashes.

The complete 24-language rendering stack is not certified portable across all operating systems. On macOS, generated adapters run with a restricted AST and a subprocess sandbox denying network/credential access. Other platforms retain the AST restriction but do not have the same macOS sandbox; use an isolated environment for generated adapters. Verify representative Latin, CJK, right-to-left and Indic scripts before a full run.

## API-free synthetic demo

```bash
python skills/multilingual-visual-benchmark/scripts/visual_harness.py run \
  --spec skills/multilingual-visual-benchmark/examples/table.json \
  --translations skills/multilingual-visual-benchmark/examples/table_locales.json \
  --languages en,zh,ar --output data/demo
```

Add `--font /absolute/path/to/covering-font.ttf` when needed. This uses checked-in synthetic data/translations, performs no API calls and writes a content-addressed run plus `latest.json`. Inspect the generated PNGs and JSONL records directly.

## Full construction

Run root `scripts/run_pipeline.py` stages in order:

1. `download`: read public source pins from `configs/upstream_manifest.json`, fetch selected files, verify upstream hashes and write local metadata. This requires several GB of storage. A pre-existing local metadata file takes precedence, so preserve its provenance.
2. `prepare`: profile the sources, apply the configured candidate selection, extract assets and build stable identities. Selection policies and cardinality checks are implemented in the selection and builder modules.
3. `baseline`: reconstruct/transcribe, normalize QA, generate the baseline localizations, render and export candidates.
4. `baseline-audit`: source review, code-constant verification and multilingual admission audit. Uncertain/failed candidates remain separate.
5. `expand`: copy a baseline's frozen specification and QA into a new output and complete the remaining localizations for the 24-language set. If the matching local `query_polish_v1` records exist, their adopted edits are reused; otherwise the baseline queries are used.
6. `expand-audit`: review the remaining localized images, labels, query fluency and reference-answer equivalence in bounded batches.
7. `finalize`: verify every exported code's constants, execute all 24 languages on representative chart/table cases, check inherited/new admission criteria, export screened JSONL and package standalone code. Requires complete generation and audit records.

Pass `--baseline PATH`, `--output PATH` and `--workers N` to the entry point. For advanced targeted repairs use the underlying modules' `--help`. Do not run duplicate writers against one output directory. Watcher variants are optional local orchestration, not required for the sequential public workflow.

## Retry and resume

Successful API responses are cached by request fingerprint. Inspect failed attempt records, fix their cause, then explicitly resume with `--retry-failed`. Transport failures (connection/timeout, 429 and 5xx) have ten automatic retries, each after a five-second wait. An individual API request may itself take up to the configured timeout; five seconds is the retry delay, not the response timeout. Batch execution continues after transport retry exhaustion.

Malformed/incomplete JSON and schema/content violations are not transport failures and are not automatically regenerated. Authentication errors also require configuration repair. The resumable request history is local and must not be pushed to GitHub.

## Outputs and interpretation

| Artifact | Meaning |
| --- | --- |
| `selection_lock.json`, `source/` | Frozen selected sources and identities |
| `cases/<id>/spec.json`, `qa.json`, `locales/` | Frozen visual specification, linked QA and language dictionaries |
| `images/`, `code/` within each case | PNGs, layout checks and standalone rendering code |
| `benchmark.jsonl` | Full candidate configurations, including flagged items |
| `validation_release/val.jsonl` | Candidates satisfying the current automated admission gates |
| `validation_release/val.needs_review.jsonl` | Excluded/uncertain candidates |
| `api/`, `expansion_audit/` | Local generation/review provenance and failures |
| `status.json`, `completion.json` | Actual progress; final completion marker only after finalization |
| `reproducible_code.zip` | Final code package |

An image existing on disk is not evidence of semantic quality. No human verification is implied by automated admission. Exact reproduction uses stored specification/label/code/font snapshots rather than new model calls.

## Offline checks

```bash
python -m unittest discover -s tests -v
python -m unittest scripts.final_benchmark.test_contract -v
python -m unittest discover -s skills/multilingual-visual-benchmark/tests -v
```

The latter two suites require covering fonts. CI runs portable API/configuration contracts without credentials; local rendering tests provide additional platform-specific evidence.
