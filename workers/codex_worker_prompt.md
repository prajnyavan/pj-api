# Codex Worker Prompt

Solve exactly one task from the queue.

Output:

- `patch.diff`
- `candidate_trace.json`
- `commands_run.txt`
- `test_logs.txt`

Rules:

- Do not set `dataset_ready=true`.
- Do not fake command success.
- Keep changes inside `expected_files` unless the task explicitly allows otherwise.
- The verifier is the only authority that can mark a trace dataset-ready.
