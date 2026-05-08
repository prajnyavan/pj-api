#!/usr/bin/env python3
"""Generate a deterministic starter queue of candidate coding tasks."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any


SEED = 20260508
OUTPUT_PATH = Path("tasks/tasks_queue.jsonl")

CATEGORY_COUNTS = {
    "react_typescript_bug_fix": 250,
    "python_fastapi_bug_fix": 200,
    "test_writing": 150,
    "refactor": 150,
    "docker_ci": 100,
    "typing_lint_build": 100,
    "documentation_to_code": 50,
}

REQUIRED_FIELDS = [
    "task_id",
    "repo_name",
    "repo_path",
    "base_commit",
    "task_type",
    "language",
    "framework",
    "difficulty",
    "description",
    "expected_files",
    "test_command",
    "build_command",
    "lint_command",
    "constraints",
]

REPOS = {
    "react": [
        "atlas-dashboard",
        "billing-portal",
        "content-studio",
        "field-ops-console",
        "inventory-web",
        "learnhub-ui",
        "metrics-workbench",
        "support-inbox",
    ],
    "fastapi": [
        "accounts-api",
        "audit-log-service",
        "catalog-api",
        "events-gateway",
        "notifications-api",
        "orders-service",
        "reporting-api",
        "search-service",
    ],
    "mixed": [
        "acme-monorepo",
        "data-quality-tools",
        "developer-platform",
        "edge-runtime-lab",
        "internal-automation",
        "release-workflows",
    ],
}

DIFFICULTIES = ["easy", "medium", "medium", "medium", "hard"]

REACT_AREAS = [
    ("filter state", ["src/components/FilterPanel.tsx", "src/hooks/useFilters.ts"]),
    ("pagination controls", ["src/components/Pagination.tsx", "src/pages/ListView.tsx"]),
    ("form validation", ["src/components/EditForm.tsx", "src/lib/validation.ts"]),
    ("empty-state rendering", ["src/components/EmptyState.tsx"]),
    ("date range picker", ["src/components/DateRangePicker.tsx", "src/utils/date.ts"]),
    ("optimistic update rollback", ["src/hooks/useOptimisticMutation.ts"]),
    ("route parameter handling", ["src/routes/details.tsx", "src/lib/routes.ts"]),
    ("table sort toggling", ["src/components/DataTable.tsx"]),
    ("toast error display", ["src/components/ToastHost.tsx", "src/lib/errors.ts"]),
    ("saved view selector", ["src/components/SavedViews.tsx"]),
]

REACT_FAILURES = {
    "filter state": (
        "Clearing one filter currently clears every active filter.",
        "Clearing one filter should preserve unrelated filters.",
        "FilterPanel preserves unrelated filters when one filter is cleared",
    ),
    "pagination controls": (
        "Clicking Next on the last page still increments the page index.",
        "Next should be disabled at the last page and keep the current page unchanged.",
        "Pagination does not advance past the final page",
    ),
    "form validation": (
        "Submitting a form with whitespace-only required fields is accepted.",
        "Whitespace-only values should be treated as empty and show the existing validation message.",
        "EditForm rejects whitespace-only required fields",
    ),
    "empty-state rendering": (
        "The empty state flashes while data is still loading.",
        "The empty state should render only after loading completes with zero rows.",
        "EmptyState is hidden while the list is loading",
    ),
    "date range picker": (
        "Selecting an end date before the start date leaves the range in an invalid state.",
        "The picker should reject the invalid end date and keep the previous valid range.",
        "DateRangePicker keeps the previous range when end date is invalid",
    ),
    "optimistic update rollback": (
        "A failed optimistic mutation leaves the stale optimistic item in the list.",
        "A failed mutation should roll the UI back to the server-confirmed state.",
        "useOptimisticMutation rolls back failed updates",
    ),
    "route parameter handling": (
        "Opening a details route with a URL-encoded id requests the encoded value literally.",
        "The route should decode the id before passing it to the API client.",
        "details route decodes encoded ids before loading",
    ),
    "table sort toggling": (
        "Clicking the active sort column never cycles back to an unsorted state.",
        "The third click should clear sorting and restore the default row order.",
        "DataTable cycles sort direction back to unsorted",
    ),
    "toast error display": (
        "API errors with a nested message render as a generic unknown error.",
        "The toast should show the nested server message when it is available.",
        "ToastHost displays nested API error messages",
    ),
    "saved view selector": (
        "Deleting the active saved view leaves the removed view selected.",
        "After deletion, the selector should fall back to the default view.",
        "SavedViews selects default after deleting the active view",
    ),
}

FASTAPI_AREAS = [
    ("request validation", ["app/routers/items.py", "app/schemas.py"]),
    ("pagination metadata", ["app/routers/listing.py", "app/services/pagination.py"]),
    ("authorization guard", ["app/dependencies/auth.py", "app/routers/admin.py"]),
    ("background job scheduling", ["app/jobs/scheduler.py", "app/routers/jobs.py"]),
    ("database transaction handling", ["app/repositories/orders.py"]),
    ("HTTP error mapping", ["app/services/errors.py", "app/routers/api.py"]),
    ("cache invalidation", ["app/services/cache.py"]),
    ("webhook signature parsing", ["app/routers/webhooks.py", "app/security.py"]),
    ("timezone normalization", ["app/services/dates.py", "app/schemas.py"]),
    ("search query parsing", ["app/services/search.py"]),
]

FASTAPI_FAILURES = {
    "request validation": (
        "Requests with an empty `name` field are accepted and later fail in the service layer.",
        "The endpoint should return a 422 validation response before calling the service.",
        "test_create_item_rejects_empty_name",
    ),
    "pagination metadata": (
        "The `has_next` metadata is false when the current page is exactly full.",
        "`has_next` should be true when more rows exist after the current page.",
        "test_list_response_sets_has_next_for_full_page",
    ),
    "authorization guard": (
        "Users without the admin role can reach one admin-only route.",
        "The dependency should reject non-admin users with 403.",
        "test_admin_route_rejects_non_admin_user",
    ),
    "background job scheduling": (
        "Retry jobs are scheduled immediately even when a future `run_at` is provided.",
        "The scheduler should honor the requested `run_at` timestamp.",
        "test_retry_job_uses_requested_run_at",
    ),
    "database transaction handling": (
        "A repository method commits after the first write and leaves partial data after the second write fails.",
        "The method should commit only after all writes succeed and roll back on failure.",
        "test_create_order_rolls_back_partial_write",
    ),
    "HTTP error mapping": (
        "Known service exceptions are returned as 500 responses.",
        "Known service exceptions should map to their documented HTTP status codes.",
        "test_known_service_error_maps_to_status_code",
    ),
    "cache invalidation": (
        "Updating a record leaves the stale cached detail response in place.",
        "The update path should invalidate the cached detail key for that record.",
        "test_update_invalidates_detail_cache",
    ),
    "webhook signature parsing": (
        "Webhook signatures with extra spaces are rejected before normalization.",
        "The parser should trim signature segments before verification.",
        "test_webhook_signature_parser_trims_segments",
    ),
    "timezone normalization": (
        "Naive datetimes are stored as local time instead of normalized UTC.",
        "Naive datetimes should be interpreted with the configured default timezone and stored as UTC.",
        "test_normalize_naive_datetime_to_utc",
    ),
    "search query parsing": (
        "Quoted search phrases are split into separate tokens.",
        "Quoted phrases should stay grouped as one search term.",
        "test_search_parser_preserves_quoted_phrases",
    ),
}

TEST_AREAS = [
    ("cover a React form regression", "TypeScript", "React", ["src/components/EditForm.test.tsx"], "EditForm rejects whitespace-only required fields"),
    ("add tests for a custom hook edge case", "TypeScript", "React", ["src/hooks/useFilters.test.ts"], "useFilters preserves unrelated filter state"),
    ("cover FastAPI validation errors", "Python", "FastAPI", ["tests/test_validation.py"], "test_create_item_rejects_empty_name"),
    ("add repository transaction tests", "Python", "pytest", ["tests/test_repositories.py"], "test_create_order_rolls_back_partial_write"),
    ("cover CLI argument parsing", "Python", "pytest", ["tests/test_cli.py"], "test_cli_rejects_invalid_output_format"),
    ("add component accessibility assertions", "TypeScript", "React", ["src/components/DataTable.test.tsx"], "DataTable exposes sort state to assistive technology"),
]

REFACTOR_AREAS = [
    ("extract repeated date formatting into an existing utility", "TypeScript", "React", ["src/utils/date.ts", "src/components/ActivityList.tsx"]),
    ("split a large FastAPI router helper without changing routes", "Python", "FastAPI", ["app/routers/reports.py", "app/services/reports.py"]),
    ("remove duplicated permission checks behind one helper", "Python", "FastAPI", ["app/dependencies/auth.py", "app/routers/admin.py"]),
    ("simplify repeated table column mapping", "TypeScript", "React", ["src/components/DataTable.tsx", "src/lib/tableColumns.ts"]),
    ("isolate API client response normalization", "TypeScript", "React", ["src/lib/apiClient.ts", "src/lib/normalizers.ts"]),
    ("move configuration parsing into a small helper", "Python", "pytest", ["app/config.py", "app/config_loader.py"]),
]

DOCKER_CI_AREAS = [
    ("fix Docker build context so production assets are included", "Dockerfile", "Docker", ["Dockerfile", ".dockerignore"]),
    ("make the GitHub Actions test job install cached dependencies correctly", "YAML", "GitHub Actions", [".github/workflows/test.yml"]),
    ("ensure the CI lint job runs from the package workspace", "YAML", "GitHub Actions", [".github/workflows/lint.yml"]),
    ("repair docker-compose healthcheck wiring for the API service", "YAML", "Docker Compose", ["docker-compose.yml"]),
    ("pin the Node version used by the frontend build workflow", "YAML", "GitHub Actions", [".github/workflows/frontend.yml"]),
]

TYPING_LINT_AREAS = [
    ("resolve a strict TypeScript nullability error", "TypeScript", "React", ["src/components/UserMenu.tsx"]),
    ("fix an ESLint exhaustive-deps warning without changing behavior", "TypeScript", "React", ["src/hooks/usePolling.ts"]),
    ("add missing Python type annotations for a service helper", "Python", "FastAPI", ["app/services/notifications.py"]),
    ("repair mypy Optional handling in a repository method", "Python", "FastAPI", ["app/repositories/users.py"]),
    ("fix an import-order lint failure", "Python", "ruff", ["app/routers/reports.py"]),
]

DOC_TO_CODE_AREAS = [
    ("implement the documented `include_archived` query parameter", "Python", "FastAPI", ["docs/api.md", "app/routers/items.py"]),
    ("align the settings panel labels with the product copy", "TypeScript", "React", ["docs/settings.md", "src/components/SettingsPanel.tsx"]),
    ("add the documented retry option to the client configuration", "TypeScript", "React", ["docs/client-config.md", "src/lib/apiClient.ts"]),
    ("make the health endpoint return the documented version field", "Python", "FastAPI", ["docs/operations.md", "app/routers/health.py"]),
    ("wire the documented CSV delimiter option into export handling", "Python", "FastAPI", ["docs/exports.md", "app/services/exporter.py"]),
]


def bug_description(domain: str, area: str) -> str:
    failures = REACT_FAILURES if domain == "react" else FASTAPI_FAILURES
    actual, expected, test_name = failures[area]
    return (
        f"Fix {area}. Actual behavior: {actual} Expected behavior: {expected} "
        f"Existing failing test: `{test_name}`. Keep the patch focused on the listed files and leave verification "
        "to the configured commands."
    )


def stable_commit(repo_name: str) -> str:
    return hashlib.sha1(f"{SEED}:{repo_name}".encode("utf-8")).hexdigest()


def command_set(language: str, framework: str) -> tuple[str, str, str]:
    if language == "TypeScript" or framework == "React":
        return ("npm test -- --runInBand", "npm run build", "npm run lint")
    if framework == "Docker":
        return ("docker build .", "docker build .", "hadolint Dockerfile || true")
    if framework == "Docker Compose":
        return ("docker compose config", "docker compose build", "yamllint docker-compose.yml || true")
    if framework == "GitHub Actions":
        return ("yamllint .github/workflows || true", "docker build .", "yamllint .github/workflows || true")
    return ("pytest", "python -m compileall app tests", "ruff check . && mypy app")


def constraints_for(task_type: str, expected_files: list[str], rng: random.Random) -> dict[str, Any]:
    allow_new_dependencies = task_type in {"docker_ci", "documentation_to_code"} and rng.random() < 0.12
    return {
        "candidate_only": True,
        "no_patch_in_task": True,
        "no_fake_test_results": True,
        "independent_verifier_required": True,
        "allow_new_dependencies": allow_new_dependencies,
        "max_expected_files": max(3, len(expected_files)),
        "keep_scope_small": True,
    }


def make_task(
    index: int,
    task_type: str,
    repo_name: str,
    language: str,
    framework: str,
    difficulty: str,
    description: str,
    expected_files: list[str],
    rng: random.Random,
) -> dict[str, Any]:
    test_command, build_command, lint_command = command_set(language, framework)
    return {
        "task_id": f"skb-task-{index:04d}",
        "repo_name": repo_name,
        "repo_path": f"repos/{repo_name}",
        "base_commit": stable_commit(repo_name),
        "task_type": task_type,
        "language": language,
        "framework": framework,
        "difficulty": difficulty,
        "description": description,
        "expected_files": expected_files,
        "test_command": test_command,
        "build_command": build_command,
        "lint_command": lint_command,
        "constraints": constraints_for(task_type, expected_files, rng),
    }


def generate_tasks() -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    tasks: list[dict[str, Any]] = []

    for _ in range(CATEGORY_COUNTS["react_typescript_bug_fix"]):
        area, files = rng.choice(REACT_AREAS)
        repo = rng.choice(REPOS["react"])
        description = bug_description("react", area)
        tasks.append(make_task(len(tasks) + 1, "bug_fix", repo, "TypeScript", "React", rng.choice(DIFFICULTIES), description, files, rng))

    for _ in range(CATEGORY_COUNTS["python_fastapi_bug_fix"]):
        area, files = rng.choice(FASTAPI_AREAS)
        repo = rng.choice(REPOS["fastapi"])
        description = bug_description("fastapi", area)
        tasks.append(make_task(len(tasks) + 1, "bug_fix", repo, "Python", "FastAPI", rng.choice(DIFFICULTIES), description, files, rng))

    for _ in range(CATEGORY_COUNTS["test_writing"]):
        area, language, framework, files, test_name = rng.choice(TEST_AREAS)
        repo = rng.choice(REPOS["react"] if language == "TypeScript" else REPOS["fastapi"])
        description = (
            f"Write focused tests to {area}. Target test name: `{test_name}`. Capture the expected behavior before "
            "any production fix, avoid broad fixture rewrites, and do not include solved implementation changes."
        )
        tasks.append(make_task(len(tasks) + 1, "test_writing", repo, language, framework, rng.choice(["easy", "medium", "medium"]), description, files, rng))

    for _ in range(CATEGORY_COUNTS["refactor"]):
        area, language, framework, files = rng.choice(REFACTOR_AREAS)
        repo_pool = REPOS["react"] if language == "TypeScript" else REPOS["fastapi"]
        repo = rng.choice(repo_pool)
        description = (
            f"Refactor to {area}. Keep behavior unchanged, keep the patch small, and rely on existing tests plus "
            "the listed verification commands."
        )
        tasks.append(make_task(len(tasks) + 1, "refactor", repo, language, framework, rng.choice(["medium", "medium", "hard"]), description, files, rng))

    for _ in range(CATEGORY_COUNTS["docker_ci"]):
        area, language, framework, files = rng.choice(DOCKER_CI_AREAS)
        repo = rng.choice(REPOS["mixed"])
        description = (
            f"Update Docker/CI configuration to {area}. Keep workflow intent unchanged and avoid introducing "
            "new services unless the existing config already expects them."
        )
        tasks.append(make_task(len(tasks) + 1, "docker_ci", repo, language, framework, rng.choice(["easy", "medium", "medium"]), description, files, rng))

    for _ in range(CATEGORY_COUNTS["typing_lint_build"]):
        area, language, framework, files = rng.choice(TYPING_LINT_AREAS)
        repo = rng.choice(REPOS["react"] if language == "TypeScript" else REPOS["fastapi"])
        description = (
            f"Fix a typing/lint/build issue to {area}. Make the smallest code change that satisfies the configured "
            "checks without weakening lint, type, or build settings."
        )
        tasks.append(make_task(len(tasks) + 1, "typing_lint_build", repo, language, framework, rng.choice(["easy", "medium"]), description, files, rng))

    for _ in range(CATEGORY_COUNTS["documentation_to_code"]):
        area, language, framework, files = rng.choice(DOC_TO_CODE_AREAS)
        repo = rng.choice(REPOS["react"] if language == "TypeScript" else REPOS["fastapi"])
        description = (
            f"Bring implementation in line with documentation: {area}. Treat the docs as the source of expected "
            "behavior, but do not include a solved patch in the task record."
        )
        tasks.append(make_task(len(tasks) + 1, "documentation_to_code", repo, language, framework, rng.choice(["medium", "hard"]), description, files, rng))

    return tasks


def validate_tasks(tasks: list[dict[str, Any]]) -> None:
    if len(tasks) != 1000:
        raise ValueError(f"Expected 1000 tasks, generated {len(tasks)}")

    type_counts: dict[str, int] = {
        "react_typescript_bug_fix": 0,
        "python_fastapi_bug_fix": 0,
        "test_writing": 0,
        "refactor": 0,
        "docker_ci": 0,
        "typing_lint_build": 0,
        "documentation_to_code": 0,
    }

    seen_ids: set[str] = set()
    for task in tasks:
        missing = [field for field in REQUIRED_FIELDS if field not in task]
        if missing:
            raise ValueError(f"{task.get('task_id', '<unknown>')} missing fields: {missing}")
        if task["task_id"] in seen_ids:
            raise ValueError(f"Duplicate task_id: {task['task_id']}")
        seen_ids.add(task["task_id"])
        if not isinstance(task["expected_files"], list) or not 1 <= len(task["expected_files"]) <= 3:
            raise ValueError(f"{task['task_id']} expected_files must contain 1 to 3 paths")
        if any(forbidden in task for forbidden in ("patch", "solution", "dataset_ready", "test_results")):
            raise ValueError(f"{task['task_id']} contains a forbidden solved-data field")

        if task["task_type"] == "bug_fix" and task["language"] == "TypeScript" and task["framework"] == "React":
            type_counts["react_typescript_bug_fix"] += 1
        elif task["task_type"] == "bug_fix" and task["language"] == "Python" and task["framework"] == "FastAPI":
            type_counts["python_fastapi_bug_fix"] += 1
        else:
            type_counts[task["task_type"]] += 1

    if type_counts != CATEGORY_COUNTS:
        raise ValueError(f"Category counts mismatch: {type_counts}")


def write_jsonl(tasks: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for task in tasks:
            file.write(json.dumps(task, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    tasks = generate_tasks()
    validate_tasks(tasks)
    write_jsonl(tasks)
    print(f"Wrote {len(tasks)} tasks to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
