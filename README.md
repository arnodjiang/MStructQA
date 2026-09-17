# MStructQA

**A Multilingual Benchmark for Chart and Visual Tabular Question Answering in MLLMs**

[Getting Started](#getting-started) · [Benchmark](#benchmark) · [Pipeline](#construction-pipeline) · [Dataset](https://huggingface.co/datasets/arnodjiang/MStructBench) · [New-server evaluation](docs/SERVER_MIGRATION.md) · [Prompts](prompts/README.md) · [Documentation](#documentation)

MStructQA provides a **24-language** benchmark construction framework for evaluating how multimodal large language models understand charts and visual tables. It pairs localized visuals with questions and reference answers while preserving the underlying numerical data, table structure and question intent.

The project supports same-language visual question answering and cross-language evaluation with Chinese or English questions. This repository includes the generation pipeline, English prompts, rendering tools, quality checks and reproducible export utilities.

## Highlights

- **24 languages:** parallel localized charts, tables, questions and answers.
- **Three evaluation settings:** same-language QA, Chinese cross-language QA and English cross-language QA.
- **Linked visual and textual references:** protected label keys connect questions to the labels used for rendering.
- **Reproducible visual construction:** frozen specifications, standalone Python renderers, source provenance and artifact hashes.
- **Explicit quality checks:** numerical consistency, typography, layout, source fidelity and translation review.
- **Resumable execution:** request caching, recorded attempts and bounded transport retries.

## Benchmark

### Languages

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

Each source visual is localized into separate language versions. Numerical content and structural relationships remain aligned across versions; a single image is not required to contain multiple languages.

### Evaluation settings

| Setting | Visual language | Query language | Answer language |
| --- | --- | --- | --- |
| Same-language QA | Any supported language | Same as visual | Same as query |
| Chinese cross-language QA | Any supported language except Chinese | Chinese | Chinese |
| English cross-language QA | Any supported language except English | English | English |

For each base question, the distinct language configurations are `(v, q, q)`, where `v` is the visual language and `q` belongs to `{v, zh, en}`. Chinese–Chinese and English–English configurations are included only once. Other all-to-all language pairs and independently selected answer languages are outside this protocol.

For answers consisting only of ASCII numerals (including signed decimals and comma-grouped thousands), exported questions omit the appended response-language instruction. Answers containing words, units, percentages or lists retain it. The answer-language metadata remains unchanged.

Language variants share their base identity and source provenance. They must remain grouped across evaluation splits rather than being treated as independent source questions.

### Source datasets

| Source | Collected split/configuration |
| --- | --- |
| [TableVQA-Bench](https://huggingface.co/datasets/terryoo/TableVQA-Bench) | fintabnetqa, vtabfact, vwtq, vwtq_syn |
| [CharXiv](https://huggingface.co/datasets/princeton-nlp/CharXiv) | validation |
| [ChartQAPro](https://huggingface.co/datasets/ahmed-masry/ChartQAPro) | test |
| [Visual-TableQA](https://huggingface.co/datasets/AI-4-Everyone/Visual-TableQA) | train, validation, test |
| [ChartQA](https://huggingface.co/datasets/HuggingFaceM4/ChartQA) | test |
| [MMTU](https://huggingface.co/datasets/MMTU-benchmark/MMTU) | upstream train split |

Public revisions and file hashes are recorded in [the upstream manifest](configs/upstream_manifest.json). Collection scope is separate from evaluation eligibility: multi-turn records, multiple questions per row and nonvisual table tasks require explicit selection or conversion.

## Construction pipeline

1. **Collect and select.** Download pinned sources, verify file hashes and assign stable identities and provenance to selected examples.
2. **Recover visual structure.** Prefer structured table cells when available. Otherwise use the configured multimodal API to reconstruct a chart specification or transcribe a visual table, without using reference answers as fitting targets.
3. **Link questions and labels.** Normalize the supplied QA without solving it. Protected `[[label_key]]` references connect question templates with visible labels.
4. **Localize.** Translate labels and linked QA through the API using English prompts and language-specific fluency rules. Preserve quantities, units, comparisons, negation, approximation and temporal scope.
5. **Render.** Generate images deterministically from frozen data and translated labels. Tables use a common layout measured across languages; text rendering supports shaping, bidirectional layout and font fallback.
6. **Review and export.** Validate numerical consistency, label references, glyph coverage, layout, source fidelity and translation meaning. Export candidate and screened QA, images, standalone code and review records.

The API handles semantic reconstruction, translation, query editing and review. Local code handles deterministic rendering, validation, caching and export. Generated plotting scripts are reconstructed renderers, not the upstream authors' original plotting source.

## Getting started

### Installation

Use Python 3.11+, `curl` and fonts covering the requested scripts. See [platform and font configuration](docs/SETUP.md) for rendering requirements.

```bash
git clone https://github.com/arnodjiang/MStructQA.git
cd MStructQA
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL` in your local `.env`. The provider must support an OpenAI-compatible **Responses API**, image input and sufficient context/output length. `.env`, generated data and API logs are excluded from Git.

Optional `JUDGE_MODEL`, `JUDGE_BASE_URL` and `JUDGE_API_KEY` configure answer judging
independently; blank values inherit `OPENAI_*`. The active local benchmark path is
recorded in `configs/benchmark_release.json`; retired revisions are rejected by
the inference runners.

### Evaluate an existing release

```bash
python -m scripts.distribution.download
```

See [server setup and new-model evaluation](docs/SERVER_MIGRATION.md) for background commands, provider configuration, progress files and scoring. No previous evaluation checkpoint is required.

### Run the pipeline

```bash
python scripts/run_pipeline.py download
python scripts/run_pipeline.py prepare
python scripts/run_pipeline.py baseline --workers 4
python scripts/run_pipeline.py baseline-audit --workers 4
python scripts/run_pipeline.py expand --workers 4
python scripts/run_pipeline.py expand-audit
python scripts/run_pipeline.py finalize
```

`baseline` and `expand` are internal construction stages of the 24-language pipeline. Use `--baseline` and `--output` to configure directories, and `--help` to inspect available options. The final output defaults to `data/visual_benchmark/mstructqa_24/`.

Successful API results are cached. After inspecting a failure, use `--retry-failed` to resume. Connection/timeout failures, HTTP 429 and HTTP 5xx receive up to ten retries, five seconds apart, after the initial request. Exhausted requests are recorded and skipped so the batch can process subsequent items. Malformed content and authentication errors are not automatically retried.

### Try an API-free example

```bash
python skills/multilingual-visual-benchmark/scripts/visual_harness.py run \
  --spec skills/multilingual-visual-benchmark/examples/table.json \
  --translations skills/multilingual-visual-benchmark/examples/table_locales.json \
  --languages en,zh,ar --output data/demo
```

This uses synthetic data and checked-in translations. Add `--font /absolute/path/to/font.ttf` when needed.

## Outputs and quality

| Output | Contents |
| --- | --- |
| `benchmark.jsonl` | Candidate QA configurations with provenance and review state |
| `validation_release/val.jsonl` | Examples satisfying the configured automated admission checks |
| `validation_release/val.needs_review.jsonl` | Examples requiring additional review |
| `cases/<id>/images/` | Localized images and layout reports |
| `cases/<id>/code/` | Standalone rendering code with embedded data and labels |
| `reproducible_code.zip` | Packaged renderers and reproduction metadata |

The current dataset is distributed on [Hugging Face](https://huggingface.co/datasets/arnodjiang/MStructBench) as image-bearing Parquet and an exact evaluation archive. This GitHub repository provides the code, prompts and synthetic examples. Follow [new-server evaluation](docs/SERVER_MIGRATION.md) to download the frozen data and evaluate another model without regenerating images or translations.

Source fidelity and localization quality are assessed separately. A successful translation does not override a failed source audit. Automated reviewers can use the same model as generation and do not constitute human certification. Exact reproduction requires the saved specifications, labels, code and fonts; new model calls can produce different results.

## Visual categories

The dataset’s `visual_kind` provides fine-grained GPT-6 image classifications,
including chart subtypes and four table merge structures. `visual_family` retains
the coarse chart/table cohorts. See [visual taxonomy](docs/VISUAL_TAXONOMY.md) for
definitions, classification prompts and reproducibility.

## Evaluation and reporting

Original source identities and unmodified model inputs/outputs are retained in
content-addressed snapshots for paired original-versus-enhanced ablations. See
[source and evaluation provenance](docs/ABLATION_PROVENANCE.md) for identifiers,
preserved artifacts, and the comparison protocol.

This is a benchmark construction and evaluation repository, not a model checkpoint distribution. For evaluation, generate model predictions against a frozen, reviewed export, keep all language variants of each source in the same split, and report results by language, setting and visual type. Report the evaluated denominator and exclusions alongside scores.

The full inference runner sends each current question and localized image to the configured API, saves structured answers and per-attempt token usage, and automatically computes XQA, LQA and AVG when all QA finish. See [evaluation execution and accounting](scripts/evaluation/README.md). Final semantic ACC first applies deterministic matching, then uses a separately configured text-only LLM judge for non-matches. Set `JUDGE_MODEL=gpt-6-astra` to reproduce the current judging setup. Judge inputs contain no images; uncertain decisions count as incorrect.

The preliminary strict-matching scorer is documented in [the evaluation design](docs/DESIGN.md); inspect its arguments with `python -m scripts.final_benchmark.score_val --help`. Numeric tolerances, alternative-answer handling and model-based judges must be explicitly specified and validated for the chosen experiment. The repository does not claim published model rankings or human-validated coverage from automated checks alone.

## Documentation

- [Setup and execution](docs/SETUP.md)
- [Benchmark design and evaluation](docs/DESIGN.md)
- [Dataset card](docs/DATASET_CARD.md)
- [English prompt catalog](prompts/README.md)
- [Rendering adapter contract](skills/multilingual-visual-benchmark/references/contract.md)
- [Contributing](CONTRIBUTING.md)

The implementation is organized under `scripts/final_benchmark/`, with reusable rendering tools and synthetic examples under `skills/multilingual-visual-benchmark/`. Some internal paths retain the identifier `MVisQA` for compatibility.

## Testing

```bash
python -m unittest discover -s tests -v
python -m unittest scripts.final_benchmark.test_contract -v
python -m unittest discover -s skills/multilingual-visual-benchmark/tests -v
```

Portable contracts run in CI without API credentials. Rendering tests additionally require suitable fonts.

## License

Code is available under the [MIT License](LICENSE). The bundled harness retains its existing license notice. Upstream datasets, derived records, fonts and API provider terms are separate; the code license does not grant redistribution rights over those assets.
