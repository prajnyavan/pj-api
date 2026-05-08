from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*=\s*['\"][^'\"]{16,}['\"]"),
]


def scan_for_secrets(text: str) -> tuple[bool, str]:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return False, "secret_pattern_detected"
    return True, "ok"
