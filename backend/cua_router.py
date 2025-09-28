from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict

from cua_adapter import preview_objective, execute_objective, cua_available
from llm_inference import generate_response


router = APIRouter(prefix="/api/cua", tags=["cua"])


class CuaPreviewRequest(BaseModel):
    objective: str = Field(..., min_length=5)
    target_rel: str = Field(..., description="Relative path under agent_output for the artifact")


class CuaExecuteRequest(CuaPreviewRequest):
    seed_files: Optional[Dict[str, str]] = None


@router.get("/status")
def status() -> dict:
    return {"available": cua_available()}


@router.post("/preview")
def preview(req: CuaPreviewRequest) -> dict:
    try:
        return preview_objective(req.objective, req.target_rel)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute")
def execute(req: CuaExecuteRequest) -> dict:
    try:
        return execute_objective(req.objective, req.target_rel, req.seed_files)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CuaPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="User request to turn into a CUA objective")
    default_target_rel: str = Field("cua_runs/output.txt")


@router.post("/plan")
def plan(req: CuaPlanRequest) -> dict:
    """Use the local LLM (Ollama) to produce a tiny JSON plan for CUA.
    We instruct it strictly to return JSON with fields objective and target_rel only.
    """
    system = (
        "You are a planner that outputs strict JSON with keys 'objective' and 'target_rel'. "
        "Do not include markdown or explanations. Keep objective concise."
    )
    user = f"Prompt: {req.prompt}\nDefault target_rel: {req.default_target_rel}"
    # generate_response sends a single prompt; emulate system+user in one message
    raw = generate_response(system + "\n\n" + user + "\nReturn JSON only.")
    # Best-effort JSON extraction
    import json as _json
    objective = None
    target_rel = req.default_target_rel
    try:
        obj = _json.loads(raw)
        objective = str(obj.get("objective") or "").strip() or None
        tr = obj.get("target_rel")
        if tr and isinstance(tr, str) and tr.strip():
            target_rel = tr.strip()
    except Exception:
        # fallback: use first line of text as objective
        objective = raw.splitlines()[0].strip() if raw else None
    if not objective:
        raise HTTPException(status_code=400, detail="Planner failed to produce objective")
    preview = preview_objective(objective, target_rel)
    return {"objective": objective, "target_rel": target_rel, "preview": preview}
