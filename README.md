# MStructQA

**MStructQA: A Multilingual Benchmark for Chart and Visual Tabular Question Answering in MLLMs**

> **Work In Progress** — Code and prompts for a research construction pipeline. The paper title, dataset composition and evaluation protocol are provisional. The 24-language dataset is under construction and review; no finalized dataset or model leaderboard is released here.

MStructQA studies how multimodal large language models (MLLMs) understand charts and visual tables across languages. It constructs controlled language variants of the same source question and numerical/structural content, supporting same-language QA and Chinese/English questions about visuals in other languages.

## Benchmark overview

### 24 languages

| Code | Language | Code | Language | Code | Language |
| --- | --- | --- | --- | --- | --- |
| en | English | zh | Simplified Chinese | ja | Japanese |
| ko | Korean | fr | French | de | German |
| es | Spanish | pt | Portuguese | ru | Russian |
| ar | Arabic | hi | Hindi | it | Italian |
| nl | Dutch | pl | Polish | tr | Turkish |
| vi | Vietnamese | id | Indonesian | th | Thai |
| sw | Swahili | fa | Persian | ur | Urdu |
| bn | Bengali | ta | Tamil | te | Telugu |

The initial eleven-language version uses en, zh, ja, ko, fr, de, es, pt, ru, ar and hi. The expansion adds the remaining thirteen. A multilingual visual means parallel localized versions of a chart/table, not a requirement to mix all languages in one image.

### Evaluation settings

| Setting | Visual language | Query / answer language | Configurations per base QA |
| --- | --- | --- | ---: |
| Same-language | Each language | Same as visual | 24 |
| Chinese cross-language | Each language except Chinese | Chinese | 23 |
| English cross-language | Each language except English | English | 23 |

For **L** languages including Chinese and English, each base QA has **3L − 2** unique configurations. Chinese–Chinese and English–English cases are counted once. Other all-to-all query pairs and independent answer-language permutations are outside the current design.

| Construction scale | Initial 11 languages | Expanded 24 languages |
| --- | ---: | ---: |
| Base QA in the current development selection | 128 | 128 |
| Per-case visual-language artifacts | 1,408 | 3,072 |
| Configurations per base QA | 31 | 70 |
| Candidate QA configurations | 3,968 | 8,960 |

**These are construction targets, not accepted-example counts.** The final paper-scale dataset size is not fixed by this development selection. Language variants are dependent observations of the same base QA; source figures/tables/documents must stay grouped across splits. Visual artifacts can be deduplicated when multiple questions share a source visual.

### Upstream sources

