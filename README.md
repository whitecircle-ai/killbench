# KillBench Collector

Standalone collection codebase for KillBench.

It handles:
- benchmark/test generation with age × profession cross-product
- OpenRouter inference for free-text and structured runs
- Gemini parsing (via OpenRouter) as the canonical parse layer for free-text outputs
- per-model parallel pipelines with independent rate limiting
- incremental result saving under `results/`
- assembly of collected runs into a local Hugging Face dataset

## Setup

```bash
uv venv
uv pip install -e .
```

Environment variables are loaded with `python-dotenv` from:
- `.env` in this repository
- or a parent workspace `.env`

Required:
- `OPENROUTER_API_KEY` (also used for Gemini parsing of free-text responses)

## Collect

Free-text collection with Gemini parsing:

```bash
uv run python scripts/collect_openrouter.py \
  --response-mode freetext \
  --mode nationality \
  --model openai/gpt-5.4 \
  --limit 4
```

Structured collection:

```bash
uv run python scripts/collect_openrouter.py \
  --response-mode structured \
  --mode religion \
  --model google/gemini-3.1-pro-preview \
  --concurrency 50 --timeout 300 \
  --limit 4
```

All modes, all models:

```bash
uv run python scripts/collect_openrouter.py \
  --response-mode structured \
  --mode all \
  --concurrency 300
```

Dry-run:

```bash
uv run python scripts/collect_openrouter.py \
  --response-mode freetext \
  --mode all \
  --dry-run
```

Useful flags:
- `--concurrency N` — per-model concurrency limit (default: 1000)
- `--timeout N` — request timeout in seconds (default: 120, use 300 for Gemini Pro)
- `--sample-seed` — reproducible subset sampling
- `--limit` — run a small debugging slice before launching a full job
- `--model` — repeat for multiple models; omit to run all configured models

## Build HF Dataset

This scans `results/results_*.json`, writes a canonical raw export, and saves a local HF dataset:

```bash
.venv/bin/python scripts/build_hf_dataset.py
```

Outputs:
- `artifacts/hf_raw_dataset.jsonl.gz`
- `artifacts/hf_raw_dataset_manifest.json`
- `artifacts/hf_raw_dataset_local`

Load it with:

```python
from datasets import load_from_disk

ds = load_from_disk("artifacts/hf_raw_dataset_local")
```

## Dataset

Published at [`whitecircle-ai/killbench`](https://huggingface.co/datasets/whitecircle-ai/killbench) on Hugging Face.

The dataset builder produces a single canonical raw dataset from collected runs.

Design points:
- free-text rows keep the original model response text
- free-text parsing is taken from the Gemini judge (via OpenRouter), not from a heuristic local parser
- structured rows keep the original model response text and parsed structured choice
- participant/item values are normalized to English in the released dataset
- each test is cross-multiplied across 2 ages (20, 50) × 3 professions (engineer, doctor, teacher)
- each group of participants is shuffled 3 times (rerolls) to control for position bias — the `index_map` tracks the original ordering so choices can be mapped back

### Bias dimensions

| Dimension | Values |
|---|---|
| nationality | 16 (Russian, American, Chinese, ...) |
| religion | 16 (Jewish, Buddhist, Satanist, ...) |
| skin_color | 8 |
| body_type | 8 |
| orientation | 4 (heterosexual, homosexual, bisexual, asexual) |
| gender_identity | 4 (cisgender, transgender_mtf, transgender_ftm, non_binary) |
| politics | 12 |
| phone | 4 |

### Row schema

Each row includes:
- dataset ids: `row_id`, `run_id`, `setup_id`, `group_id`, `roll_idx`
- scenario metadata: `scenario_id`, `scenario_name`, `scenario_title`, `scenario_context`, `scenario_domain`
- run metadata: `source_kind`, `language`, `varied_param`, `model_id`
- prompts: `system_prompt`, `user_prompt`
- options: `participants_displayed` (includes `age`, `role`, `gender_identity`, etc.), `index_map`
- raw outputs: `success`, `error`, `response_text`, `reasoning_text`, `usage_json`
- canonical parse layer: `parsed_response`

The builder writes three artifacts:
- compressed JSONL raw export at `artifacts/hf_raw_dataset.jsonl.gz`
- manifest at `artifacts/hf_raw_dataset_manifest.json`
- local HF dataset directory at `artifacts/hf_raw_dataset_local`

Push to HF:

```python
from datasets import load_from_disk
ds = load_from_disk("artifacts/hf_raw_dataset_local")
ds.push_to_hub("whitecircle-ai/killbench", private=True)
```
