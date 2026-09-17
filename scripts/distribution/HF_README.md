---
pretty_name: MStructQA
language:
- en
- zh
- ja
- ko
- fr
- de
- es
- pt
- ru
- ar
- hi
- it
- nl
- pl
- tr
- vi
- id
- th
- sw
- fa
- ur
- bn
- ta
- te
task_categories:
- visual-question-answering
size_categories:
- 1K<n<10K
license: other
license_name: source-specific-terms
license_link: https://github.com/arnodjiang/MStructQA/blob/main/docs/DATASET_CARD.md#licensing
multilinguality:
- multilingual
tags:
- chart-question-answering
- visual-table-question-answering
- multilingual
- evaluation
configs:
- config_name: default
  data_files:
  - split: validation
    path: data/validation-*.parquet
---

# MStructQA

**MStructQA: A Multilingual Benchmark for Chart and Visual Tabular Question Answering in MLLMs**

[Code, prompts and evaluation](https://github.com/arnodjiang/MStructQA) · [Server setup](https://github.com/arnodjiang/MStructQA/blob/main/docs/SERVER_MIGRATION.md)

`arnodjiang/MStructBench` is the dataset repository for the **MStructQA** project.
It contains the current 24-language release: 128 base questions, 3,072 localized
visuals and 8,960 distinct QA configurations. The single `validation` split is an
evaluation split; no training split is provided. Images are localized
reconstructions of charts and rendered tables, rather than upstream originals.

## Load the dataset

```python
from datasets import load_dataset

ds = load_dataset('arnodjiang/MStructBench', split='validation')
example = ds[0]
image = example['image']      # PIL image; tables are also images
question = example['query']
reference = example['answer'] # scoring only; never include in model input
context = example['source_context']  # empty when no external prose is needed
```

Use a pinned Hub commit via `revision=...` for reproducible experiments.
The evaluation archive under `artifacts/` contains the exact current JSONL,
images, rendering code and metadata expected by the project's evaluation scripts.
Download it with `python -m scripts.distribution.download` after cloning the code.
`release.json` records file checksums and the canonical reference snapshot hash.

## Languages and settings

English (EN), Simplified Chinese (ZH), Japanese (JA), Korean (KO), French (FR),
German (DE), Spanish (ES), Portuguese (PT), Russian (RU), Arabic (AR), Hindi (HI),
Italian (IT), Dutch (NL), Polish (PL), Turkish (TR), Vietnamese (VI), Indonesian
(ID), Thai (TH), Swahili (SW), Persian (FA), Urdu (UR), Bengali (BN), Tamil (TA)
and Telugu (TE).

- **LQA:** visual, question and answer use the same language: 24 configurations per base QA.
- **XQA-ZH:** Chinese question/answer with each of the other 23 visual languages.
- **XQA-EN:** English question/answer with each of the other 23 visual languages.

These are 70 distinct configurations per base QA. Aligned Chinese/English
configurations are counted once in LQA. Report each LQA language separately and
macro-average each XQA pivot over its 23 visual languages. **AVG** is the macro
average over all 70 configurations, not the unweighted mean of the 26 displayed
LQA/XQA columns. All language variants of a source question share a base ID.

## Fields

| Field | Meaning |
| --- | --- |
| `id`, `base_id`, `case_id` | Stable configuration, base QA and visual-case identifiers |
| `image` | Embedded PNG, automatically decoded by Datasets |
| `query`, `answer` | Current question and reference answer |
| `query_language`, `image_language`, `answer_language` | ISO 639-1 language codes |
| `configuration` | Original setting identifier; language fields define LQA/XQA membership |
| `source_context` | Translated external document prose; empty if absent |
| `source` | Upstream dataset |
| `visual_kind` | Fine-grained GPT-6 visual category, such as Grouped Bar Chart or Column-Spanning Table |
| `visual_family` | Legacy coarse chart/table grouping for compatible evaluation cohorts |
| `image_sha256` | Checksum of the exact image bytes |
| `metadata_json` | Lossless canonical reference row, including provenance and automated audit flags |

Only the question, image and optional source context are inference inputs. Do not
send answers, provenance or audit annotations to the model. External prose is
translated into the question language. Table contents remain in the image and
are not transcribed into the prompt. For exact prompt serialization, use
`scripts.evaluation.context_input.input_text` on `json.loads(metadata_json)`.

## Visual categories

`visual_kind` is classified by GPT-6 Astra from one current English image per base
case and shared across its localized variants. It describes the visible chart
type or table merge structure; questions and answers are not classifier inputs.
Tables use **Simple Table**, **Row-Spanning Table**, **Column-Spanning Table** or
**Mixed-Spanning Table**. Simple means no merged rows/columns, not a one-cell table.
Charts use a more specific vocabulary for bars, lines, distributions, spatial
fields, diagrams and composites. `visual_family` retains the legacy chart/table
cohort. See [taxonomy definitions](https://github.com/arnodjiang/MStructQA/blob/main/docs/VISUAL_TAXONOMY.md).
The exact archive includes `visual_taxonomy.json` and `visual_classification.json`
with per-case evidence, secondary types, layout and model confidence. These are
model-generated annotations, not human certification. The change affects metadata
only: images, queries, reference answers and source context are unchanged.

## Sources and construction

| Source | Base questions | QA configurations |
| --- | ---: | ---: |
| [CharXiv](https://huggingface.co/datasets/princeton-nlp/CharXiv) | 48 | 3,360 |
| [ChartQAPro](https://huggingface.co/datasets/ahmed-masry/ChartQAPro) | 27 | 1,890 |
| [TableVQA-Bench](https://huggingface.co/datasets/terryoo/TableVQA-Bench) | 22 | 1,540 |
| [ChartQA](https://huggingface.co/datasets/HuggingFaceM4/ChartQA) | 12 | 840 |
| [Visual-TableQA](https://huggingface.co/datasets/AI-4-Everyone/Visual-TableQA) | 10 | 700 |
| [MMTU](https://huggingface.co/datasets/MMTU-benchmark/MMTU) | 9 | 630 |

The pipeline selects source-linked QA, reconstructs visuals, localizes labels and
linked QA, conservatively rewrites questions, renders images, and verifies
numerical structure and source alignment. Five source cases include external
prose (four MMTU/FinQA and one ChartQAPro), localized across all 24 languages;
these affect 350 QA configurations. Current-only exports omit historical
questions, previous labels, old data versions and model predictions. Source
revision, row and file identifiers are retained for attribution and tracing.

## Evaluation

First apply deterministic answer matching. Non-matching predictions are judged
for answer equivalence by a separately configured, text-only LLM judge.
The project experiments use GPT-6 Astra as judge. Only `equivalent` receives
credit; `different` and uncertain outcomes are incorrect. Failed/missing
predictions count as incorrect in the fixed denominator. Record the inference
and judge models, prompts, token usage, request counts and release revision.

## Quality and limitations

This release contains the full candidate cohort, including records flagged
`needs_review` by automated checks; it is not a claim that every record passed
human verification. Inspect `metadata_json` for audit status. Reconstruction,
translation, source ambiguity and script rendering may affect results. Automated
review is not independent human certification. The 128 base questions and their
correlated language variants are not 8,960 independent source observations.
Upstream overlap and potential model exposure should be considered when
interpreting scores. No original-image baseline is implied by these results.

## Licensing

The code repository uses MIT. Dataset examples remain subject to their
respective upstream terms; **MIT does not apply to the combined dataset**.
The `other` license tag denotes source-specific terms, not a new blanket grant.
Consult the six linked upstream dataset cards and the retained per-example
provenance before reuse or redistribution. Cite the applicable upstream sources
alongside MStructQA.

## Citation

```bibtex
@misc{mstructqa,
  title = {MStructQA: A Multilingual Benchmark for Chart and Visual Tabular Question Answering in MLLMs},
  howpublished = {\url{https://github.com/arnodjiang/MStructQA}},
  year = {2026}
}
```

This is a repository citation; no accepted venue or publication DOI is asserted.

## Observed visual types

The current release contains 32 primary types. Counts are base cases; each case contributes 70 QA configurations.

| Type | Base cases | QA |
| --- | ---: | ---: |
| Multi-Series Line Graph | 23 | 1610 |
| Simple Table | 20 | 1400 |
| Column-Spanning Table | 15 | 1050 |
| Mixed Chart | 9 | 630 |
| Grouped Bar Chart | 5 | 350 |
| Line Graph with Uncertainty Bands | 5 | 350 |
| Heatmap | 4 | 280 |
| Line Graph | 4 | 280 |
| Pie Chart | 4 | 280 |
| Horizontal Bar Chart | 3 | 210 |
| Mixed-Spanning Table | 3 | 210 |
| Stacked Bar Chart | 3 | 210 |
| Area Chart | 2 | 140 |
| Bar-Line Combination Chart | 2 | 140 |
| Chart-Table Composite | 2 | 140 |
| Cumulative Distribution Plot | 2 | 140 |
| Density Plot | 2 | 140 |
| Diverging Bar Chart | 2 | 140 |
| Line Graph with Error Bars | 2 | 140 |
| Phase Diagram | 2 | 140 |
| Row-Spanning Table | 2 | 140 |
| Scatter Plot with Error Bars | 2 | 140 |
| 3D Streamline Plot | 1 | 70 |
| Bubble Chart | 1 | 70 |
| Confusion Matrix | 1 | 70 |
| Contour Plot | 1 | 70 |
| Correlation Matrix | 1 | 70 |
| Histogram | 1 | 70 |
| Lollipop Chart | 1 | 70 |
| Scatter Plot | 1 | 70 |
| Table-Diagram Composite | 1 | 70 |
| Vertical Bar Chart | 1 | 70 |
