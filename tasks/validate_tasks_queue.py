#!/usr/bin/env python3
"""Validate candidate task queue records against local repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

QUEUE = Path("tasks/tasks_queue.jsonl")
REQUIRED_FIELDS = {
    "task_id",
    "repo_name",
    "repo_path",
    "base_commit",
    "task_type",
    "language",
    "framework",
    "difficulty",
    "description",
    "expected_files",
    "test_command",
    "build_command",
    "lint_command",
    "constraints",
}
FORBIDDEN_FIELDS = {"patch", "solution", "dataset_ready", "test_results"}


def commit_exists(repo_path: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a candidate task queue against local repos.")
    parser.add_argument("--queue", type=Path, default=QUEUE, help="JSONL queue to validate.")
    args = parser.parse_args()

    errors: list[str] = []
    seen: set[str] = set()

    if not args.queue.exists():
        print(f"valid: no\n - queue file does not exist: {args.queue}")
        return 1

    for line_no, line in enumerate(args.queue.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            task = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc}")
            continue

        missing = REQUIRED_FIELDS - task.keys()
        forbidden = FORBIDDEN_FIELDS & task.keys()
        task_id = task.get("task_id", f"line-{line_no}")

        if missing:
            errors.append(f"line {line_no}: missing fields for {task_id}: {sorted(missing)}")
        if forbidden:
            errors.append(f"line {line_no}: forbidden fields for {task_id}: {sorted(forbidden)}")
        if task_id in seen:
            errors.append(f"line {line_no}: duplicate task_id {task_id}")
        seen.add(task_id)

        repo_path = Path(task.get("repo_path", ""))
        if not repo_path.exists():
            errors.append(f"{task_id}: repo_path does not exist: {repo_path}")
            continue
        if not (repo_path / ".git").exists():
            errors.append(f"{task_id}: repo_path is not a git repository: {repo_path}")
            continue

        commit = task.get("base_commit", "")
        if not commit_exists(repo_path, commit):
            errors.append(f"{task_id}: base_commit not found in {repo_path}: {commit}")

        expected_files = task.get("expected_files", [])
        if not isinstance(expected_files, list) or not expected_files:
            errors.append(f"{task_id}: expected_files must be a non-empty list")
            continue
        for expected_file in expected_files:
            if not (repo_path / expected_file).exists():
                errors.append(f"{task_id}: expected_file missing: {expected_file}")

    print(f"tasks checked: {len(seen)}")
    if errors:
        print("valid: no")
        for error in errors[:100]:
            print(" -", error)
        if len(errors) > 100:
            print(f" - ... {len(errors) - 100} more errors")
        return 1

    print("valid: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
