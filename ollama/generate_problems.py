#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama.client import DEFAULT_OLLAMA_URL, generate
from ollama.json_utils import parse_json_array, write_jsonl

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "problem_generator.md"


def normalize_row(row: dict, index: int) -> dict:
    row["problem_id"] = row.get("problem_id") or f"raw-fastapi-{index:06d}"
    row["domain"] = row.get("domain") or "api"
    row["language"] = "Python"
    row["framework"] = "FastAPI"
    row["status"] = "raw"
    if not isinstance(row.get("likely_files"), list):
        row["likely_files"] = []
    return row


def generate_batch(args: argparse.Namespace, system: str, start: int, batch_size: int) -> list[dict]:
    prompt = (
        f"Generate {batch_size} diverse raw problem ideas. "
        f"Use problem ids raw-fastapi-{start:06d} through raw-fastapi-{start + batch_size - 1:06d}."
    )
    last_error: Exception | None = None
    for _attempt in range(1, args.retries + 1):
        response = generate(
            model=args.model,
            system=system,
            prompt=prompt,
            base_url=args.ollama_url,
            temperature=args.temperature,
        )
        try:
            batch = parse_json_array(response)
        except ValueError as exc:
            last_error = exc
            prompt = (
                "Your previous response was not valid JSON. "
                "Return only a JSON array of problem objects. No markdown, no prose.\n\n"
                + prompt
            )
            continue
        if batch:
            return batch
        last_error = RuntimeError("Ollama returned an empty problem batch")
    raise RuntimeError(f"failed to generate valid problem batch after {args.retries} attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate raw pj-api problem ideas with local Ollama.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    system = PROMPT_PATH.read_text(encoding="utf-8")
    rows: list[dict] = []
    while len(rows) < args.count:
        start = len(rows) + 1
        batch_size = min(args.batch_size, args.count - len(rows))
        batch = generate_batch(args, system, start, batch_size)
        for row in batch:
            rows.append(normalize_row(row, len(rows) + 1))
            if len(rows) >= args.count:
                break
        write_jsonl(args.out, rows)
        print(f"generated {len(rows)}/{args.count}", flush=True)


if __name__ == "__main__":
    main()
