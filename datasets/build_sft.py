from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_traces(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


def build_sft(verified_dir: Path = Path("traces/verified"), output: Path = Path("datasets/sft_train.jsonl")) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as file:
        for trace in load_traces(verified_dir):
            if trace.get("dataset_ready") is not True:
                continue
            row = {
                "task_id": trace["task"]["task_id"],
                "prompt": trace["task"]["description"],
                "response": trace["candidate"].get("patch_diff", ""),
                "metadata": {
                    "repo_name": trace["task"]["repo_name"],
                    "base_commit": trace["task"]["base_commit"],
                    "trace_id": trace["trace_id"],
                },
            }
            file.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count
