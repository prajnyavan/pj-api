#!/usr/bin/env python3
"""Generate a deterministic starter queue of candidate coding tasks."""

from __future__ import annotations

import argparse
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

PJ_API_PILOT_TASKS = [
    (
        "bug_fix",
        "easy",
        "Fix auth token handling. Actual behavior: an Authorization header without a token is treated like a generic invalid token. "
        "Expected behavior: `Bearer` with no token should return 401 with detail `Missing authorization token`. "
        "Existing failing test: `test_bearer_without_token_returns_missing_token`.",
        ["app/routes/auth.py", "app/services/auth_service.py", "tests/test_auth.py"],
    ),
    (
        "bug_fix",
        "easy",
        "Fix auth scheme handling. Actual behavior: `Token valid-token` is accepted when the token text matches. "
        "Expected behavior: only the Bearer scheme should authenticate. Existing failing test: `test_non_bearer_scheme_returns_401`.",
        ["app/services/auth_service.py", "tests/test_auth.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix user creation id allocation. Actual behavior: creating a user after the in-memory store is empty raises `ValueError`. "
        "Expected behavior: the first created user should receive id 1. Existing failing test: `test_create_user_when_store_is_empty`.",
        ["app/routes/users.py", "app/db/session.py", "tests/test_users.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix email normalization. Actual behavior: emails with surrounding spaces are stored with those spaces. "
        "Expected behavior: user creation should trim email whitespace before storing. Existing failing test: `test_create_user_trims_email_whitespace`.",
        ["app/schemas/user.py", "tests/test_users.py"],
    ),
    (
        "bug_fix",
        "easy",
        "Fix user name normalization. Actual behavior: names with surrounding spaces are returned unchanged. "
        "Expected behavior: user creation should trim name whitespace before storing. Existing failing test: `test_create_user_trims_name_whitespace`.",
        ["app/schemas/user.py", "tests/test_users.py"],
    ),
    (
        "bug_fix",
        "easy",
        "Fix invalid user id status. Actual behavior: `/users/-1` returns 400 with a generic detail. "
        "Expected behavior: it should return 422 with detail `User id must be greater than zero`. "
        "Existing failing test: `test_negative_user_id_returns_validation_error`.",
        ["app/routes/users.py", "tests/test_users.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix health response shape. Actual behavior: `/health` omits the service name. "
        "Expected behavior: the response should include `service: pj-api` while preserving status and version. "
        "Existing failing test: `test_health_check_includes_service_name`.",
        ["app/routes/health.py", "tests/test_health.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix auth error consistency. Actual behavior: missing and invalid credentials return different response shapes after exception handling is customized. "
        "Expected behavior: both should use FastAPI HTTPException with a string `detail`. Existing failing test: `test_auth_errors_use_string_detail`.",
        ["app/routes/auth.py", "tests/test_auth.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix duplicate email handling. Actual behavior: creating a user with an existing email creates a duplicate record. "
        "Expected behavior: duplicate email should return 409. Existing failing test: `test_create_user_rejects_duplicate_email`.",
        ["app/routes/users.py", "app/db/session.py", "tests/test_users.py"],
    ),
    (
        "bug_fix",
        "medium",
        "Fix case-insensitive email uniqueness. Actual behavior: `Ada@Example.com` and `ada@example.com` are treated as different users. "
        "Expected behavior: duplicate checks should compare normalized lowercase email values. "
        "Existing failing test: `test_create_user_rejects_case_insensitive_duplicate_email`.",
        ["app/routes/users.py", "app/schemas/user.py", "tests/test_users.py"],
    ),
    (
        "test_writing",
        "easy",
        "Add focused auth tests for malformed Authorization headers. Target test name: `test_malformed_authorization_header_returns_401`. "
        "Do not change production behavior unless a tiny fix is required to make the documented auth behavior pass.",
        ["tests/test_auth.py", "app/routes/auth.py"],
    ),
    (
        "test_writing",
        "easy",
        "Add health endpoint tests that assert stable response keys. Target test name: `test_health_response_has_only_expected_keys`. "
        "Avoid snapshot-style assertions outside this endpoint.",
        ["tests/test_health.py", "app/routes/health.py"],
    ),
    (
        "test_writing",
        "medium",
        "Add user creation validation tests for empty name and invalid email format. "
        "Target tests: `test_empty_name_returns_422` and `test_invalid_email_returns_422`.",
        ["tests/test_users.py", "app/schemas/user.py"],
    ),
    (
        "test_writing",
        "medium",
        "Add tests proving unknown users return 404 without mutating the in-memory user store. "
        "Target test name: `test_missing_user_does_not_mutate_store`.",
        ["tests/test_users.py", "app/db/session.py"],
    ),
    (
        "refactor",
        "medium",
        "Refactor auth validation so parsing the Authorization header is isolated in `auth_service.py`. "
        "Keep endpoint behavior unchanged and keep all existing tests passing.",
        ["app/routes/auth.py", "app/services/auth_service.py", "tests/test_auth.py"],
    ),
    (
        "refactor",
        "medium",
        "Refactor user lookup into a small helper in `users.py` to remove repeated HTTPException construction. "
        "Keep route paths, status codes, and response models unchanged.",
        ["app/routes/users.py", "tests/test_users.py"],
    ),
    (
        "refactor",
        "easy",
        "Refactor health metadata so the API version is defined once and reused by `app/main.py` and the health route. "
        "Keep `/health` response unchanged.",
        ["app/main.py", "app/routes/health.py", "tests/test_health.py"],
    ),
    (
        "typing_lint_build",
        "easy",
        "Resolve strict typing for the in-memory user store by introducing a shared type alias. Do not change runtime behavior.",
        ["app/db/session.py", "app/routes/users.py"],
    ),
    (
        "typing_lint_build",
        "easy",
        "Tighten the auth service return path so ruff and type checkers see one clear boolean expression for valid Bearer tokens. "
        "Do not change accepted credentials.",
        ["app/services/auth_service.py", "tests/test_auth.py"],
    ),
    (
        "documentation_to_code",
        "medium",
        "Bring README API documentation in line with implementation by documenting `/health`, `/auth/validate`, and `/users/{user_id}` "
        "with expected status codes. Do not include solved patches in the task record.",
        ["README.md", "app/routes/health.py", "app/routes/auth.py"],
    ),
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
    return hashlib.sha1(f"{SEED}:{repo_name}".encode()).hexdigest()


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


def make_grounded_task(
    index: int,
    repo_name: str,
    repo_path: str,
    base_commit: str,
    task_type: str,
    difficulty: str,
    description: str,
    expected_files: list[str],
) -> dict[str, Any]:
    return {
        "task_id": f"{repo_name}-{index:04d}",
        "repo_name": repo_name,
        "repo_path": repo_path,
        "base_commit": base_commit,
        "task_type": task_type,
        "language": "Python",
        "framework": "FastAPI",
        "difficulty": difficulty,
        "description": description,
        "expected_files": expected_files,
        "test_command": "pytest",
        "build_command": "python -m compileall app",
        "lint_command": "ruff check .",
        "constraints": {
            "candidate_only": True,
            "no_patch_in_task": True,
            "no_fake_test_results": True,
            "independent_verifier_required": True,
            "allow_new_dependencies": False,
            "max_expected_files": 3,
            "keep_scope_small": True,
        },
    }


def generate_pj_api_tasks(base_commit: str, count: int, repo_path: str) -> list[dict[str, Any]]:
    if count < 1 or count > len(PJ_API_PILOT_TASKS):
        raise ValueError(f"pj-api grounded mode supports 1 to {len(PJ_API_PILOT_TASKS)} tasks")

    tasks = []
    for index, (task_type, difficulty, description, expected_files) in enumerate(PJ_API_PILOT_TASKS[:count], start=1):
        tasks.append(
            make_grounded_task(
                index=index,
                repo_name="pj-api",
                repo_path=repo_path,
                base_commit=base_commit,
                task_type=task_type,
                difficulty=difficulty,
                description=description,
                expected_files=expected_files,
            )
        )
    return tasks


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


def validate_task_shape(tasks: list[dict[str, Any]], expected_count: int) -> None:
    if len(tasks) != expected_count:
        raise ValueError(f"Expected {expected_count} tasks, generated {len(tasks)}")

    seen_ids: set[str] = set()
    for task in tasks:
        missing = [field for field in REQUIRED_FIELDS if field not in task]
        if missing:
            raise ValueError(f"{task.get('task_id', '<unknown>')} missing fields: {missing}")
        if task["task_id"] in seen_ids:
            raise ValueError(f"Duplicate task_id: {task['task_id']}")
        seen_ids.add(task["task_id"])
        if not isinstance(task["expected_files"], list) or not 1 <= len(task["expected_files"]) <= task["constraints"]["max_expected_files"]:
            raise ValueError(f"{task['task_id']} expected_files exceeds max_expected_files")
        if any(forbidden in task for forbidden in ("patch", "solution", "dataset_ready", "test_results")):
            raise ValueError(f"{task['task_id']} contains a forbidden solved-data field")


def write_jsonl(tasks: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for task in tasks:
            file.write(json.dumps(task, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SKB Coding Data Factory candidate task queues.")
    parser.add_argument("--repo", choices=["pj-api"], help="Generate a grounded repo-specific queue.")
    parser.add_argument("--base-commit", help="Real base commit SHA for grounded repo mode.")
    parser.add_argument("--count", type=int, default=20, help="Number of grounded tasks to generate.")
    parser.add_argument("--repo-path", help="Repo path to write into each grounded task.")
    parser.add_argument("--output", type=Path, help="Output JSONL path.")
    args = parser.parse_args()

    if args.repo == "pj-api":
        if not args.base_commit:
            raise SystemExit("--base-commit is required for grounded repo mode")
        repo_path = args.repo_path or "repos/pj-api"
        output_path = args.output or Path("tasks/pilot_20.jsonl")
        tasks = generate_pj_api_tasks(args.base_commit, args.count, repo_path)
        validate_task_shape(tasks, args.count)
        write_jsonl(tasks, output_path)
    else:
        output_path = args.output or OUTPUT_PATH
        tasks = generate_tasks()
        validate_tasks(tasks)
        write_jsonl(tasks, output_path)

    print(f"Wrote {len(tasks)} tasks to {output_path}")


if __name__ == "__main__":
    main()
