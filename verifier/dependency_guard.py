from __future__ import annotations

from verifier.patch_integrity import changed_files

DEPENDENCY_FILES = {"requirements.txt", "pyproject.toml", "package.json", "package-lock.json", "Dockerfile"}


def validate_dependencies(patch_text: str, allow_new_dependencies: bool) -> tuple[bool, str]:
    if allow_new_dependencies:
        return True, "ok"
    touched = changed_files(patch_text)
    blocked = sorted(touched & DEPENDENCY_FILES)
    if blocked:
        return False, f"dependency_file_changed:{','.join(blocked)}"
    return True, "ok"
