from __future__ import annotations

import re

PATCH_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def changed_files(patch_text: str) -> set[str]:
    return {match.group(1) for match in PATCH_FILE_RE.finditer(patch_text) if match.group(1) != "/dev/null"}


def validate_patch_scope(patch_text: str, expected_files: list[str]) -> tuple[bool, str]:
    files = changed_files(patch_text)
    if not files:
        return False, "patch_has_no_changed_files"
    unexpected = sorted(files - set(expected_files))
    if unexpected:
        return False, f"patch_touches_unexpected_files:{','.join(unexpected)}"
    return True, "ok"
