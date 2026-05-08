from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FENCED_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_text(text: str) -> str:
    match = FENCED_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = extract_json_text(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"expected a JSON object, got: {cleaned[:200]}") from exc
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def parse_json_array(text: str) -> list[dict[str, Any]]:
    cleaned = extract_json_text(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"expected a JSON array, got: {cleaned[:200]}") from exc
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("expected a JSON array of objects")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

