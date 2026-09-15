# Design

MStructQA aims to measure multilingual chart and visual-table understanding while controlling the underlying numerical/structural content. Planned analyses compare same-language QA and Chinese/English QA over localized visuals, with breakdowns by language, source, visual type and reasoning operation. These are research aims, not established findings.

## Unit of construction

A base QA has a stable source-derived identity and a visual specification separating numeric data/table geometry from visible labels. Variants retain source grouping and provenance. For language set S containing en and zh, generate the distinct tuples `(v, q, q)` where `v in S` and `q in {v, en, zh}`. This yields `3|S| - 2` configurations. Cross-language queries use the query language's label dictionary; resolving the corresponding label in a differently localized visual is part of the task.

## Preservation

- Recover chart axes, panels and series without using reference answers to tune numerical reconstruction. Retain approximations and unresolved recovery errors.
- Preserve table values, order, blank cells and spans. Prefer structured source tables over OCR.
- Keep label keys and placeholder multiplicity immutable. Preserve quantities, units, operators, negation, comparison sets, aggregation, approximation and temporal scope.
- A value at 10 hours is not a maximum up to 10 hours or a value during the tenth hour. Copyediting may improve grammar/spacing but must not silently resolve ambiguity or repair substantive translation mistakes.
- Equal-value conversion of localized decimal digit glyphs to ASCII retains before/after provenance; it must never recompute an answer.

Semantic generation uses the configured API. Python handles deterministic rendering, validation and export. Native fluency requirements are included in translation prompts. The separate query-copyediting tool supports small edits followed by answer-blind equivalence review; uncertain edits preserve the original question.

## Quality gates

Mechanical checks cover hashes, numerical specifications, label keys, references, numeric tokens, collapsed labels, geometry, missing glyphs, code constants and representative pixel reproduction. These checks do not establish semantic correctness.

API review checks source reconstruction, supplied reference preservation, translation and visual readability. Expanded languages receive their own review. Source failures remain failures. Only candidates satisfying configured admission gates enter `val.jsonl`; unresolved candidates remain in `val.needs_review.jsonl`.

The reviewer may be the same model as the generator. A separate call is not an independent-model experiment or human certification. Human adjudication and agreement measurement remain future work.

## Evaluation

Report candidate and screened denominators, including exclusions by source and language. Keep variants of shared figures/tables/documents in one split. Cluster uncertainty estimates at source-group level; 70 variants are not 70 independent observations. Report language-specific coverage when screening differs across languages.

`score_val.py` implements a preliminary strict matching baseline with clustered uncertainty estimates. Exact match is unsuitable for some numeric approximations, unordered lists and long answers. Any normalization, tolerance or judge-based scoring must be declared and validated before evaluation. Do not invent tolerances to make reconstructed examples pass.
