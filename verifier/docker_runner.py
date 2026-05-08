from __future__ import annotations

import subprocess
from pathlib import Path


def run_command(command: str, cwd: Path, timeout: int = 120) -> dict[str, object]:
    result = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }
