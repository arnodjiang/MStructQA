# Supplementary context audit

The audit examines all downloaded Parquet schemas and non-image fields, then
checks the 128 selected source records against their exact file/row entries.
Its scope is the locally downloaded versions, not unseen material on the web.

| Source | Selected QA | QA requiring prose restoration | Configurations |
| --- | ---: | ---: | ---: |
| CharXiv | 48 | 0 | 0 |
| ChartQA | 12 | 0 | 0 |
| ChartQAPro | 27 | 1 | 70 |
| MMTU | 9 | 4 | 280 |
| TableVQA-Bench | 22 | 0 | 0 |
| Visual-TableQA | 10 | 0 | 0 |

The selected ChartQAPro case `807df4112e73625d5bb9` (test row 851, zero-based)
contains 607 words in `Paragraph`, including the survey population size. This
field is source prose and is preserved in full, without using the answer to
select sentences. In the downloaded full ChartQAPro split, 262 of 1,948 rows
have nonempty paragraphs; only one belongs to the current selection.

ChartQAPro's `Year` field is an evaluation flag for year-based answers, as stated
in the [official evaluation instructions](https://github.com/vis-nlp/ChartQAPro#-evaluation-instructions).
It is excluded together with answers and nonselected QA history. All 27 selected
ChartQAPro entries contain one question, so no conversational history is missing
from these inputs.

CharXiv supplies figure provenance, layout annotations, and other QA labels, but
no separate document paragraph in the downloaded schema. Other QA answers must
not be added as context. ChartQA and Visual-TableQA similarly have no separate
source-prose field in their downloaded schemas.

TableVQA-Bench's HTML and Markdown are table representations, not extra reading
material. All 22 selected HTML tables were checked for text outside the table;
none was found. Two contain captions, and both captions already exist as
`table_title` rows in the render specification. They are not duplicated into the
text prompt. This audit does not substitute for checking whether every visual
element has been faithfully reconstructed.

The four MMTU/FinQA cases retain complete `metadata.pre_text` and
`metadata.post_text`. QA labels, programs, reasoning, and gold evidence selectors
are excluded. Source-context translation follows the question language and keeps
numeric strings protected. All original and repaired conditions remain traceable.

Reproduce the audit without API calls:

```bash
python -m scripts.final_benchmark.audit_context \
  --dataset data/visual_benchmark/final_128_24lang_v3 \
  --output output/analysis/all_datasets_context_audit.json
```

See [context restoration](CONTEXT_RESTORATION.md) for data-only preparation.
Evaluation was subsequently authorized to resume after data completion and
context/current-only release validation; no incomplete dataset is evaluated.
