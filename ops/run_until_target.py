#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datasets.build_dpo import build_dpo
from datasets.build_sft import build_sft
from ops.scorecard import build_scorecard, print_scorecard, write_scorecard
from verifier.verify_patch import verify_candidate_trace


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_dirs(traces_dir: Path) -> None:
    for name in ("candidates", "verified", "rejected", "runs"):
        (traces_dir / name).mkdir(parents=True, exist_ok=True)


def load_tasks(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def create_worker_stub_trace(task: dict[str, Any], run_id: str, worker: str, traces_dir: Path) -> Path:
    trace_id = f"{run_id}-{task['task_id']}"
    trace = {
        "trace_id": trace_id,
        "run_id": run_id,
        "worker": worker,
        "task": task,
        "candidate": {
            "patch_diff": "",
            "commands_run": [],
            "test_logs": "",
            "notes": "Worker stub did not produce a patch.",
        },
        "dataset_ready": False,
        "created_at": utc_now(),
    }
    output = traces_dir / "candidates" / f"{trace_id}.json"
    output.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def stop_reason(scorecard: dict[str, Any], args: argparse.Namespace, started_at: float, processed: int) -> str | None:
    runtime_hours = (time.monotonic() - started_at) / 3600
    if scorecard["verified_traces"] >= args.target_verified:
        return "target reached"
    if processed >= args.max_candidates:
        return "max candidates reached"
    if runtime_hours >= args.max_hours:
        return "time limit reached"
    if scorecard["rejected_traces"] >= args.max_rejections:
        return "too many failed traces"
    return None


def run_until_target(args: argparse.Namespace) -> dict[str, Any]:
    ensure_dirs(args.traces_dir)
    run_id = args.run_id or f"run-{datetime.now(UTC).strftime('%Y-%m-%d-%H%M%S')}"
    tasks = load_tasks(args.tasks)
    started_at = time.monotonic()
    processed = 0

    run_config = {
        "run_id": run_id,
        "tasks": str(args.tasks),
        "target_verified": args.target_verified,
        "max_candidates": args.max_candidates,
        "max_hours": args.max_hours,
        "max_rejections": args.max_rejections,
        "worker": args.worker,
        "status": "running",
        "started_at": utc_now(),
    }
    (args.traces_dir / "runs" / f"{run_id}.json").write_text(
        json.dumps(run_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for task in tasks[: args.max_candidates]:
        scorecard = build_scorecard(args.traces_dir, run_id)
        reason = stop_reason(scorecard, args, started_at, processed)
        if reason:
            run_config["status"] = "stopped"
            run_config["stop_reason"] = reason
            break

        candidate_path = create_worker_stub_trace(task, run_id, args.worker, args.traces_dir)
        verify_candidate_trace(candidate_path, args.traces_dir / "verified", args.traces_dir / "rejected")
        processed += 1

        scorecard = build_scorecard(args.traces_dir, run_id)
        scorecard["target_verified"] = args.target_verified
        scorecard["candidate_tasks"] = processed
        print_scorecard(scorecard)
        write_scorecard(scorecard, args.scorecard)

    final_scorecard = build_scorecard(args.traces_dir, run_id)
    final_scorecard["target_verified"] = args.target_verified
    final_scorecard["candidate_tasks"] = processed
    final_reason = stop_reason(final_scorecard, args, started_at, processed) or "task queue exhausted"
    final_scorecard["status"] = "stopped"
    final_scorecard["stop_reason"] = final_reason
    run_config["status"] = "stopped"
    run_config["stop_reason"] = final_reason
    run_config["stopped_at"] = utc_now()
    (args.traces_dir / "runs" / f"{run_id}.json").write_text(
        json.dumps(run_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.build_datasets:
        build_sft(args.traces_dir / "verified", args.datasets_dir / "sft_train.jsonl")
        build_dpo(args.traces_dir / "verified", args.traces_dir / "rejected", args.datasets_dir / "dpo_train.jsonl")

    write_scorecard(final_scorecard, args.scorecard)
    return final_scorecard


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local factory loop until a target or guardrail stops it.")
    parser.add_argument("--tasks", type=Path, default=Path("tasks/pilot_20.jsonl"))
    parser.add_argument("--target-verified", type=int, required=True)
    parser.add_argument("--max-candidates", type=int, required=True)
    parser.add_argument("--max-hours", type=float, default=8)
    parser.add_argument("--max-rejections", type=int, default=1_000_000)
    parser.add_argument("--worker", default="stub")
    parser.add_argument("--run-id")
    parser.add_argument("--traces-dir", type=Path, default=Path("traces"))
    parser.add_argument("--datasets-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--scorecard", type=Path, default=Path("scorecard.json"))
    parser.add_argument("--build-datasets", action="store_true")
    args = parser.parse_args()

    final_scorecard = run_until_target(args)
    print_scorecard(final_scorecard)


if __name__ == "__main__":
    main()
