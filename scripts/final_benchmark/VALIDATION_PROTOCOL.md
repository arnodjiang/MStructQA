# Validation protocol

## Files and admission

`val.candidates.jsonl` contains all 3,968 constructed configurations. `val.jsonl` contains only configurations passing mechanical checks and the automated source, reference-answer, QA-format, translation and image-readability review. `val.needs_review.jsonl` retains all other configurations with reasons. This is automated screening, not human certification. Review uses the configured generation provider/model, so correlated errors remain possible. Report candidate and admitted counts separately and recompute diversity on the admitted split.

Resolve `image_path` and `code_path` relative to the JSONL directory (`validation_release`); paths start with `../cases/`. IDs are immutable variant hashes; base_id identifies the original QA. Keep all variants sharing a figure/document split_group_key in the same split. These files designate validation only; no independently disjoint training/test split is asserted. Upstream sources can themselves be train/test datasets. Do not use this validation set for training if reporting validation performance.

Difficulty is an estimated easy/medium/hard annotation: easy = direct retrieval, medium = single comparison/arithmetic/count operation or moderate grounding, hard = dependent operations, dense or cross-panel grounding, or approximate interpretation. It is not measured model difficulty.

Chart types are multi-label annotations: a multi-panel figure may contain line, scatter, bar, heatmap and other types simultaneously. Table classes are mutually exclusive: row_spanning (rowspan>1 only), column_spanning (colspan>1 only), mixed (both), simple (neither). Simple means ordinary unmerged cells, not a table of one row and one column. Synthetic title/note cells are excluded; source footnote spans remain part of source structure. Classification describes reconstructed structure; source fidelity is reviewed separately.

## Dataset quality metrics

Report counts with denominators, separately for candidate and admitted data:

- Source fidelity pass rate: base cases with reviewer source_fidelity=pass / all 128 base cases. Pending/uncertain are not passes.
- Answer preservation pass rate: base cases whose source and reconstruction support the supplied answer / 128.
- Normal-QA pass rate: concise answerable QA cases / 128; descriptive, choice-letter-only, ambiguous and conversational examples are flagged.
- Translation equivalence rate: (base case, language) pairs passing translation and answer equivalence / 1,408. This is API-assessed equivalence, not human accuracy.
- Render validity rate: distinct images with valid hashes, glyph coverage and bounds / 1,408. Readability and layout overlap require separate semantic review; bounds alone are insufficient.
- Reference binding rate: variants whose query/answer match the language-specific label dictionaries and contain no unresolved placeholders / 3,968.
- Admission rate: accepted variants / 3,968. Also report retained base cases and sources; do not hide filtering-induced loss of diversity.
- Diversity: unique sources, chart types, table classes, reasoning operations, difficulty and language configurations; report counts per BASE CASE for source/type/difficulty, not inflated variant counts. For a categorical partition optionally report normalized entropy H=-sum(p log p)/log K (K>1). Multi-label chart categories need per-label prevalence, not an ordinary mutually exclusive entropy.

## Model evaluation

1. Freeze reference normalization before evaluating predictions. Use Unicode NFC and trim outer whitespace; preserve case-sensitive identifiers, signs, units, digits and internal mathematical syntax. Do not translate predictions before scoring: requested-language compliance is measured separately.
2. Primary metric: exact answer accuracy after the declared normalization (EM). Apply locale-aware numeric parsing only where unit, decimal separator and grouping rules are unambiguous. Numeric equality requires compatible units; do not convert percentages or currencies by guessing.
3. Approximate numerical questions: declare the upstream task's tolerance per case before evaluation. When no documented tolerance exists, keep exact scoring or exclude from tolerance-based results pending annotation. Do not choose tolerances from model predictions or to admit reconstruction errors. Report numeric relative/absolute error as secondary diagnostics, explicitly handling zero references.
4. Lists: use order-sensitive exact comparison if order is requested, otherwise multiset exact match. Structured answers use a frozen schema. Boolean answers use reviewed language-specific yes/no mappings. Long explanations are not an exact-match reference; curate concise references before admitting them.
5. Report micro EM over variants, base-case macro EM (mean per-case accuracy), and macro EM across sources and languages. Disaggregate by image language, query language, answer language, monolingual/cross_en/cross_zh, difficulty, chart types, table classes and reasoning operation. Provide denominators; empty groups are N/A.
6. Cross-language gap: on matched base cases and fixed image language v, compare same-language QA accuracy A(v,v,v) with A(en,v,en) or A(zh,v,zh). Report their difference in percentage points. Exclude duplicate monolingual configurations and compare only matched admitted configurations.
7. Language compliance rate: textual responses written in the requested answer language / responses with enough linguistic content to judge. Numbers, proper identifiers and mathematical expressions are language-neutral and excluded from that denominator. Report answer correctness separately from compliance.
8. Consistency: within a base case, proportion of available language configurations answered correctly, plus all-configurations-correct rate on complete 31-variant groups. Never count repeated language variants as independent original questions.
9. Confidence intervals: bootstrap connected components formed by shared figure/document split_group_keys, not individual variants (e.g., 2,000 resamples, declared seed, 95% percentile intervals). Macro groups and model comparisons use the same resampled components.

## Suggested appendix text (use after full audit completion)

We screened all constructed validation candidates using deterministic identity, language-binding, image-integrity, and rendering checks, followed by an automated audit of source fidelity, reference-answer preservation, translation equivalence, and visual readability across eleven languages. Uncertain or failed candidates were retained in a separate review file and excluded from the screened validation split. Chart types were annotated as multiple labels, while table structure was classified from row and column spans into row-spanning, column-spanning, mixed, and unmerged tables. Difficulty labels reflect a predefined reasoning and visual-grounding rubric rather than empirical model performance. We report exact-match accuracy with source- and language-macro averages, matched cross-language accuracy gaps, and confidence intervals obtained by resampling source figure/document groups. Automated screening is not a substitute for bilingual human verification.
