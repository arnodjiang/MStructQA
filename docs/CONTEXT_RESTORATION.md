# Source document context restoration

The context-restored condition supplies complete original document prose as text
alongside the chart/table image and unchanged question: `pre_text` followed by
`post_text` for MMTU/FinQA, and `Paragraph` for ChartQAPro. Four selected FinQA
cases and one ChartQAPro case contribute 350 of the 8,960 configurations.
Images, references, base IDs, and variant IDs remain unchanged. The new input is
identified by its dataset revision, context hashes and inference input ID.

The latest release uses the [current-only export policy](CLEAN_RELEASE.md).
Historical question/answer text and intermediate files remain in external
archives; only current QA and assets enter the dataset directory. Metadata fields
are cleaned while effective references and inference inputs remain unchanged.

Context follows the question language: the aligned language for LQA, Chinese or
English for XQA. All 24 languages are represented; English is an exact source
copy, and 115 case/language translations use the user's configured API. Numeric
strings are protected by placeholders. Translation validates paragraph IDs/order,
placeholder multiplicity, and absence of added numerical digits. These checks
establish structural preservation, not human-certified translation equivalence.
No question, answer label, `Year` evaluation flag, `gold_inds`, reasoning steps, `program`, or answer-based
sentence selection is sent to the translator. Every original paragraph is kept.

The table is never transcribed into the inference prompt. Original prose can
naturally repeat table values; it is preserved as source text, not synthesized
from the table. Prompts explicitly permit this evidence. The query language still
controls the answer language. System/user text and the supplied image are bound
to the saved request and raw output. Both JSON and one-shot plain-answer fallback
use the same context. Missing or changed context prevents reuse of old results.

## Data-only preparation and authorized resumption

The user initially paused evaluations on 2026-09-17 and later authorized automatic
resumption after the latest data is complete and validated. Pause markers are
archived with that authorization before restarting orchestration. Dataset
preparation can still be run separately without starting evaluations:

```bash
python -u -m scripts.final_benchmark.restore_context \
  --source data/visual_benchmark/final_128_24lang_v3 \
  --work data/context_restoration/all_sources_context_v1 \
  --output data/visual_benchmark/final_128_24lang_v4_context --workers 2
```

Previously completed FinQA translations are reused with source/hash verification.
`data_job.json` records translation/publication status and `evaluation_autostart=false`.
Publishing this revision alone does not switch the active evaluation release or
mutate old results. The authorized orchestrator waits for the existing producer,
then verifies all source/translation bindings, API outputs, image hashes and
unchanged questions/references before migration and evaluation startup:

```bash
python -u -m scripts.evaluation.context_rerun --after-data-pid <data-producer-pid>
```

`dependency_audit.json` records whether images, questions and answers need new
translation. All five currently affected cases have numeric answers and 24
verified existing image locales, so only the omitted prose needs translation.
`context_validation.json` records the final gate; failure prevents model startup.

## Run and resume

For the current local selection, submit the resumable orchestrator:

```bash
python -u -m scripts.evaluation.context_rerun
```

It translates into `data/context_restoration/all_sources_context_v1`, publishes a separate
`final_128_24lang_v4_context` dataset after every translation passes validation,
and migrates the three existing model runs. Source run locks must be released
first. Completed unaffected predictions, including terminal failures, are reused;
unattempted cases continue and exactly 350 changed configurations per model are
prioritized for new inference. The old dataset and all old outputs are retained.
The job submits model workers in the background and records PIDs/log paths in
`data/context_restoration/all_sources_context_v1/job.json`.

To resume a stopped model worker, use its new run directory and original provider:

```bash
python -u -m scripts.evaluation.context_rerun \
  --run data/evaluation/gpt6_astra_v4_context_20260916 --provider openai
```

The Gemini worker uses `--provider token_router`, two workers and a global 6.5-second
request interval, and exits when the provider reports insufficient quota. GPT
inference retains each run's original model. All final judgments use GPT-6 Astra:
exact matching first, then text-only answer equivalence for mismatches.

Unchanged Judge decisions are reused only with verified identical references,
predictions, and Judge model/prompt/policy. Their provenance is recorded, and no
new API call is charged. Changed inputs are judged anew. Completion publishes only
that model's LaTeX row and writes `context_comparison.json` for available paired
old/new judgments. Old runs without judgments do not receive invented baseline
accuracy. Translation, new inference and Judge usage are recorded separately;
inherited attempts must not be counted twice.

This condition restores previously missing evidence and therefore changes the
available information. Report it separately from an ablation of image rendering
alone. Archived original inputs/outputs remain available for either analysis.
