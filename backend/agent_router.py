from __future__ import annotations

import os
import uuid
import json
import datetime as dt
from enum import Enum
from typing import Optional, List, Literal, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator


router = APIRouter(prefix="/api/agent", tags=["agent"])


# Offline-only: restrict actions to a safe, allowlisted base directory
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
AGENT_BASE_DIR = os.path.join(REPO_ROOT, "agent_output")
AUDIT_LOG = os.path.join(REPO_ROOT, "agent_audit.jsonl")

os.makedirs(AGENT_BASE_DIR, exist_ok=True)


class ActionType(str, Enum):
    FS_CREATE_FOLDER = "fs.create_folder"
    FS_WRITE_FILE = "fs.write_file"


class FSCreateFolderParams(BaseModel):
    # Relative path from AGENT_BASE_DIR, or absolute under that directory
    parent_path: str = Field(..., description="Parent directory (relative or absolute under allowlist)")
    name: str = Field(..., min_length=1, max_length=255)

    @validator("parent_path")
    def validate_parent(cls, v: str) -> str:
        return v.strip()


class FSWriteFileParams(BaseModel):
    absolute_path: Optional[str] = Field(None, description="Absolute path; must be under allowlist")
    relative_path: Optional[str] = Field(None, description="Relative path under allowlist")
    content: str = Field("")
    encoding: str = Field("utf-8")

    @validator("encoding")
    def validate_encoding(cls, v: str) -> str:
        try:
            """Validate encoding is supported."""
            "test".encode(v)
            return v
        except Exception:
            raise ValueError("Unsupported encoding")


class Action(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ActionType
    params: Union[FSCreateFolderParams, FSWriteFileParams]
    preview_only: bool = False


class PlanRequest(BaseModel):
    # For MVP we accept actions directly; planning via LLM comes later.
    actions: List[Action]


class NaturalLanguagePlanRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language objective for agent")
    execute: bool = Field(True, description="Whether to immediately execute the planned actions")
    base_folder: str = Field("project", description="Top-level folder (relative) to place generated artifacts if needed")

class NaturalLanguagePlanResponse(BaseModel):
    prompt: str
    raw_plan: str
    actions: List[Action]
    executed: bool
    execution_results: Optional[List[ExecuteResponse]] = None
    previews: Optional[List[PreviewResponse]] = None


class PreviewResponse(BaseModel):
    action: Action
    summary: str
    target_path: Optional[str] = None


class ExecuteResponse(BaseModel):
    id: str
    type: ActionType
    result: dict


class AuditEntry(BaseModel):
    timestamp: str
    action: Action
    summary: str
    result: Optional[dict] = None
    error: Optional[str] = None


def _to_abs_under_base(path_like: str) -> str:
    """Resolve to absolute path and ensure it's under AGENT_BASE_DIR."""
    if not path_like:
        raise HTTPException(status_code=400, detail="Path is required")
    # If absolute, use as-is, else join with base
    p = path_like
    if not os.path.isabs(p):
        p = os.path.join(AGENT_BASE_DIR, p)
    p = os.path.abspath(p)
    # Ensure under base
    base = os.path.abspath(AGENT_BASE_DIR)
    if os.path.commonpath([p, base]) != base:
        raise HTTPException(status_code=403, detail="Path outside allowed directory")
    return p


def _append_audit(entry: AuditEntry) -> None:
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.dict()) + "\n")
    except Exception:
        # Silent failure of audit must not break main path
        pass


@router.post("/plan")
def plan(req: PlanRequest) -> dict:
    # MVP: return actions as-is; real planning (LLM) later.
    previews = []
    for a in req.actions:
        previews.append(_preview_action(a).dict())
    return {"actions": [p["action"] for p in previews], "previews": previews}


@router.post("/preview", response_model=PreviewResponse)
def preview(action: Action) -> PreviewResponse:
    return _preview_action(action)


# ---------------- Natural Language Auto Planning -----------------
try:
    from .llm_inference import generate_response as _agent_llm
except Exception:  # pragma: no cover
    def _agent_llm(prompt: str) -> str:
        return '{"actions": []}'

_PLAN_SYSTEM = (
    "You are an offline code automation planner. Return STRICT JSON with key 'actions' only. "
    "Each action must have: type (fs.create_folder | fs.write_file) and params. "
    "For fs.create_folder: params: {\"parent_path\": string, \"name\": string}. "
    "For fs.write_file: params: {\"relative_path\": string, \"content\": string}. "
    "Avoid explanations. Do not wrap JSON in markdown. Keep paths relative."
)

