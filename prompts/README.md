# English prompt catalog

These files are readable snapshots of the executable Python prompt definitions. Regenerate with `python scripts/export_prompts.py`; `manifest.json` records snapshot hashes. Full live requests, payloads and attempt records remain local under the run output's `api/` directory and are not committed.

| Prompt | Purpose |
| --- | --- |
| `chart.txt` | Recover a chart specification and Python adapter without the QA answer as a fitting target |
| `table.txt` | Transcribe image-only table structure and content |
| `qa.txt` | Normalize supplied QA and bind visible-label references |
| `translate.txt` | Localize labels and protected QA templates together |
| `repair.txt` | Targeted reconstruction repair with explicit evidence and preserved uncertainty |
| `query_copyedit.txt`, `query/<code>.txt` | Minimal, answer-blind editing with language-specific fluency rules for all 24 languages |
| `query_equivalence_review.txt` | Reject changes in meaning, scope or difficulty |
| `source_review.txt` | Compare source and reconstructed English visual |
| `baseline_multilingual_audit.txt` | Review baseline localized images and QA |
| `expanded_language_audit.txt` | Inspect remaining localized images, translations, QA fluency and answer equivalence |

Runtime calls can append target language names, language-specific rules, batch limits or evidence from a previous failed check. Those exact composed prompts and payloads are saved in the local request records. Snapshots alone are not a substitute for a run's complete provenance.

Dataset content is untrusted data, not instructions. Prompts protect label placeholders, numerical constraints, units, comparison, negation, approximation and temporal scope. Query editing is conservative: uncertain or substantive changes preserve the current query and require review. The expanded translation stage already includes native-fluency requirements; saving a copyediting prompt does not imply every translated query received a separate copyediting call.