| Source | Collected split/configuration |
| --- | --- |
| [TableVQA-Bench](https://huggingface.co/datasets/terryoo/TableVQA-Bench) | fintabnetqa, vtabfact, vwtq, vwtq_syn |
| [CharXiv](https://huggingface.co/datasets/princeton-nlp/CharXiv) | validation |
| [ChartQAPro](https://huggingface.co/datasets/ahmed-masry/ChartQAPro) | test |
| [Visual-TableQA](https://huggingface.co/datasets/AI-4-Everyone/Visual-TableQA) | train, validation, test |
| [ChartQA](https://huggingface.co/datasets/HuggingFaceM4/ChartQA) | test |
| [MMTU](https://huggingface.co/datasets/MMTU-benchmark/MMTU) | upstream train split |

Collection does not imply admission to a held-out test set. Multiple questions per row, contextual turns and nonvisual table tasks require explicit selection and conversion. [Pinned public revisions and file hashes](configs/upstream_manifest.json) support local download. Dataset files are not redistributed in this code repository.

## Construction pipeline

1. **Collect and freeze:** download pinned sources, verify hashes, select candidates and assign stable identities/provenance.
2. **Recover a visual specification:** prefer structured table cells; otherwise ask the configured multimodal API for chart reconstruction or table transcription. Never use the reference answer as a reconstruction fitting target.
3. **Link QA to labels:** normalize the supplied reference without solving the question; protected `[[label_key]]` references connect question templates and visible labels.
4. **Localize through the API:** translate labels and linked QA together with English prompts and native-language fluency constraints. Preserve numbers, units, comparison, negation, approximation and temporal scope.
5. **Render deterministically:** render the frozen data and translated labels in Python. Tables share a layout measured across all languages; complex scripts use shaping, bidirectional layout and covering fonts.
6. **Review and export:** check geometry, glyphs, references, numerical consistency, source fidelity and translation meaning. Export candidate/screened JSONL, PNGs, standalone rendering code, audit records and a gallery.

The API handles semantic recovery, translation, query editing and review. Local code handles deterministic rendering, validation, caching and export. Exported plotting scripts are **reconstructed code**, not the upstream authors' original plotting source. Successful translation cannot override a failed source audit.

## Quick start

Use Python 3.11+ for a fresh environment, `curl`, and Unicode fonts covering your scripts. The renderer was developed on macOS; read the [platform/font notes](docs/SETUP.md) for other environments.

```bash
git clone https://github.com/arnodjiang/MStructQA.git
cd MStructQA
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env locally: API key, base URL and a supported model.
python scripts/run_pipeline.py --help
```

The provider must support an OpenAI-compatible **Responses API**, image input and sufficient context/output length. A configured model name does not establish provider support. `.env`, local data and logs are excluded from Git.

```bash
python scripts/run_pipeline.py download
python scripts/run_pipeline.py prepare
python scripts/run_pipeline.py baseline --workers 4
python scripts/run_pipeline.py baseline-audit --workers 4
python scripts/run_pipeline.py expand --workers 4
python scripts/run_pipeline.py expand-audit
python scripts/run_pipeline.py finalize
```

API stages consume provider quota and can take substantial time. Default outputs: `data/visual_benchmark/baseline_11/` and `data/visual_benchmark/mstructqa_24/`. Use `--baseline` / `--output` to select other directories. Fresh model calls are not guaranteed to reproduce an earlier research run exactly; retain cached specifications and rendering snapshots for exact reproduction.

Inspect failures before resuming with `--retry-failed`. Connection/timeout errors, HTTP 429 and HTTP 5xx receive up to **10 retries**, **5 seconds** apart, after the initial attempt. Exhaustion records the failure and lets the batch process the next item. Malformed/incomplete content and authentication failures are not automatically retried. Attempts are retained locally, without a global connection-error circuit breaker.

An API-free synthetic example and stage/output details are in [Setup](docs/SETUP.md).

## Code, prompts and documentation

- [Prompt catalog](prompts/README.md): English recovery, QA, translation, per-language copyediting and review prompts.
- [Design](docs/DESIGN.md): research questions, preservation rules, quality gates and evaluation limits.
- [Dataset card](docs/DATASET_CARD.md): sources, scope, status and limitations.
- [`scripts/run_pipeline.py`](scripts/run_pipeline.py): public staged entry point.
- [`scripts/final_benchmark/`](scripts/final_benchmark/): construction, expansion, auditing, rendering, export and scoring.
- [`skills/multilingual-visual-benchmark/`](skills/multilingual-visual-benchmark/): reusable harness, adapter contract and synthetic examples.

Some research paths and environment variables retain the earlier internal name `MVisQA` for compatibility. The public project name is **MStructQA**.

## Status and licensing

**Work In Progress.** No acceptance, benchmark scores, final test-set size or human certification is claimed. Automated review can use the same model as generation; it is not independent human validation. Source recovery, translation, readability, dataset overlap and scoring remain research risks.

Local runs expose `status.json`, `expansion_audit/progress.json` and, after finalization, `completion.json`. Candidate and screened outputs remain separate.

See [CONTRIBUTING.md](CONTRIBUTING.md). Code is MIT-licensed, with the bundled harness's existing notice retained. Upstream datasets, derived records, fonts and provider terms are separate. This repository grants no redistribution rights over those assets.
