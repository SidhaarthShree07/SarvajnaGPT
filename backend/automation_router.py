"""CUA-only Automation Router (pure)

This module provides a minimal set of automation endpoints implemented purely
via the CUA adapter, with no Win32, COM, or UIAutomation dependencies.

Scope and design:
- Keep familiar endpoint shapes where reasonable (/cua/status, /word/execute,
  /word/open_existing, /shim/info).
- Avoid window enumeration, OS hotkeys, or COM automation.
- Best-effort actions only; relies on the user (or caller) to have Word open
  and focused, or for the environment to present Snap Assist tiles.

Note: If you later replace your existing automation router with this one,
functionality will be limited to what `cua_adapter` exposes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os

router = APIRouter(prefix="/api/automation", tags=["automation"])

# Soft imports for CUA adapter
try:  # Prefer package-relative, then bare
    from .cua_adapter import (
        cua_runtime_status,
        select_snap_assist_tile,
        snap_current_and_select,
        open_path as cua_open_path,
    )  # type: ignore
except Exception:  # pragma: no cover
    try:
        from cua_adapter import (
            cua_runtime_status,
            select_snap_assist_tile,
            snap_current_and_select,
            open_path as cua_open_path,
        )  # type: ignore
    except Exception:
        cua_runtime_status = None  # type: ignore
        select_snap_assist_tile = None  # type: ignore


# Models matching prior expectations (pared down)
class WordTypeRequest(BaseModel):
    text: str = Field(..., description="Text intended for Word (CUA-only; typing not guaranteed)")
    snap: bool | None = Field(False, description="Attempt selecting a 'Word' Snap Assist tile")


class WordOpenExistingRequest(BaseModel):
    path: str = Field(..., description="Path to an existing .docx (best-effort open via OS shell)")
    split_screen: bool | None = Field(True, description="If True, attempt CUA tile selection for Word")


class VSCodeOpenRequest(BaseModel):  # kept for import compatibility in callers
    path: str
    line: Optional[int] = None
    column: Optional[int] = None


# Helpers

def _status() -> Dict[str, Any]:
    if callable(cua_runtime_status):  # type: ignore[truthy-bool]
        try:
            st = cua_runtime_status()  # type: ignore[misc]
            if isinstance(st, dict):
                return st
        except Exception:
            pass
    return {"available": False, "detail": "cua_runtime_status unavailable"}


def _select_word_tile(tokens: Optional[list[str]] = None) -> Dict[str, Any]:
    if not callable(select_snap_assist_tile):  # type: ignore[truthy-bool]
        return {"attempted": False, "selected": False, "reason": "select_snap_assist_tile_unavailable"}
    used = tokens or ["word", "microsoft word"]
    try:
        sel = bool(select_snap_assist_tile(used))  # type: ignore[misc]
        return {"attempted": True, "selected": sel, "tokens": used}
    except Exception as e:  # pragma: no cover
        return {"attempted": True, "selected": False, "tokens": used, "error": str(e)}


# Routes
@router.get("/cua/status")
def cua_status() -> Dict[str, Any]:
    return {"ok": True, "status": _status()}


@router.post("/word/execute")
def word_execute(req: WordTypeRequest) -> Dict[str, Any]:
    if not req.text:
        raise HTTPException(status_code=400, detail="text is required")
    snap_result: Dict[str, Any] | None = None
    if bool(req.snap):
        # Prefer the higher-level helper if available
        if callable(snap_current_and_select):  # type: ignore[truthy-bool]
            snap_result = snap_current_and_select(["word"])  # type: ignore[misc]
        else:
            snap_result = _select_word_tile()
    # No direct typing in CUA-only baseline; just acknowledge intent
    return {
        "ok": True,
        "action": "word_execute_cua_only",
        "intent_text_len": len(req.text),
        "snap": snap_result or {"attempted": False, "selected": False},
        "cua_only": True,
    }


@router.post("/word/open_existing")
def word_open_existing(req: WordOpenExistingRequest) -> Dict[str, Any]:
    p = Path(req.path).expanduser()
    exists = p.is_file()
    launched = False
    if exists:
        try:
            r = cua_open_path(str(p)) if callable(cua_open_path) else {"ok": False}
            launched = bool(r.get("ok"))
        except Exception:
            launched = False
    snap_result: Dict[str, Any] | None = None
    if bool(req.split_screen):
        tokens = [p.stem, "microsoft word", "word"] if exists else ["word"]
        if callable(snap_current_and_select):  # type: ignore[truthy-bool]
            snap_result = snap_current_and_select(tokens)  # type: ignore[misc]
        else:
            snap_result = _select_word_tile(tokens)
    return {
        "ok": True,
        "exists": exists,
        "launched": launched,
        "path": str(p),
        "snap": snap_result or {"attempted": False, "selected": False},
        "note": "CUA-only: opening is best-effort; selection relies on Snap Assist tiles.",
    }


@router.get("/shim/info")
def shim_info() -> Dict[str, Any]:
    return {
        "ok": True,
        "mode": "cua-only-pure",
        "routes": [
            "/api/automation/cua/status",
            "/api/automation/word/execute",
            "/api/automation/word/open_existing",
            "/api/automation/inline-selection",
        ],
    }


# Minimal inline selection endpoint for backward compatibility
@router.get("/inline-selection")
def inline_selection() -> Dict[str, Any]:
    try:
        status = _status()
    except Exception:
        status = {"available": False}
    return {
        "ok": True,
        "available": bool(status.get("core_import") or status.get("repo_dir_present")),
        "status": status,
        "note": "inline-selection is a compatibility no-op in CUA-only mode",
    }


# Compatibility stubs

def vscode_open_existing(_req: VSCodeOpenRequest) -> Dict[str, Any]:
    return {"ok": False, "detail": "VS Code automation not included in cua-only-pure"}


def _word_execute_impl(*_a: Any, **_k: Any) -> Dict[str, Any]:
    return {"ok": False, "detail": "_word_execute_impl not available in cua-only-pure"}


def replace_word_selection(*_a: Any, **_k: Any) -> bool:
    return False


__all__ = [
    "router",
    "WordTypeRequest", "WordOpenExistingRequest", "VSCodeOpenRequest",
    "cua_status", "word_execute", "word_open_existing", "shim_info",
    "vscode_open_existing", "_word_execute_impl", "replace_word_selection",
]
