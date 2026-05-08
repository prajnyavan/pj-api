# SKB Coding Data Factory

## PJ API Seed Repo

This repository is the first grounded seed project for the SKB Coding Data Factory. It contains a small FastAPI app with real source files, tests, lint configuration, and Docker build metadata.

Run the API checks from the repository root:

```bash
pytest
python -m compileall app
ruff check .
```

Run the development server:

```bash
uvicorn app.main:app --reload
```

## Generate Starter Task Queue

Run the deterministic generator from the repository root:

```bash
python3 generate_tasks_queue.py
```

The script writes exactly 1000 candidate JSONL tasks to:

```text
tasks/tasks_queue.jsonl
```

Each line is one valid JSON object for a later agent/verifier workflow. These are candidate tasks only: the queue does not include solved answers, patches, final training data, fake test results, or a `dataset_ready` flag.

The generated mix is:

- 250 React/TypeScript bug-fix tasks
- 200 Python/FastAPI bug-fix tasks
- 150 test-writing tasks
- 150 refactor tasks
- 100 Docker/CI tasks
- 100 typing/lint/build tasks
- 50 documentation-to-code tasks

Generation uses a fixed seed so repeated runs produce the same queue.

## Generate Grounded PJ API Pilot

Use grounded mode when the tasks should point at a real repository commit instead of synthetic SHA-shaped placeholders:

```bash
python3 generate_tasks_queue.py \
  --repo pj-api \
  --repo-path repos/pj-api \
  --base-commit "$(git rev-parse HEAD)" \
  --count 20 \
  --output tasks/pilot_20.jsonl
```

Grounded `pj-api` pilot tasks use:

```text
repo_name: pj-api
repo_path: repos/pj-api
language: Python
framework: FastAPI
test_command: pytest
build_command: python -m compileall app
lint_command: ruff check .
```

## Validate Against Local Repositories

After the referenced repositories are available under `repos/`, validate that each task points at a real repository, commit, and expected file:

```bash
python3 tasks/validate_tasks_queue.py
```

Validate the grounded pilot directly:

```bash
python3 tasks/validate_tasks_queue.py --queue tasks/pilot_20.jsonl
```

The validator checks JSONL parsing, duplicate ids, required fields, forbidden solved-data fields, `repo_path`, `base_commit`, and `expected_files`.

## Create A 20-Task Pilot

Before solving at scale, create a small pilot queue:

```bash
python3 generate_tasks_queue.py --repo pj-api --repo-path repos/pj-api --base-commit "$(git rev-parse HEAD)" --count 20 --output tasks/pilot_20.jsonl
```

Use the pilot for the first solve-and-verify loop. Keep `dataset_ready` unset until independent verification passes.

## Run Until Target

Run the local target controller against the grounded pilot:

```bash
python3 ops/run_until_target.py \
  --tasks tasks/pilot_20.jsonl \
  --target-verified 5 \
  --max-candidates 20 \
  --build-datasets
```

The current worker is a safe stub. It creates candidate traces but does not invent patches, so the verifier rejects those traces with `worker_stub_no_patch`. Real workers should write candidate traces with patches into `traces/candidates/`; the verifier is the only component allowed to set `dataset_ready=true`.

Stop conditions:

```text
verified_traces >= target_verified
candidate_tasks >= max_candidates
runtime >= max_hours
rejected_traces >= max_rejections
```

## Scorecard

Print and write the current scorecard:

```bash
python3 ops/scorecard.py --output scorecard.json
```

The scorecard reports candidate, verified, and rejected trace counts, pass rate, DPO pair count, and top rejection reasons.

## Build Datasets

Build dataset JSONL files from verified traces:

```bash
python3 - <<'PY'
from pathlib import Path
from datasets.build_sft import build_sft
from datasets.build_dpo import build_dpo

print("sft rows:", build_sft(Path("traces/verified"), Path("datasets/sft_train.jsonl")))
print("dpo rows:", build_dpo(Path("traces/verified"), Path("traces/rejected"), Path("datasets/dpo_train.jsonl")))
PY
```

Dataset builders only use verifier-approved traces where `dataset_ready` is true.

## Data Factory API

Run the API:

```bash
uvicorn api.main:app --reload
```

Exposed endpoints:

```text
POST /runs/start
GET  /runs/{run_id}
GET  /scorecard
GET  /traces/verified
GET  /traces/rejected
POST /datasets/build
```
