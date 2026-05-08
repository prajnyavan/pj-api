#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama.json_utils import read_jsonl, write_jsonl

ALLOWED_FILES = {
    "app/routes/auth.py",
    "app/routes/users.py",
    "app/schemas/user.py",
    "app/services/auth_service.py",
    "tests/test_auth.py",
    "tests/test_users.py",
}
DEFAULT_CONSTRAINTS = {
    "candidate_only": True,
    "no_patch_in_task": True,
    "no_fake_test_results": True,
    "independent_verifier_required": True,
    "allow_new_dependencies": False,
    "max_expected_files": 3,
    "keep_scope_small": True,
}


def git_sha(repo: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def build_description(problem: dict[str, Any]) -> str:
    return (
        f"{problem.get('title', '').strip()}. "
        f"Actual behavior: {problem.get('actual_behavior', '').strip()} "
        f"Expected behavior: {problem.get('expected_behavior', '').strip()} "
        f"Verification idea: {problem.get('verification_idea', '').strip()}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pj-api grounded tasks from refined problems.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("tasks/pj_api_pilot_20.jsonl"))
    parser.add_argument("--validated-out", type=Path, default=Path("tasks/validated_tasks.jsonl"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--repo-name", default="pj-api")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    repo = args.repo.resolve()
    base_commit = git_sha(repo)
    tasks: list[dict[str, Any]] = []
    for problem in read_jsonl(args.input):
        files = problem.get("likely_files", [])
        if not isinstance(files, list) or not 1 <= len(files) <= 3:
            continue
        if any(file not in ALLOWED_FILES or not (repo / file).exists() for file in files):
            continue
        task_id = f"pj-api-ollama-{len(tasks) + 1:06d}"
        task = {
            "task_id": task_id,
            "repo_name": args.repo_name,
            "repo_path": str(repo),
            "base_commit": base_commit,
            "task_type": problem.get("task_type", "bug_fix"),
            "language": "Python",
            "framework": "FastAPI",
            "difficulty": problem.get("difficulty", "easy"),
            "description": build_description(problem),
            "expected_files": files,
            "test_command": "pytest",
            "build_command": "python -m compileall app",
            "lint_command": "ruff check .",
            "constraints": DEFAULT_CONSTRAINTS,
            "source_problem_id": problem.get("problem_id"),
        }
        tasks.append(task)
        if len(tasks) >= args.limit:
            break

    write_jsonl(args.out, tasks)
    write_jsonl(args.validated_out, tasks)
    print(f"wrote {len(tasks)} tasks to {args.out}")


if __name__ == "__main__":
    main()