def _coerce_actions_from_json(raw: str, base_folder: str) -> List[Action]:
    try:
        data = json.loads(raw)
    except Exception:
        return []
    acts = []
    arr = data.get('actions') if isinstance(data, dict) else None
    if not isinstance(arr, list):
        return []
    for item in arr:
        if not isinstance(item, dict):
            continue
        atype = item.get('type')
        params = item.get('params') or {}
        try:
            if atype == ActionType.FS_CREATE_FOLDER:
                parent = params.get('parent_path') or base_folder
                name = params.get('name') or 'new_folder'
                acts.append(Action(type=ActionType.FS_CREATE_FOLDER, params=FSCreateFolderParams(parent_path=parent, name=name)))
            elif atype == ActionType.FS_WRITE_FILE:
                rel = params.get('relative_path') or f"{base_folder}/generated.txt"
                content = params.get('content') or ''
                # guard content length
                if len(content) > 200_000:
                    content = content[:200_000]
                acts.append(Action(type=ActionType.FS_WRITE_FILE, params=FSWriteFileParams(relative_path=rel, content=content)))
        except Exception:
            continue
    return acts

@router.post('/autoplan', response_model=NaturalLanguagePlanResponse)
def autoplan(req: NaturalLanguagePlanRequest) -> NaturalLanguagePlanResponse:
    user_prompt = req.prompt.strip()
    composite = _PLAN_SYSTEM + "\nUser Request:\n" + user_prompt + "\nReturn JSON now."  # single prompt paradigm
    raw_plan = _agent_llm(composite)
    actions = _coerce_actions_from_json(raw_plan, req.base_folder)
    previews: List[PreviewResponse] = []
    for a in actions:
        try:
            previews.append(_preview_action(a))
        except HTTPException:
            continue
    executed = False
    execution_results: Optional[List[ExecuteResponse]] = None
    if req.execute and actions:
        try:
            execution_results = execute(actions)
            executed = True
        except HTTPException as he:
            # partial failure: still return what we have
            executed = False
    return NaturalLanguagePlanResponse(
        prompt=user_prompt,
        raw_plan=raw_plan,
        actions=actions,
        executed=executed,
        execution_results=execution_results,
        previews=previews,
    )

def _preview_action(action: Action) -> PreviewResponse:
    if action.type == ActionType.FS_CREATE_FOLDER:
        params = action.params  # type: ignore
        parent_abs = _to_abs_under_base(params.parent_path)
        target = os.path.join(parent_abs, params.name)
        summary = f"Create folder '{params.name}' under '{os.path.relpath(parent_abs, AGENT_BASE_DIR)}'"
        return PreviewResponse(action=action, summary=summary, target_path=target)
    elif action.type == ActionType.FS_WRITE_FILE:
        params = action.params  # type: ignore
        if params.absolute_path:
            target = _to_abs_under_base(params.absolute_path)
        elif params.relative_path:
            target = _to_abs_under_base(params.relative_path)
        else:
            raise HTTPException(status_code=400, detail="Provide absolute_path or relative_path")
        rel = os.path.relpath(target, AGENT_BASE_DIR)
        summary = f"Write file '{rel}' (encoding={params.encoding})"
        return PreviewResponse(action=action, summary=summary, target_path=target)
    else:
        raise HTTPException(status_code=400, detail="Unknown action type")

@router.post("/execute", response_model=List[ExecuteResponse])
def execute(actions: List[Action]) -> List[ExecuteResponse]:
    results: List[ExecuteResponse] = []
    for a in actions:
        prev = _preview_action(a)
        err: Optional[str] = None
        out: Optional[dict] = None
        try:
            if a.type == ActionType.FS_CREATE_FOLDER:
                target = prev.target_path or _to_abs_under_base(os.path.join(a.params.parent_path, a.params.name))  # type: ignore
                os.makedirs(target, exist_ok=True)
                out = {"created": True, "path": target}
            elif a.type == ActionType.FS_WRITE_FILE:
                target = prev.target_path
                if not target:
                    raise HTTPException(status_code=400, detail="Target resolution failed")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                p = a.params  # type: ignore
                with open(target, "w", encoding=p.encoding) as f:
                    f.write(p.content or "")
                out = {"written": True, "path": target, "bytes": len((p.content or "").encode(p.encoding))}
            else:
                raise HTTPException(status_code=400, detail="Unknown action type")
        except HTTPException as he:
            err = he.detail if isinstance(he.detail, str) else str(he.detail)
        except Exception as e:
            err = str(e)

        entry = AuditEntry(
            timestamp=dt.datetime.utcnow().isoformat() + "Z",
            action=a,
            summary=prev.summary,
            result=out,
            error=err,
        )
        _append_audit(entry)

        if err:
            raise HTTPException(status_code=500, detail=f"Action failed: {err}")
        results.append(ExecuteResponse(id=a.id, type=a.type, result=out or {}))
    return results


@router.get("/logs")
def logs(limit: int = 50) -> dict:
    entries: List[dict] = []
    try:
        if os.path.isfile(AUDIT_LOG):
            with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()[-limit:]
                for ln in lines:
                    try:
                        entries.append(json.loads(ln))
                    except Exception:
                        continue
    except Exception:
        pass
    return {"entries": entries, "base_dir": AGENT_BASE_DIR}
