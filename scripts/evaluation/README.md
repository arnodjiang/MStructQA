# Full benchmark evaluation

Context-restored revisions additionally supply the original document
`pre_text`/`post_text` (MMTU/FinQA) or `Paragraph` (ChartQAPro) as translated text in the user prompt. Context follows
the question language, while tables remain image-only. The original question is
unchanged. `context_input.py` records the exact combined input and a versioned
context-aware system prompt for both JSON and plain-answer modes. Only the
affected rows use this prompt. Translation never receives answer labels,
reasoning programs, or gold evidence selectors. See
[context restoration](../../docs/CONTEXT_RESTORATION.md) for execution and reuse.

Inference uses the configured `.env` model and Responses API. It sends the exact current `query` string plus its localized image, with translated source prose for context-restored rows as described above; no reference answer, source specification, labels, or quality-review evidence is sent. Each QA receives one independent conversation and one selected valid answer. JSON Schema constrains output to `{"answer":"..."}`. The base English system prompt is in `answer_prompt.txt`; `context_input.py` applies the versioned context extension only to affected rows.

```bash
python -m scripts.evaluation.run \
  --dataset data/visual_benchmark/mstructqa_24 \
  --output data/evaluation/astra_run1 --smoke --workers 1

# After a successful preflight, reuse its result and finish the same run:
python -m scripts.evaluation.run \
  --dataset data/visual_benchmark/mstructqa_24 \
  --output data/evaluation/astra_run1 --workers 3
```

The second command can be launched in the background. It scores automatically only after every QA has a terminal outcome. The same command resumes unfinished IDs; existing successes and terminal failures are not resampled. A new output directory denotes a new repetition. Do not mix data/prompt/model settings inside one run. A file lock prevents concurrent writers. `.env` credentials are never copied to the run metadata.

Defaults: three workers, request starts at least three seconds apart, 300-second timeout, maximum 8,192 output tokens (including provider reasoning tokens), provider-default temperature/reasoning effort, no tools or external retrieval. One initial request and up to ten transport retries, five seconds apart, are permitted for connection/timeouts, HTTP 429 and 5xx. Malformed final-answer JSON uses the single plain-answer fallback described below. Refusal, incomplete generation and other content failures are retained without answer-conditioned retries. Authentication failures stop further submissions. An interrupted transport request may have unknown provider-side usage; its attempt record is retained.

Both providers first request JSON and also accept a valid answer object enclosed
in a single Markdown code fence. If the final answer still cannot be parsed,
exactly one additional call uses `plain_answer_prompt.txt`, the same question and
image, and plain-text output without a JSON schema. Its nonempty final text is
saved directly as the prediction (a returned valid answer object is unwrapped).
This fallback is never retried, including on connection errors; an interrupted
fallback also consumes its one-call allowance. No reference answer or correctness
signal is used to select it. Refused or truncated responses do not trigger it.
The global request-start interval and quota-stop policy still apply.

On resume, saved format failures with valid fenced JSON are recovered without an
API call; other eligible format failures are queued for their one plain call.
Original predictions are archived in `prediction_history`, and raw responses and
usage records are retained. The manifest records the versioned policy amendment
and prompt hash, each attempt records its answer mode, and usage summaries count
`plain_answer_fallback_calls`. Scores disclose policy amendments. The ACC metric
is unchanged; a plain sentence is not automatically judged semantically correct.

## Frozen scoring protocol

The rules below describe the original strict metric. The final semantic judging
stage described below is a separate, explicitly versioned metric; old strict scores
and frozen inference snapshots remain available.

`score.py` is implemented and tested before full inference. After inference finishes, it compares each extracted prediction to the frozen reference:

- Plain ASCII numeric forms: exact decimal-value equality, with comma thousands separators and minus-glyph normalization. For example `750.0` equals `750`; `749` does not. No approximation tolerance is introduced.
- Other answers: strict text equality after Unicode NFC and outer-whitespace normalization. No case folding, translation, percentage conversion, list reordering, substring matching or model judge.
- Failed predictions count as incorrect in the fixed denominator. Coverage and failures are reported, so transport failure is not silently filtered out.

Report full candidate results as diagnostic candidate-set performance. The candidate cohort is not human-certified. Screened, chart-only and table-only results are also reported separately. The primary table does not silently substitute the screened subset.

XQA-ZH and XQA-EN are macro-averages over 23 off-diagonal image languages each. LQA reports the 24 diagonal configurations. AVG averages all 70 distinct configurations, **not** the 26 displayed metric columns. Missing configuration coverage yields an unavailable aggregate rather than a silently changed denominator.

After all predictions exist, scoring can be repeated without any API calls:

```bash
python -m scripts.evaluation.score --run data/evaluation/astra_run1
```

## Artifacts and accounting

