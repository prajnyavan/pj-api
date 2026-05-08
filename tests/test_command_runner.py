from __future__ import annotations

from verifier.command_runner import EXECUTION_MODE, command_allowed, normalize_output, run_command, truncate_output


def test_command_must_be_globally_allowlisted_and_task_approved(tmp_path):
    allowed, _ = command_allowed("pytest", {"pytest"})
    assert allowed is True

    allowed, _ = command_allowed("pytest", {"ruff check ."})
    assert allowed is False

    result = run_command("pytest", tmp_path, approved_commands={"ruff check ."})
    assert result["passed"] is False
    assert result["stderr"] == "command_not_allowlisted"
    assert result["execution_mode"] == EXECUTION_MODE


def test_shell_syntax_is_not_allowlisted(tmp_path):
    result = run_command("pytest; echo unsafe", tmp_path, approved_commands={"pytest; echo unsafe"})
    assert result["passed"] is False
    assert result["stderr"] == "command_not_allowlisted"


def test_truncate_output_caps_long_text():
    text = "x" * 25_000
    truncated = truncate_output(text)
    assert len(truncated) < len(text)
    assert truncated.endswith("...[truncated]")


def test_normalize_output_handles_timeout_bytes():
    assert normalize_output(b"hello") == "hello"
    assert normalize_output(None) == ""
