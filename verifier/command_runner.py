from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

EXECUTION_MODE = "host_mvp"
MAX_OUTPUT_CHARS = 20_000
ALLOWED_COMMANDS = {
    ("pytest",),
    ("python", "-m", "compileall", "app"),
    ("python3", "-m", "compileall", "app"),
    ("ruff", "check", "."),
}


def truncate_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n...[truncated]"


def normalize_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_command(command: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(command))
    except ValueError:
        return ()


def command_allowed(command: str, approved_commands: set[str] | None = None) -> tuple[bool, tuple[str, ...]]:
    argv = parse_command(command)
    if not argv:
        return False, argv

    allowed = set(ALLOWED_COMMANDS)
    if approved_commands:
        allowed &= {parse_command(item) for item in approved_commands}
    return argv in allowed, argv


def rejected_command_result(command: str, reason: str) -> dict[str, Any]:
    return {
        "command": command,
        "execution_mode": EXECUTION_MODE,
        "returncode": None,
        "stdout": "",
        "stderr": reason,
        "passed": False,
        "timed_out": False,
    }


def run_command(
    command: str,
    cwd: Path,
    *,
    approved_commands: set[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    allowed, argv = command_allowed(command, approved_commands)
    if not allowed:
        return rejected_command_result(command, "command_not_allowlisted")

    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "execution_mode": EXECUTION_MODE,
            "returncode": None,
            "stdout": truncate_output(normalize_output(exc.stdout)),
            "stderr": truncate_output(normalize_output(exc.stderr) or "command timed out"),
            "passed": False,
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "command": command,
            "execution_mode": EXECUTION_MODE,
            "returncode": None,
            "stdout": "",
            "stderr": truncate_output(str(exc)),
            "passed": False,
            "timed_out": False,
        }

    return {
        "command": command,
        "execution_mode": EXECUTION_MODE,
        "returncode": result.returncode,
        "stdout": truncate_output(result.stdout),
        "stderr": truncate_output(result.stderr),
        "passed": result.returncode == 0,
        "timed_out": False,
    }
