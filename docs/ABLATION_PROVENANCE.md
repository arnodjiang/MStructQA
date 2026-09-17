# Original samples and paired ablations

Every reconstructed/localized QA retains `original_sample_id` (the existing
`base_id`) and its source dataset/revision/file/row/slot. Never join original and
enhanced examples by their positions in a file. A repeated language variant is
not an independent original sample.

## Preserved evidence

`scripts/evaluation/lineage.py` makes an offline, content-addressed archive. It
does not call an API or modify reference snapshots, inference outputs, or scores.
Both inference runners archive after inference. After scoring, evaluation
orchestration refreshes the existing snapshot using frozen input metadata only;
the text Judge never needs to open an image.
For a running or completed run, refresh the index with:

```bash
python -m scripts.evaluation.lineage --run data/evaluation/astra_run1
```

`<run>/lineage/latest.json` points to the current snapshot. Previous indices remain
in `<run>/lineage/snapshots/`. Archived bytes are shared across runs in
`data/evaluation/provenance_assets/`, keyed by SHA-256. Keep this directory with
the evaluation artifacts; it contains the preserved source images, input images,
source metadata, prompts, requests, all finished attempts and returned provider
responses for terminal predictions, prediction records, and judgments. Failed
attempts and unselected answers remain available. An in-flight attempt is not
represented as a completed output. Partial snapshots explicitly mark pending QA.
Existing archived content is verified before reuse.

The snapshot contains two collections:

| Collection / field | Meaning |
| --- | --- |
| `source_records[].original_sample_id` | Stable upstream QA identity, shared by all derived language variants |
| `source_records[].upstream_question`, `upstream_answer` | Original source labels, including labels later corrected by an explicit overlay |
| `source_records[].upstream_image`, `upstream_assets` | Original raster and any original table/prompt files, archived with hashes |
| `samples[].variant_id` | Existing dataset variant identifier |
| `samples[].pair_id` | Base QA + question/image/answer language tuple; independent of changing question wording or image bytes |
| `samples[].condition` | `reconstructed_localized` for the current pipeline, including its English images |
| `samples[].visual_question_id` | Fingerprint of actual question text and image bytes |
| `samples[].model_io_id` | Identifier for the selected request/attempt/raw provider response; every finished attempt also has one |
| `samples[].input` | Exact question, archived image and prompt, frozen reference and correction ID |
| `samples[].raw_model_output`, `extracted_answer` | Unmodified returned answer text versus parsed prediction |
| `samples[].reused_from` | Prior-run lineage for identical-input reused results |
| `samples[].correct`, `reference_effective`, `judgment` | Existing binary text-Judge outcome and the effective scoring label |

Request/attempt metadata retain the actual JSON/plain-answer mode and prompt hash;
provider payloads retain returned model, usage, and response identifiers when
available. The main run prompt is archived, and plain-answer fallback prompt
content is also archived when present in the snapshot's run assets. Reference
answers are local scoring metadata and were not sent to the inference model.

## Original is not an older reconstruction

Current 24-language results use reconstructed/localized images. Neither an older
release nor `code/original/en` is an upstream original-image baseline. The snapshot
therefore records `is_upstream_original_input=false` and
`baseline_evaluation_status=not_established_by_this_run`.

The current selection preserves 119 upstream raster images for 128 source QA.
The other nine have source table text and require a faithful, separately versioned
rendering before an image-only baseline can be evaluated. They are explicitly
marked `requires_faithful_table_rendering`; do not feed their table text to a model
and report it as an original-image result.

## Comparing performance before and after construction

Run an upstream-image baseline separately and keep both conditions. Match source
QA using `original_sample_id`; use `pair_id` for comparisons with the same language
configuration. Use the same model, decoding settings, answer protocol, effective
reference labels, and text-Judge model/prompt in both conditions. Keep source-label
corrections identical across conditions while retaining the upstream labels in the
archive. Do not compare old strict accuracy with new semantic accuracy.

Report original ACC, enhanced ACC, their difference in percentage points, and
paired correct-to-wrong / wrong-to-correct counts with a shared denominator.
Separate failures from content errors diagnostically, without silently dropping
them. If the question is also rewritten, label the result as the combined effect
of question and visual construction. To isolate image reconstruction, hold the
question fixed. Compare only valid matching native-language cases for an original
baseline; do not treat a single native original as 24 independent observations.
If estimating uncertainty, resample by original sample rather than by its 70
correlated variants. Snapshot availability alone does not establish a measured
baseline or demonstrate a performance change.
