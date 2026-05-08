# SKB Coding Data Factory

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