Source identities and unmodified model inputs/outputs are preserved for paired
ablation studies. See [ABLATION_PROVENANCE.md](../../docs/ABLATION_PROVENANCE.md)
for the original-versus-reconstructed distinction, snapshot fields, and comparison
protocol. `lineage/latest.json` points to a content-addressed snapshot; this sidecar
does not change frozen references, predictions, or Judge decisions.

- `manifest.json`: frozen input hashes, configured model, endpoint hash, decoding settings, number of repetitions and execution sessions.
- `references.jsonl`, `prompt.txt`: exact local scoring references and inference prompt.
- `requests/<id>.json`: answer-blind request metadata with image checksum and exact question.
- `attempts/<id>/<n>.json`: every HTTP attempt, timestamps, latency, returned model, response ID, error, raw output and provider `usage`.
- `responses/<id>/<n>.json`: complete provider response for returned responses.
- `predictions/<id>.json`: extracted answer or terminal failure, including selected attempt.
- `progress.json`: compact progress and usage totals, updated after each attempt/result.
- `usage_summary.json`: final totals for API attempts, retries, input/output/total tokens and optional cached-input/reasoning-output details. Cached tokens are a subset of input; reasoning tokens are a subset of output, never added twice. Missing usage is unknown, not zero. Provider prices and billing are required to report monetary cost.
- `scores.json`, `scored_predictions.jsonl`, `leaderboard.csv`: aggregate and per-example scores.
- `main_table_row.tex`: result row in the agreed XQA/LQA/AVG order; `main_results.tex` is also generated when a table template was available at startup.

A preflight session and the subsequent resumed batch count as two process invocations of **one evaluation repetition**, not two full benchmark runs. Failed retries remain part of API/token accounting. No semantic quality verdict is inferred from usage or successful execution.

## Gemini through Token Router (separate provider)

Configure `TOKEN_ROUTER_API_KEY` and `TOKEN_ROUTER_BASE_URL` in `.env`. These are
independent of `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL`. The Gemini
runner does not change or use the GPT credentials. The requested model identifier
is preserved as `google/gemini-3.8-flash`.

`TOKEN_ROUTER_BASE_URL=https://api.tokenrouter.com/v1` is normalized to the native
`https://api.tokenrouter.com/v1beta/models/google/gemini-3.8-flash:generateContent`
endpoint. Origins, `/v1beta` and `/v1beta/models` are also supported. The adapter
uses `x-goog-api-key`, `systemInstruction`, image `inlineData` and
`generationConfig.responseJsonSchema`; it does not send an OpenAI Responses request.

Run two real examples (one English chart and one Chinese table):

```bash
python -m scripts.evaluation.run_token_router \
  --dataset data/visual_benchmark/mstructqa_24 \
  --output data/evaluation/gemini38_flash_run1 --smoke --workers 1
```

Inspect `smoke_report.json`. These two examples test transport and extraction;
they are not a benchmark accuracy estimate. For a full independent run, omit
`--smoke` and retain the output directory to reuse the two completed examples:

```bash
python -m scripts.evaluation.run_token_router \
  --dataset data/visual_benchmark/mstructqa_24 \
  --output data/evaluation/gemini38_flash_run1 --workers 2
```

All results and locks are scoped to the output directory; Gemini and GPT can run
concurrently through their separate providers. The full Gemini run uses the same
XQA/LQA/AVG scorer and automatically exports the correctly named model row after
all QA terminate. Resume only with the same frozen data, prompt, model and settings.

Gemini temperature defaults to **0.7**, matching the supplied provider example.
Thinking and image resolution use provider defaults; GPT's defaults differ and
must be disclosed in cross-model comparisons. Both use an 8,192-token output
cap. Only a single `STOP` candidate is accepted; JSON format errors use the shared
one-call plain-answer fallback above.
Thought parts, refusal/safety stops and truncated output are not treated as final
answers. No answer-aware retry or automatic model fallback is performed.

Token Router defaults to two workers and a global minimum request-start interval
of 6.5 seconds, including retries, to stay below the observed 10 requests/minute
limit. Concurrency and request rate are separate controls. Override the interval
with `--request-interval` only to match the provider's actual limit.

Transport failures, 429 and 5xx get up to ten retries after a five-second pause,
also subject to the global request-start interval;
400/401/403/404 stop further submissions because configuration or access may be
wrong. Raw successful/error HTTP response bodies are retained with credentials
redacted. Optional `modelVersion` and `responseId` are recorded as returned;
missing model identity is not invented.

