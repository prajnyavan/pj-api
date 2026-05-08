#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama.client import DEFAULT_OLLAMA_URL, generate
from ollama.json_utils import read_jsonl

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "patch_solver.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def load_task(path: Path, task_id: str | None) -> dict[str, Any]:
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
        if task_id:
            for row in rows:
                if row.get("task_id") == task_id:
                    return row
            raise ValueError(f"task_id not found: {task_id}")
        if not rows:
            raise ValueError(f"no tasks in {path}")
        return rows[0]
    return json.loads(path.read_text(encoding="utf-8"))


def strip_to_diff(text: str) -> str:
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            cleaned = part.removeprefix("diff").strip()
            if cleaned.startswith("diff --git"):
                return cleaned + "\n"
    index = text.find("diff --git")
    if index >= 0:
        return text[index:].strip() + "\n"
    return text + ("\n" if text else "")


def build_prompt(task: dict[str, Any]) -> str:
    repo = Path(task["repo_path"])
    file_blocks = []
    for file in task["expected_files"]:
        path = repo / file
        file_blocks.append(f"--- {file} ---\n{path.read_text(encoding='utf-8')}")
    return (
        "Task JSON:\n"
        f"{json.dumps(task, indent=2, sort_keys=True)}\n\n"
        "Relevant files:\n"
        + "\n\n".join(file_blocks)
        + "\n\nReturn only a unified diff patch."
    )


def write_trace(task: dict[str, Any], patch: str, model: str, run_id: str, out_dir: Path) -> Path:
    task_dir = out_dir / task["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    patch_path = task_dir / "patch.diff"
    patch_path.write_text(patch, encoding="utf-8")
    trace_id = f"{task['task_id']}-attempt-001"
    trace = {
        "trace_id": trace_id,
        "run_id": run_id,
        "worker": "ollama",
        "agent": "ollama",
        "model": model,
        "task_id": task["task_id"],
        "task": task,
        "patch": patch,
        "candidate": {
            "patch_diff": patch,
            "patch_path": "patch.diff",
            "commands_run": [],
            "test_logs": "",
            "notes": "Ollama generated patch only; verifier determines truth.",
        },
        "dataset_ready": False,
        "created_at": utc_now(),
    }
    output = task_dir / "candidate_trace.json"
    output.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask local Ollama to attempt one task as a patch.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--out-dir", type=Path, default=Path("traces/candidates"))
    parser.add_argument("--run-id", default="ollama-manual")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--temperature", type=float, default=0.1)
    args = parser.parse_args()

    task = load_task(args.task, args.task_id)
    response = generate(
        model=args.model,
        system=PROMPT_PATH.read_text(encoding="utf-8"),
        prompt=build_prompt(task),
        base_url=args.ollama_url,
        temperature=args.temperature,
    )
    patch = strip_to_diff(response)
    output = write_trace(task, patch, args.model, args.run_id, args.out_dir)
    print(output)


if __name__ == "__main__":
    main()
