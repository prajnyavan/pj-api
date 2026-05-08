from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from verifier.dependency_guard import validate_dependencies
from verifier.docker_runner import run_command
from verifier.patch_integrity import validate_patch_scope
from verifier.secret_scanner import scan_for_secrets


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_trace(trace: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{trace['trace_id']}.json"
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def reject(trace: dict[str, Any], reason: str, rejected_dir: Path, candidate_path: Path) -> dict[str, Any]:
    trace["dataset_ready"] = False
    trace["verified_at"] = utc_now()
    trace["verification"] = {
        "tests_passed": False,
        "build_passed": False,
        "lint_passed": False,
    }
    trace["rejection_reason"] = reason
    write_trace(trace, rejected_dir)
    candidate_path.unlink(missing_ok=True)
    return trace


def patch_text_from_trace(trace: dict[str, Any], candidate_path: Path) -> str:
    candidate = trace.get("candidate", {})
    patch_diff = candidate.get("patch_diff", "")
    if patch_diff:
        return patch_diff

    patch_path = candidate.get("patch_path")
    if not patch_path:
        return ""
    resolved = (candidate_path.parent / patch_path).resolve()
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8")


def git_commit_exists(repo_path: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def apply_patch(worktree: Path, patch_text: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=worktree,
        input=patch_text,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, "ok"


def verify_candidate_trace(candidate_path: Path, verified_dir: Path, rejected_dir: Path) -> dict[str, Any]:
    trace = json.loads(candidate_path.read_text(encoding="utf-8"))
    if trace.get("dataset_ready") is True:
        return reject(trace, "worker_set_dataset_ready", rejected_dir, candidate_path)

    task = trace["task"]
    repo_path = Path(task["repo_path"])
    if not repo_path.exists():
        return reject(trace, "repo_path_missing", rejected_dir, candidate_path)
    if not git_commit_exists(repo_path, task["base_commit"]):
        return reject(trace, "base_commit_missing", rejected_dir, candidate_path)
    for expected_file in task["expected_files"]:
        if not (repo_path / expected_file).exists():
            return reject(trace, "expected_file_missing", rejected_dir, candidate_path)

    patch_text = patch_text_from_trace(trace, candidate_path)
    if not patch_text:
        return reject(trace, "worker_stub_no_patch", rejected_dir, candidate_path)

    ok, reason = validate_patch_scope(patch_text, task["expected_files"])
    if not ok:
        return reject(trace, reason, rejected_dir, candidate_path)
    ok, reason = validate_dependencies(patch_text, task["constraints"].get("allow_new_dependencies", False))
    if not ok:
        return reject(trace, reason, rejected_dir, candidate_path)
    ok, reason = scan_for_secrets(patch_text)
    if not ok:
        return reject(trace, reason, rejected_dir, candidate_path)

    temp_dir = Path(tempfile.mkdtemp(prefix="skb-verify-"))
    worktree = temp_dir / "repo"
    try:
        add_result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), task["base_commit"]],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if add_result.returncode != 0:
            return reject(trace, "worktree_create_failed", rejected_dir, candidate_path)

        patch_ok, patch_reason = apply_patch(worktree, patch_text)
        if not patch_ok:
            return reject(trace, "patch_did_not_apply", rejected_dir, candidate_path)

        build = run_command(task["build_command"], worktree)
        lint = run_command(task["lint_command"], worktree)
        tests = run_command(task["test_command"], worktree)
        trace["verification"] = {
            "build": build,
            "lint": lint,
            "tests": tests,
            "build_passed": build["passed"],
            "lint_passed": lint["passed"],
            "tests_passed": tests["passed"],
        }

        if not build["passed"]:
            return reject(trace, "build_failed", rejected_dir, candidate_path)
        if not lint["passed"]:
            return reject(trace, "lint_failed", rejected_dir, candidate_path)
        if not tests["passed"]:
            return reject(trace, "tests_failed", rejected_dir, candidate_path)

        trace["dataset_ready"] = True
        trace["verified_at"] = utc_now()
        write_trace(trace, verified_dir)
        candidate_path.unlink(missing_ok=True)
        return trace
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo_path, capture_output=True, text=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
