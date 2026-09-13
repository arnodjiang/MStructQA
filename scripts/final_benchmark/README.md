# Historical eleven-language implementation reference

For the current MStructQA WIP interface, see the root README and docs/SETUP.md. Paths and counts below describe the earlier development workflow.

# MVisQA 128-case API construction

This is the reproducible batch implementation for the 128 frozen candidates selected
in `data/processed/normal_qa_v3/candidates.jsonl`. It retains all six source quotas and
overlapping diversity features; it does not replace difficult examples with easy ones.

## Configuration and execution

Use the existing project environment and dependencies from
`scripts/final_benchmark/requirements.txt`. Set `OPENAI_API_KEY`,
set `OPENAI_MODEL` to your provider-supported model (the development run used `gpt-6-astra`), and optionally set
`OPENAI_BASE_URL` in the project `.env` or environment. API calls use the
Responses API. Environment values take precedence. Keys are never included in output metadata or
the offline rendering worker's environment.

On a fresh source checkout, create `.venv`, install the requirements, then reconstruct
the frozen inputs from the pinned public upstream metadata included in the source zip:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/final_benchmark/requirements.txt
.venv/bin/python scripts/download_benchmarks.py
.venv/bin/python scripts/profile_and_sample.py
.venv/bin/python scripts/export_candidate_assets.py
.venv/bin/python scripts/build_expansion_registry.py
```

The downloader fetches approximately 5.2 GB and checks upstream file hashes. Follow
the upstream datasets' terms. The drawing runtime defaults to a macOS system font;
on another machine provide `MVISQA_FONT` pointing to a covering Unicode font. Live
model outputs can differ on a fresh run; saved API responses/specifications and the
standalone renderers reproduce the recorded build without new generation calls.

```sh
.venv/bin/python -m scripts.final_benchmark.pipeline --stage all --workers 2
.venv/bin/python -m scripts.final_benchmark.review --workers 2
.venv/bin/python -m scripts.final_benchmark.export
```

The batch runner supports stages `prepare`, `recovery`, `qa`, `translate`, `render`,
plus `--ids` for targeted work and `--retry-failed` for an intentional bounded retry
after inspecting a failure. Successful API responses are reused by request hash.
SDK retries are disabled. Explicit transport retries run up to ten times with a five-second delay; every submitted request has an attempt file.
Streaming checkpoints partial text when the provider sends chunks. Some gateways
buffer the response and can still time out; streaming alone does not solve that limit.
Interrupted/non-JSON responses are not treated as successful results.
Previously failed requests require explicit resumption. Malformed/incomplete output is not automatically retried. Recorded rendering errors
may trigger at most two targeted API code repairs with the original image and error.

Default output: `data/visual_benchmark/final_128_v1/`. `status.json` and `events.jsonl`
show actual progress. `export --partial` can create an honest incomplete preview;
normal `export` refuses to call an incomplete set complete.

For a dense multi-panel chart that exceeds the provider's response limit, use
`split_recovery --ids CASE_ID --retry-failed`. It saves panel boxes, crops, each API
adapter and the composite adapter. Resume the normal QA and translation stages after
recovery. `reuse_pilot` is a provenance-preserving migration for the previously
digitized pilot chart, not a general recovery fallback. `render_ready --watch` renders
completed locale sets while API work continues. Keep the combined concurrency of all
API processes within the provider's limit (five worked for this run).

Run `python -m scripts.final_benchmark.audit_run` to snapshot code hashes, dependency
versions, artifact counts and observed API usage. Recorded token totals exclude
requests for which the provider returned no usage; they are not a billing statement.
`verify_export` executes representative standalone English, Chinese, Arabic and Hindi
code and compares decoded pixels. `package_source` creates the credential-free source
archive under `data/releases/`. `repair_json` can ask the same configured API for
punctuation-only edits to a complete malformed response; its guard rejects changes
to numbers, letters and other non-punctuation content and preserves the raw attempt.

## Construction

1. Freeze the source selection, base IDs, upstream revisions and raw assets.
2. Charts: API returns numerical data, label dictionary and Python adapter, without
   seeing the reference QA. Tables: use original HTML/Markdown cells where available;
   image-only tables are transcribed through the API. Render an English baseline.
3. API normalizes the supplied reference answer without solving it, retaining the
   original answer. It replaces label references with protected `[[key]]` placeholders.
4. API translates labels and QA templates together into ten non-English languages.
   Languages are batched by source text size; every target dictionary is validated.
5. Render eleven image languages from one frozen numeric/structural specification.
   The table layout is measured across all locales and held constant across languages.
6. An independent API review compares source and reconstruction and checks reference
   answer preservation. It does not alter recovered data to fit an answer.
7. Export standalone original-English and translated Python, PNGs, JSONL, metadata,
   checks and an HTML comparison gallery.

Generated adapters have a restricted AST contract. They run without network access
or project credentials; on macOS a subprocess sandbox confines file writes. Exported
code requires normal Python dependencies and a covering Unicode font, but no external
JSON, API, or project imports. Font choice/hash is recorded; system fonts are not
redistributed.
Arabic mixing with ASCII numbers uses Unicode bidi runs before HarfBuzz shaping;
shaping an entire mixed-direction string as one RTL run reverses the digits.

## Configuration count

For each original QA and each visual language `v`, query and answer languages are
chosen from the distinct set `{v, zh, en}`. Answer language follows query language.
The question ends with an explicit reply-language instruction.

- 11 monolingual configurations.
- 10 cross-language configurations with Chinese query/answer.
- 10 cross-language configurations with English query/answer.

Total: 128 × 31 = **3,968 QA configurations** and 128 × 11 = **1,408 images**.
English/Chinese monolingual configurations are not duplicated. These are 128 source
questions, not 3,968 statistically independent questions. Preserve grouping by source
figure/table and document across splits and uncertainty estimates.

## Artifacts and interpretation

- `source/`, `selection_lock.json`: frozen original candidates and diversity.
- `api/<stage>/<case>/<request-hash>/`: prompt, input metadata, image hashes, raw
  responses, attempt times/status, response/model IDs, usage and parsed cache.
- `cases/<id>/original/`: untouched source assets.
- `reconstruction_*.json`, `.error.json`: every reconstruction and repair.
- `spec.json`, `render_spec.json`, `table_extraction.json`: structure and numeric data.
- `qa.json`, `locales/`: reference normalization, protected templates and translations.
- `baseline.png`, `images/`, `.layout.json`: English baseline and final images/boxes.
- `code/original/en/render.py`, `code/translated/<lang>/render.py`: frozen executable
  per-language code; earlier versions are retained if renderer code changes.
- `review.json`: independent automated source/reconstruction audit.
- `benchmark.jsonl`: all constructed variants, each carrying its review state.
- `benchmark.api_reviewed.jsonl`: candidates passing the automated source-image and
  reference checks and the configured mechanical checks; not human-certified data.
- `image_manifest.json`, `case_manifest.json`, `validation.json`, `diversity_report.json`.

Numerical data equality across languages does not establish source reconstruction
accuracy. Dense charts can be approximated or incorrectly recovered. Review failures
remain visible; no fabricated tolerance is used to admit them. Translation correctness
and long-answer scoring still require a declared evaluation protocol. Task tags are
source heuristics and API annotations, not human ground truth. The full 3,968 records
may therefore contain flagged candidates and should not all be presented as audited
benchmark test data.

Code release should include these scripts and the skill, but not `.env`, downloaded
datasets or proprietary fonts. Source data and model-generated reconstructions retain
their applicable upstream terms. This workflow does not publish an external repository.

## Screened validation release

`val_audit` performs a cached per-case review of the source and all eleven language images, including chart-type and difficulty annotations. `val_verify` checks all exported Python DATA/LABELS/identity constants without executing them. `val_report` produces explicit quality denominators and source-level diversity. `score_val` computes strict EM and clustered uncertainty estimates.

```sh
.venv/bin/python -m scripts.final_benchmark.val_verify
.venv/bin/python -m scripts.final_benchmark.val_audit --workers 5
.venv/bin/python -m scripts.final_benchmark.val_audit --export-only
.venv/bin/python -m scripts.final_benchmark.val_report
```

Output is `data/visual_benchmark/final_128_v1/validation_release/`. Read `VALIDATION_PROTOCOL.md` and `val_schema.json`. Pending or rejected candidates remain separate from screened `val.jsonl`; no API review is equivalent to human certification. The source archive v0.3.0 includes these review and evaluation tools.
