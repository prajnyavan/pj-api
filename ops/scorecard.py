#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_TRACES_DIR = Path("traces")
DEFAULT_OUTPUT = Path("scorecard.json")


def load_json_files(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for item in sorted(path.rglob("*.json")):
        rows.append(json.loads(item.read_text(encoding="utf-8")))
    return rows


def build_scorecard(traces_dir: Path = DEFAULT_TRACES_DIR, run_id: str | None = None) -> dict[str, Any]:
    candidates = load_json_files(traces_dir / "candidates")
    verified = load_json_files(traces_dir / "verified")
    rejected = load_json_files(traces_dir / "rejected")

    if run_id:
        candidates = [trace for trace in candidates if trace.get("run_id") == run_id]
        verified = [trace for trace in verified if trace.get("run_id") == run_id]
        rejected = [trace for trace in rejected if trace.get("run_id") == run_id]

    attempted = len(verified) + len(rejected)
    pass_rate = round((len(verified) / attempted) * 100, 2) if attempted else 0.0
    reasons = Counter(trace.get("rejection_reason", "unknown") for trace in rejected)

    return {
        "run_id": run_id,
        "candidate_traces": len(candidates),
        "attempted_tasks": attempted,
        "verified_traces": len(verified),
        "rejected_traces": len(rejected),
        "dpo_pairs": min(len(verified), len(rejected)),
        "pass_rate": pass_rate,
        "top_rejection_reasons": [reason for reason, _ in reasons.most_common(5)],
        "status": "running",
    }


def write_scorecard(scorecard: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> None:
    output.write_text(json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_scorecard(scorecard: dict[str, Any]) -> None:
    print(json.dumps(scorecard, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Write and print the current factory scorecard.")
    parser.add_argument("--traces-dir", type=Path, default=DEFAULT_TRACES_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scorecard = build_scorecard(args.traces_dir, args.run_id)
    write_scorecard(scorecard, args.output)
    print_scorecard(scorecard)


if __name__ == "__main__":
    main()
