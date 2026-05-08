#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama.json_utils import read_jsonl
from ops.scorecard import build_scorecard, print_scorecard, write_scorecard
from verifier.verify_patch import verify_candidate_trace


def run_step(args: list[str]) -> None:
    print("$", " ".join(args))
    subprocess.run(args, check=True)


def count_rows(path: Path) -> int:
    return len(read_jsonl(path)) if path.exists() else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Ollama-first local coding data factory loop.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--target-problems", type=int, default=1000)
    parser.add_argument("--target-refined", type=int, default=300)
    parser.add_argument("--target-tasks", type=int, default=20)
    parser.add_argument("--target-verified", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=10)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--traces-dir", type=Path, default=Path("traces"))
    parser.add_argument("--scorecard", type=Path, default=Path("scorecard.json"))
    args = parser.parse_args()

    run_id = f"ollama-{datetime.now(UTC).strftime('%Y-%m-%d-%H%M%S')}"
    raw = Path("data/problem_bank/raw/problems_001.jsonl")
    refined = Path("data/problem_bank/refined/problems_001.refined.jsonl")
    clean = Path("data/problem_bank/refined/problems_001.clean.jsonl")
    tasks = Path("tasks/pj_api_pilot_20.jsonl")

    if count_rows(raw) < args.target_problems:
        run_step([
            sys.executable,
            "ollama/generate_problems.py",
            "--model",
            args.model,
            "--count",
            str(args.target_problems),
            "--out",
            str(raw),
            "--ollama-url",
            args.ollama_url,
        ])
    if count_rows(refined) < args.target_refined:
        run_step([
            sys.executable,
            "ollama/refine_problems.py",
            "--model",
            args.model,
            "--input",
            str(raw),
            "--out",
            str(refined),
            "--ollama-url",
            args.ollama_url,
        ])
    if count_rows(clean) < args.target_refined:
        run_step([
            sys.executable,
            "ops/dedupe_problem_bank.py",
            "--input",
            str(refined),
            "--out",
            str(clean),
            "--limit",
            str(args.target_refined),
        ])
    if count_rows(tasks) < args.target_tasks:
        run_step([
            sys.executable,
            "tasks/build_tasks_from_problems.py",
            "--input",
            str(clean),
            "--out",
            str(tasks),
            "--repo",
            str(args.repo),
            "--limit",
            str(args.target_tasks),
        ])

    task_rows = read_jsonl(tasks)[: args.max_attempts]
    for task in task_rows:
        scorecard = build_scorecard(args.traces_dir, run_id)
        if scorecard["verified_traces"] >= args.target_verified:
            break
        run_step([
            sys.executable,
            "ollama/solve_task.py",
            "--model",
            args.model,
            "--task",
            str(tasks),
            "--task-id",
            task["task_id"],
            "--run-id",
            run_id,
            "--ollama-url",
            args.ollama_url,
        ])
        latest = args.traces_dir / "candidates" / task["task_id"] / "candidate_trace.json"
        verify_candidate_trace(latest, args.traces_dir / "verified", args.traces_dir / "rejected")
        scorecard = build_scorecard(args.traces_dir, run_id)
        scorecard["target_verified"] = args.target_verified
        print_scorecard(scorecard)
        write_scorecard(scorecard, args.scorecard)

    final = build_scorecard(args.traces_dir, run_id)
    final["target_verified"] = args.target_verified
    final["status"] = "stopped"
    final["stop_reason"] = "target reached" if final["verified_traces"] >= args.target_verified else "attempt limit reached"
    write_scorecard(final, args.scorecard)
    print_scorecard(final)


if __name__ == "__main__":
    main()
