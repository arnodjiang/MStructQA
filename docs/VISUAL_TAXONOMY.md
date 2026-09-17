# Fine-grained visual types

The current `visual_kind` field is a single English category assigned by GPT-6
Astra from the released English image of each base case. Its label is shared by
the 24 localized visuals and 70 QA configurations of that case, which preserve
the chart/table structure. Questions and reference answers are never sent to the
classifier. The labels describe reconstructed evaluation images, not necessarily
the upstream originals.

`visual_family` preserves the previous coarse `chart`/`table` grouping for
compatible cohort reporting. Use `visual_kind` for fine-grained analysis. Images,
questions, answers, contexts and configuration IDs are unchanged by this update;
no model inference needs to be repeated solely because of these annotations.

## Tables

| `visual_kind` | Definition | Chinese description |
| --- | --- | --- |
| `Simple Table` | No merged cells spanning rows or columns | 普通表格，无跨行或跨列单元格 |
| `Row-Spanning Table` | Vertical merging across rows only | 跨行表 |
| `Column-Spanning Table` | Horizontal merging across columns only | 跨列表 |
| `Mixed-Spanning Table` | Both row and column spans, possibly in different cells | 同时跨行、跨列的混合表 |

A simple table may have many rows and columns. Wrapped text, blank repeated
labels, indentation and outside captions are not evidence of merged cells.
Actual header cells inside the logical grid count. These are image-based model
judgments, not a claim that all original HTML spans were preserved by rendering.

## Charts and composite visuals

The complete allowed categories are defined in
[`configs/visual_taxonomy.json`](../configs/visual_taxonomy.json). They distinguish
bar orientation/grouping/stacking, line graphs with bands or error bars,
distributions, point plots, spatial fields, matrices, polar/radial diagrams,
networks, 3D plots and composite figures. The classifier chooses the closest
supported category based on visible marks rather than guessing from the subject.
Same-type small multiples retain their underlying type. `Mixed Chart` is used
when substantial heterogeneous panels coexist without a dominant type. Minor
annotations are not enough to turn a chart into a composite.

In the evaluation archive, `visual_classification.json` provides per-case
secondary types, panel layout/count, evidence, ambiguity notes, model confidence,
image hash and API-request fingerprint. Confidence is not calibrated accuracy;
labels are model-generated and are not advertised as human-certified.

## Reproduce the classification

```bash
python -m scripts.final_benchmark.classify_visuals \
  --dataset PATH_TO_DATASET --work data/visual_classification/gpt6_v1 --workers 2
python -m scripts.final_benchmark.review_visual_classes \
  --dataset PATH_TO_DATASET --work data/visual_classification/gpt6_v1
python -m scripts.final_benchmark.publish_visual_classes \
  --source PATH_TO_DATASET --work data/visual_classification/gpt6_v1 \
  --output NEW_DATASET_DIRECTORY
```

Calls use local `OPENAI_API_KEY` / `OPENAI_BASE_URL`, with the inference model
pinned to `gpt-6-astra`. The English classifier prompt is in
[`visual_classification_prompt.txt`](../scripts/final_benchmark/visual_classification_prompt.txt).
Raw responses and usage stay outside the public dataset. Publishing fails on
missing case classifications, invalid taxonomy labels or input-image hash drift.
The metadata revision has its own canonical reference hash; existing running
experiments keep their frozen reference snapshots.
