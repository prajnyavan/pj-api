from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_traces(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


def build_dpo(
    verified_dir: Path = Path("traces/verified"),
    rejected_dir: Path = Path("traces/rejected"),
    output: Path = Path("datasets/dpo_train.jsonl"),
) -> int:
    verified = {trace["task"]["task_id"]: trace for trace in load_traces(verified_dir) if trace.get("dataset_ready") is True}
    rejected = {trace["task"]["task_id"]: trace for trace in load_traces(rejected_dir)}

    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as file:
        for task_id, chosen in sorted(verified.items()):
            rejected_trace = rejected.get(task_id)
            if rejected_trace is None:
                continue
            row = {
                "task_id": task_id,
                "prompt": chosen["task"]["description"],
                "chosen": chosen["candidate"].get("patch_diff", ""),
                "rejected": rejected_trace["candidate"].get("patch_diff", ""),
                "metadata": {
                    "chosen_trace_id": chosen["trace_id"],
                    "rejected_trace_id": rejected_trace["trace_id"],
                },
            }
            file.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count