`usageMetadata` is retained without alteration. For shared accounting, input is
`promptTokenCount`, total is `totalTokenCount`, and generated tokens include
`candidatesTokenCount + thoughtsTokenCount`. If the latter split is absent, output
may be derived from `totalTokenCount - promptTokenCount` for these no-tools calls.
Absent cached/thinking detail is unknown rather than assumed zero. Gemini and
OpenAI token counts use provider-specific tokenization and are not interchangeable
pricing units. See the [native Gemini response schema](https://ai.google.dev/api/generate-content#UsageMetadata).

After resolving a Token Router quota/access failure, repeat the two-case command with `--retry-failed`. Previous failure predictions are archived in `prediction_history/`; all HTTP attempts remain in the usage ledger. Do not retry known insufficient-quota responses until the provider account has available credit.

Use `--defer-scoring` on the full Token Router run to save all predictions and usage without computing ACC. The final state is `inference_finished_scoring_deferred`; run `python -m scripts.evaluation.score --run <output>` separately when ready. This switch does not change inference settings or invalidate the two smoke-test predictions.

Token Router account-credit errors (including `insufficient_user_quota` and
`insufficient_quota`, even under HTTP 429) stop submissions and retries immediately.
Already in-flight calls may still finish and incur usage; their responses are saved
before exit. The runner then exits with code 3 and records `quota_exhausted` plus
`stop_reason.json`. Ordinary rate-limit 429 responses still use bounded retries.
SIGTERM/SIGINT now drain in-flight calls without scheduling new ones, so future
concurrency changes can preserve returned answers. Use `--workers 2
--request-interval 6.5` for the current provider limit. Successful saved answers
are reused when resuming the same output directory.

## Final LLM-as-a-judge stage

To evaluate a different inference model while pinning the existing Judge and
publishing only its completed LaTeX row:

```bash
python -m scripts.evaluation.run \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/gpt56_sol_v3_20260916 \
  --model gpt-5.6-sol --judge-model gpt-6-astra \
  --workers 3 --request-interval 3 --llm-judge \
  --publish-table paper/tables/main_results.tex
```

`--model` changes only inference; it does not rewrite `.env` or the Judge model.
The table update requires full Judge completion and all 70 configurations, checks
the expected Judge model, and replaces only the matching model row. Pending entries
remain dashes; existing model rows and table spacing are preserved. Both stages
retain separate request counts and token usage. `--smoke` tests one inference item
in the same run directory, and a subsequent full run reuses it.

Run this only after every inference input has a terminal result:

```bash
python -m scripts.evaluation.judge --run data/evaluation/astra_run1 --workers 2
# Or run both strict scoring and final semantic judging:
python -m scripts.evaluation.score --run data/evaluation/astra_run1 --llm-judge
```

For future inference jobs, both runners accept `--llm-judge` to execute this stage
at the end. For Token Router, `--llm-judge` and `--defer-scoring` cannot be combined;
use `--llm-judge` alone for automatic final adjudication. Existing already-running jobs
keep their original settings. Gemini inference still uses Token Router; judging
uses the independent `OPENAI_*` configuration. `judge --model` can select another
judge model on that endpoint. The manifest records when the evaluated model and
judge are the same; this is post-hoc automated adjudication, not independent human
validation.

Judge settings can be changed independently in the local `.env`:

```dotenv
# Blank values inherit the corresponding OPENAI_* setting.
JUDGE_MODEL=
JUDGE_BASE_URL=
JUDGE_API_KEY=
```

Model precedence is `judge --model` > `JUDGE_MODEL` > `OPENAI_MODEL`.
Environment variables override `.env` values. These overrides affect only Judge,
including the automatic stage after Gemini/GPT inference. They do not change the
inference model or Token Router credentials. Currently blank overrides use the
configured GPT-6 Astra. The Judge endpoint must support the existing Responses API with text input
and JSON output. It does not need image input. A changed model/endpoint requires a new Judge
output directory (`--output`) so incompatible judgments cannot silently mix.

`configs/benchmark_release.json` identifies the active local v3 dataset and
retired paths. The inference runners reject retired datasets. Historical run
manifests remain immutable: `frozen_images.json` maps their exact image hashes to
current identical images or a small `retired_input_assets/` archive. This archive
has no benchmark entry point and is retained only for historical provenance.
The current text-only Judge does not read this index or any image files. Translation provenance is retained separately
and resolved through `provenance_paths.json` without altering locale hashes.

The English rubric is in `judge_prompt.txt`. Exact matches to the effective
reference are accepted without another API call. Other completed answers are
judged using only the frozen question text, reference answer, prediction and
expected answer language. The question disambiguates scope, units and precision;
Judge does not solve the visual task or check image fidelity. Model
identity is not included in the judging payload. Case, punctuation, unambiguous
missing dollar signs/units, equivalent ratios/percentages, and ordinary rounding
can count as correct. A blanket numerical tolerance is not introduced. For
example, 0.13606 and 13.61% are compatible under ordinary rounding, while 720 and
750 are not automatically equivalent merely because they are close. Verdicts are binary: `equivalent` (correct) or `different` (incorrect). Ambiguous
equivalence is `different`; no uncertain verdict is published. Legacy uncertain
decisions are mapped to different without new API calls, preserving their reasons
and incurred token usage. This mapping does not change ACC, which already counted
only equivalent decisions as correct. Numeric proximity without justified rounding
or an explicit tolerance is insufficient; 720 vs 750 and -54.5 vs -54 are incorrect.
Failed inference also counts as incorrect in the fixed denominator. Language
compliance is recorded separately from semantic ACC.

Current results live in `<run>/llm_judge_text_v2/`: `manifest.json`, `prompt.txt`, individual
`judgments/`, full API request/response-attempt records under `api/`, `progress.json`,
and `usage_summary.json`. Once every item has a decision, `scores.json`,
`judgments.jsonl`, `leaderboard.csv`, and `main_table_row.tex` use the same XQA/LQA/70
configuration AVG aggregation as the strict scorer. They do not overwrite paper
scores or old strict results. Token usage is separate from inference usage; missing
provider usage stays unknown. Two workers share a three-second request-start gap;
connection/429/5xx failures use the existing five-second, up-to-ten-retry policy.
The prior image-conditioned Judge outputs have been removed. Only the text-only
protocol is supported; no historical image verdicts are reused. No image,
rendering specification, table cells or reconstruction code is sent to the Judge.
Malformed judge content is retained as a `different` decision with `judge_error`
diagnostics, not retried
until a desired verdict appears. The run is resumable and protected by a file lock.
`--ids` and `--limit` support bounded smoke checks; an incomplete judge run does not
publish an aggregate ACC. No repeated inference is performed.

### Explicit reference corrections

`configs/reference_corrections.json` contains user-confirmed source-level label
adjudications. The CharXiv case `ce3cd691bfbeb2813fd9` (source row 399) is corrected
from `θ = 45°, θ = 90°` to `0°、45°`. The correction is bound to the source dataset,
file, row and original answer, and applies to all 70 configurations. It is not
inferred from predictions. Judge outputs preserve both original and effective
references and the correction ID.

```bash
python -m scripts.final_benchmark.correct_reference \
  --parent /path/to/input_revision \
  --output /path/to/new_revision
```

This produces a separate data revision, updates the source reference-label
metadata, English QA and all 24 localized answer templates, and retains upstream
raw downloads and before-correction snapshots. Images/questions are unchanged,
so the existing predictions for this angle case can be reused for rescoring.
This differs from the repaired radial-diagram case: its images changed in v2 and
its 70 old predictions still require fresh inference for v2/v3 reporting. Judging
a v1 inference run does not turn it into an evaluation of v3 images.

### Resume Gemini against a corrected dataset

Stop the source runner with SIGTERM and wait for its in-flight calls to finish.
Create a fresh evaluation directory; do not change the frozen source manifest:

```bash
python -m scripts.evaluation.migrate_token_router \
  --source data/evaluation/gemini38_flash_tokenrouter_20260916 \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/gemini38_flash_tokenrouter_v3_20260916
python -m scripts.evaluation.run_token_router \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/gemini38_flash_tokenrouter_v3_20260916 \
  --model google/gemini-3.8-flash --workers 2 --request-interval 6.5 --llm-judge
```

Migration locks the stopped source run, verifies actual image hashes in both
revisions, and checks source provenance, question, language, model, endpoint,
prompt, answer-format policy and generation settings before reusing successful
answers. Changed images/questions and old failed inputs are submitted again.
A gold-only correction can reuse a prediction because gold was never model input.
Each reused prediction keeps its original run identity and prediction checksum
in `reused_from`; old requests/responses and token records remain traceable.
`migration.json` lists reused and invalidated IDs and source/inherited token
totals. Target usage includes inherited calls: do not add the two runs' totals
without subtracting the inherited overlap. Judge usage is reported separately.
After inference, strict matching accepts matching answers and only mismatches
go to the same English Judge rubric and `OPENAI_*` endpoint used for GPT scoring.

### Rerun only repaired GPT inputs

```bash
python -m scripts.evaluation.rerun_changed \
  --source data/evaluation/gpt6_astra_full_20260915 \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/gpt6_astra_v3_repair_20260916
```

The changed inputs must exactly match `invalidated_evaluation_inputs.json`.
All other outcomes, including prior terminal failures, are preserved. The original
run is unchanged. Only the 70 repaired radial configurations receive new inference;
label-only corrections reuse their predictions. Strict metrics use the combined
v3 prediction set, and a single resumable text-only Judge covers the combined predictions.
`repair_summary.json` records incremental calls/tokens and repair completion.
The old partial-judge/merge workflow is removed. Exact matches skip the API;
only mismatches require text-only judging. Retired v1 runs are rejected by the
Judge loader, even though their predictions are retained for accounting/provenance.
A full run is not marked finished if its Judge stage pauses before completion.
