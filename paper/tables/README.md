# Main results table

`main_results.tex` is the drop-in manuscript fragment. In the ACL manuscript preamble, load `booktabs` and `multirow`, then insert:

```tex
\input{paper/tables/main_results}
```

The fragment uses `table*` at `\textwidth`. Title, caption, section, body and float spacing are left unchanged. Only table-local cell padding and font size are set. The model column is centered and displays GPT-6-Astra on one line. The current row contains measured scores from `data/evaluation/gpt6_astra_v3_repair_20260916/llm_judge_text_v2/scores.json`, rescored on September 16, 2026.

The evaluated cohort contains 8,960 candidate QA configurations, including 8,958 returned answers and two connection failures. Failures count as incorrect. The cohort has not yet been fully verified by human review. The metric accepts exact numeric or normalized text matches first, then uses a text-only GPT-6 Astra Judge for mismatches. Only equivalent answers count as correct; unconfirmed equivalence and inference failures count as incorrect. Judge receives the question, reference, candidate answer and expected answer language, without images or reconstructed table data. The current v3 run records 7,210 correct answers: AVG 80.46875%, XQA-ZH 78.90625%, and XQA-EN 81.0801630435%. The 70 repaired radial configurations were rerun; unchanged predictions were reused. The Judge and evaluated model are the same, which should be disclosed when reporting automated semantic accuracy.

- **XQA**: cross-language QA. ZH and EN are question/answer languages. Each score is a macro-average over the other 23 visual languages.
- **LQA**: language-aligned QA. EN, ZH, JA, KO, FR, DE, ES, PT, RU, AR, HI, IT, NL, PL, TR, VI, ID, TH, SW, FA, UR, BN, TA and TE denote the same visual/question/answer language.
- **AVG**: `(23 * XQA_ZH + 23 * XQA_EN + sum(LQA_language)) / 70`. Do not directly average the 26 displayed scores.

Use a frozen evaluation cohort with aligned source examples across configurations. Declare the correctness rule separately, including numeric tolerances or accepted alternatives if used. Missing configuration scores must not be treated as zero. Report coverage when screening varies. Per-source, chart/table and task-type breakdowns can be added as row blocks using the same columns.

Use percentage scores with one decimal, without repeating `%` in every cell; `100` may be displayed without a fractional part to save width. Compute all aggregates before rounding. Consider a two-panel language layout if more precision or wider model names make the complete row hard to read at print size.

The PDF was compiled with the current official generic ACL style retrieved from https://raw.githubusercontent.com/acl-org/acl-style-files/master/acl.sty, not a separately verified ACL 2027-specific template. Formatting guidance: https://acl-org.github.io/ACLPUB/formatting.html. The one-page proof wrapper places the table block above two-column explanatory text; use the `table*` fragment directly in the actual manuscript.

Rebuild the proof from the repository root (requires TeX Live and an official `acl.sty` on the TeX search path):

```bash
TEXINPUTS=tmp/pdfs/acl-main-table: pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory=tmp/pdfs/acl-main-table paper/main_table_preview.tex
```

Table design and the explanatory proof were assisted by Codex. This table update reads completed inference and Judge outputs; it makes no new API calls.

GPT-5.6-Sol is submitted against the same v3 cohort. Its pending row uses dashes; the completed text-only GPT-6 Astra Judge results will replace only that row automatically. Existing GPT-6 Astra scores remain unchanged.
