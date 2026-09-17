# Evaluate new models on another server

The code is hosted at [GitHub](https://github.com/arnodjiang/MStructQA) and the
current data at [Hugging Face](https://huggingface.co/datasets/arnodjiang/MStructBench).
MStructQA is the project title; MStructBench is the Hugging Face repository ID.
No previous predictions or private evaluation checkpoints are needed to evaluate
a new model. Use a new output directory for every model/configuration.

## Install and download

```bash
git clone https://github.com/arnodjiang/MStructQA.git
cd MStructQA
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m scripts.distribution.download
```

The downloader retrieves `artifacts/mstructqa-current.tar.gz`, verifies its
checksum, validates the canonical reference JSONL and all image hashes, and
extracts to `data/visual_benchmark/final_128_24lang_v4_context`. It refuses to
overwrite an existing directory. For a fixed data version add
`--revision <HF_COMMIT_SHA>`; record `git rev-parse HEAD` for the code version.
The rendered images are ready to use: evaluating them does not require fonts,
rendering, translation or regeneration. Rendering from code additionally needs
the fonts described in [SETUP.md](SETUP.md).

For the standard Hugging Face image dataset interface:

```python
from datasets import load_dataset
qa = load_dataset('arnodjiang/MStructBench', split='validation')
print(qa[0]['query'])
image = qa[0]['image']
```

## Credentials and model selection

Edit `.env` locally. Never commit or upload credentials.

- OpenAI-compatible **Responses API**: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.
- Native Gemini through Token Router: `TOKEN_ROUTER_API_KEY`, `TOKEN_ROUTER_BASE_URL`.
- Independent text judge: set `JUDGE_MODEL=gpt-6-astra`; optionally set
  `JUDGE_BASE_URL` and `JUDGE_API_KEY`. Blank judge URL/key inherit `OPENAI_*`.

The inference provider must support the selected model and image input. The
OpenAI adapter uses Responses, not Chat Completions. Token Router uses native
`generateContent`. A local MLLM can implement the same image + query + optional
source-context contract; these commands assume one of those two APIs.

## Run a new OpenAI-compatible model

Replace `YOUR_MODEL` and `your_model` with the model ID and a filesystem-safe run
name. This command saves predictions and token usage, then runs the configured
text judge and updates that model's LaTeX row after all samples are judged.

```bash
mkdir -p logs
nohup .venv/bin/python -u -m scripts.evaluation.run \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/your_model \
  --model YOUR_MODEL --workers 3 --request-interval 3 \
  --llm-judge --judge-model gpt-6-astra \
  --publish-table paper/tables/main_results.tex \
  > logs/your_model.log 2>&1 &
echo $!
```

## Run a new native Gemini model

Replace `google/YOUR_MODEL` with the provider's model ID. Keep the same
`JUDGE_MODEL=gpt-6-astra` for comparisons. Ten requests/minute is accommodated by
a global 6.5-second interval, including retries, with two workers.

```bash
mkdir -p logs
nohup .venv/bin/python -u -m scripts.evaluation.run_token_router \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/evaluation/your_gemini_model \
  --model google/YOUR_MODEL --workers 2 --request-interval 6.5 \
  --llm-judge > logs/your_gemini_model.log 2>&1 &
echo $!
```

Once the judge is finished, publish its row:

```bash
python -m scripts.evaluation.publish_results \
  --judge-dir data/evaluation/your_gemini_model/llm_judge_text_v2 \
  --table paper/tables/main_results.tex --expected-judge gpt-6-astra
```

Quota exhaustion stops further submissions. After restoring credit, rerun the
same command with `--retry-failed` for Token Router. Existing successful answers
are reused; historical attempts remain in usage accounting. Do not run two
processes against the same output directory.

## Inspect progress and results

```bash
cat data/evaluation/your_model/progress.json
cat data/evaluation/your_model/llm_judge_text_v2/progress.json
cat data/evaluation/your_model/llm_judge_text_v2/scores.json
```

There are 8,960 QA across 70 configurations per base question. Main-table AVG is
the macro-average of those 70 configurations. Deterministic matches bypass the
judge; non-matches receive text-only equivalence judging. Missing/failed answers
count as incorrect. Strict preliminary scores and final semantic scores are
separate outputs; use `llm_judge_text_v2/scores.json` for the final main table.
Inference and judge usage are recorded separately. Provider-reported token
counts do not directly establish monetary charges.

## Rebuild or publish the data distribution

```bash
python -m scripts.distribution.export_hf \
  --dataset data/visual_benchmark/final_128_24lang_v4_context \
  --output data/hf_publish/MStructBench
cp scripts/distribution/HF_README.md data/hf_publish/MStructBench/README.md
hf auth login
python -m scripts.distribution.publish_hf
```

The public distribution includes current data only. API credentials, model
predictions, raw API logs and evaluation checkpoints are not uploaded. Original
source-image/model-output archives remain private research artifacts; the
released data retains stable IDs and source provenance for alignment.
