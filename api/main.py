from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from datasets.build_dpo import build_dpo
from datasets.build_sft import build_sft
from ops.scorecard import build_scorecard

app = FastAPI(title="SKB Coding Data Factory API", version="0.1.0")
TRACES_DIR = Path("traces")


class RunStartRequest(BaseModel):
    repo_name: str
    repo_path: str
    target_verified: int
    max_candidates: int
    worker: str = "stub"
    test_command: str = "pytest"
    build_command: str = "python -m compileall app"
    lint_command: str = "ruff check ."


def load_trace_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


@app.post("/runs/start")
def start_run(request: RunStartRequest) -> dict[str, object]:
    run_id = f"run-{uuid4().hex[:12]}"
    runs_dir = TRACES_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run = request.model_dump()
    run.update({"run_id": run_id, "status": "created"})
    (runs_dir / f"{run_id}.json").write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    path = TRACES_DIR / "runs" / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/scorecard")
def get_scorecard() -> dict:
    return build_scorecard(TRACES_DIR)


@app.get("/traces/verified")
def get_verified_traces() -> list[dict]:
    return load_trace_list(TRACES_DIR / "verified")


@app.get("/traces/rejected")
def get_rejected_traces() -> list[dict]:
    return load_trace_list(TRACES_DIR / "rejected")


@app.post("/datasets/build")
def build_datasets() -> dict[str, int]:
    return {
        "sft_rows": build_sft(TRACES_DIR / "verified", Path("datasets/sft_train.jsonl")),
        "dpo_rows": build_dpo(TRACES_DIR / "verified", TRACES_DIR / "rejected", Path("datasets/dpo_train.jsonl")),
    }
