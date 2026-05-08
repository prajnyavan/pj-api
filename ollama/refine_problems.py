#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama.client import DEFAULT_OLLAMA_URL, generate
from ollama.json_utils import parse_json_object, read_jsonl, write_jsonl

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "problem_refiner.md"


def refine_row(args: argparse.Namespace, system: str, row: dict) -> dict:
    prompt = f"Refine this problem JSON:\n{json.dumps(row, indent=2, sort_keys=True)}"
    last_error: Exception | None = None
    for _ in range(args.retries):
        response = generate(
            model=args.model,
            system=system,
            prompt=prompt,
            base_url=args.ollama_url,
            temperature=args.temperature,
        )
        try:
            return parse_json_object(response)
        except ValueError as exc:
            last_error = exc
            prompt = (
                "Your previous response was not valid JSON. "
                "Return only one JSON object. No markdown, no prose.\n\n"
                + prompt
            )
    return {
        "problem_id": row.get("problem_id"),
        "status": "rejected",
        "rejection_reason": f"invalid_refiner_json:{last_error}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine raw pj-api problem ideas with local Ollama.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rejected-out", type=Path, default=Path("data/problem_bank/rejected/refiner_rejected.jsonl"))
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    system = PROMPT_PATH.read_text(encoding="utf-8")
    refined: list[dict] = []
    rejected: list[dict] = []
    rows = read_jsonl(args.input)
    for index, row in enumerate(rows, start=1):
        candidate = refine_row(args, system, row)
        if candidate.get("status") == "rejected":
            rejected.append(candidate)
        else:
            candidate["status"] = "refined"
            refined.append(candidate)
        if index % 25 == 0:
            write_jsonl(args.out, refined)
            write_jsonl(args.rejected_out, rejected)
            print(f"refined {len(refined)}, rejected {len(rejected)}", flush=True)

    write_jsonl(args.out, refined)
    write_jsonl(args.rejected_out, rejected)
    print(f"done: refined {len(refined)}, rejected {len(rejected)}", flush=True)


if __name__ == "__main__":
    main()
