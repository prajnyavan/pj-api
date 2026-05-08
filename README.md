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

## Validate Against Local Repositories

After the referenced repositories are available under `repos/`, validate that each task points at a real repository, commit, and expected file:

```bash
python3 tasks/validate_tasks_queue.py
```

The validator checks JSONL parsing, duplicate ids, required fields, forbidden solved-data fields, `repo_path`, `base_commit`, and `expected_files`.

## Create A 20-Task Pilot

Before solving at scale, create a small pilot queue:

```bash
head -n 20 tasks/tasks_queue.jsonl > tasks/pilot_20.jsonl
```

Use the pilot for the first solve-and-verify loop. Keep `dataset_ready` unset until independent verification passes.
