# MStructQA pipeline modules

This package implements the 24-language construction workflow. Start with the [project README](../../README.md) and [setup guide](../../docs/SETUP.md).

## Entry points

Use `python scripts/run_pipeline.py --help` from the repository root for the public interface. The `baseline` and `expand` stages divide localization and review into manageable internal batches; they are not separate public benchmark versions.

| Module | Responsibility |
| --- | --- |
| `pipeline.py` | Freeze selection, recover visual specifications, normalize linked QA, localize and render |
| `api.py` | Request caching, attempt records and bounded transport retries |
| `prompts.py`, `languages24.py` | Semantic task prompts and language-specific rules |
| `polish_queries.py` | Conservative query copyediting and equivalence review |
| `expand24.py` | Complete all 24 language localizations using frozen specifications |
| `worker.py`, `render_runtime.py` | Offline rendering and layout checks |
| `review.py`, `val_audit.py`, `audit24.py` | Source fidelity and multilingual visual/QA review |
| `export.py`, `finalize24.py` | Candidate/screened records and standalone code export |
| `val_verify.py`, `verify_export.py` | Embedded-data validation and representative pixel reproduction |
| `score_val.py` | Preliminary strict matching and grouped uncertainty estimates |

Successful API results are reused by request fingerprint. Transport failures receive ten retries with a five-second delay; malformed content requires inspection and explicit resumption. See the setup guide for details and resource requirements.

## Reproducibility and admission

Each run retains source identities, numerical/structural specifications, language dictionaries, generated code, image hashes and review records. Exported adapters are reconstructed code rather than upstream plotting source. System fonts and source datasets are not bundled with this package.

Source fidelity and translation quality are separate gates. Candidate records with unresolved issues remain outside the screened set. Automated review does not imply human verification. Read the [design notes](../../docs/DESIGN.md) and [validation protocol](VALIDATION_PROTOCOL.md) before interpreting evaluation results.

Additional modules support targeted repair, diagnostics and local research workflows. Internal directory identifiers are retained for compatibility; the public interface is the root pipeline entry point.
