#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

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
VAGUE_RE = re.compile(r"^\s*(fix|improve|update|refactor)\s+(auth|users?|bug|code)\.?\s*$", re.IGNORECASE)


def fingerprint(row: dict) -> str:
    title = str(row.get("title", "")).strip().lower()
    expected = str(row.get("expected_behavior", "")).strip().lower()
    return re.sub(r"\s+", " ", f"{title} {expected}")


def rejection_reason(row: dict, seen: set[str]) -> str | None:
    fp = fingerprint(row)
    if not fp.strip():
        return "empty_fingerprint"
    if fp in seen:
        return "duplicate"
    title = str(row.get("title", ""))
    actual = str(row.get("actual_behavior", ""))
    expected = str(row.get("expected_behavior", ""))
    verification = str(row.get("verification_idea", ""))
    if VAGUE_RE.match(title) or len(actual) < 20 or len(expected) < 20:
        return "vague"
    if not verification or len(verification) < 12:
        return "missing_verification_idea"
    files = row.get("likely_files", [])
    if not isinstance(files, list) or not 1 <= len(files) <= 3:
        return "bad_file_scope"
    if any(file not in ALLOWED_FILES for file in files):
        return "non_pj_api_file"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Dedupe and filter refined problem bank rows.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rejected-out", type=Path, default=Path("data/problem_bank/rejected/dedupe_rejected.jsonl"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    accepted: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()
    for row in read_jsonl(args.input):
        reason = rejection_reason(row, seen)
        if reason:
            row["status"] = "rejected"
            row["rejection_reason"] = reason
            rejected.append(row)
            continue
        seen.add(fingerprint(row))
        row["status"] = "refined"
        accepted.append(row)
        if args.limit and len(accepted) >= args.limit:
            break

    write_jsonl(args.out, accepted)
    write_jsonl(args.rejected_out, rejected)
    print(f"accepted {len(accepted)}, rejected {len(rejected)}")


if __name__ == "__main__":
    main()
