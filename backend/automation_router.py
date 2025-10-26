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
        capture_inline_selection,
        get_clipboard_text_preview,
        ensure_focus_top,
        focus_previous_window,
        focus_window_by_tokens,
    )  # type: ignore
except Exception:  # pragma: no cover
    try:
        from cua_adapter import (
            cua_runtime_status,
            select_snap_assist_tile,
            snap_current_and_select,
            open_path as cua_open_path,
            capture_inline_selection,
            get_clipboard_text_preview,
            ensure_focus_top,
            focus_previous_window,
            focus_window_by_tokens,
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
            "/api/automation/inline-selection/passive",
            "/api/automation/inline-selection/assist",
        ],
    }
# Active clipboard selection (sends Ctrl+C but does not change focus)
@router.get("/inline-selection/passive")
def inline_selection_passive() -> Dict[str, Any]:
    """Capture current selection via Ctrl+C without changing window focus.
    
    Sends Ctrl+C to copy selection, reads clipboard, then restores prior clipboard content.
    Works with any app (Word, browser, Code, etc.) as long as text is selected.
    """
    try:
        if callable(get_clipboard_text_preview):  # type: ignore[truthy-bool]
            res = get_clipboard_text_preview()  # type: ignore[misc]
            if isinstance(res, dict):
                res.setdefault('ok', True)
                res.setdefault('selections', [])
                res.setdefault('primary', 'foreground')
                if not res.get('selections'):
                    res.setdefault('reason', 'No active selection detected')
                return res
    except Exception as e:
        return {"ok": True, "selections": [], "primary": "foreground", "errors": [str(e)[:160]]}
    return {"ok": True, "selections": [], "primary": "foreground", "reason": "No active selection detected"}


# Minimal inline selection endpoint for backward compatibility
@router.get("/inline-selection")
def inline_selection() -> Dict[str, Any]:
    """Return best-effort snapshot of current inline selection from the foreground window.

    Response shape:
    { ok: bool, selections: [ { source, label, preview, length, timestamp } ], primary: 'foreground', errors?: [] }
    """
    try:
        if callable(capture_inline_selection):  # type: ignore[truthy-bool]
            res = capture_inline_selection()  # type: ignore[misc]
            if isinstance(res, dict):
                # Ensure required fields are present for the frontend
                res.setdefault('ok', True)
                res.setdefault('selections', [])
                res.setdefault('primary', 'foreground')
                return res
    except Exception as e:
        return {"ok": True, "selections": [], "primary": "foreground", "errors": [str(e)[:160]]}
    # Fallback when helper unavailable
    st = _status()
    return {
        "ok": True,
        "selections": [],
        "primary": "foreground",
        "errors": ["capture_inline_selection_unavailable"],
        "status": st,
        "reason": "No active selection detected",
    }


# Assisted inline selection that momentarily focuses a target app before copying,
# then returns focus back (best-effort). Useful when the browser has focus.
@router.get("/inline-selection/assist")
def inline_selection_assist(target: str = "word") -> Dict[str, Any]:
    """Attempt to capture selection from a specific target app by focusing it briefly.

    Query params:
    - target: 'word' | 'code' | 'browser' (defaults to 'word')

    Returns the same shape as /inline-selection, plus {assisted: true, target, focus: {focused: bool, restored: bool}}
    """
    # Map targets to common window title tokens; diacritics are normalized in helper
    target = (target or "").strip().lower() or "word"
    token_map = {
        "word": ["microsoft word", "word"],
        "code": ["visual studio code", "vs code", "vscode", "code"],
        # Generic browser fallback; we can't know exact tab title reliably here
        "browser": ["microsoft edge", "edge", "google chrome", "chrome", "mozilla firefox", "firefox", "brave"],
    }
    toks = token_map.get(target, token_map["word"])
    focused_ok = False
    restored_ok = False
    try:
        if callable(ensure_focus_top):  # type: ignore[truthy-bool]
            focused_ok = bool(ensure_focus_top(toks))  # type: ignore[misc]
    except Exception:
        focused_ok = False

    # Perform the capture either way (if focus fails, this mirrors the basic endpoint outcome)
    try:
        if callable(capture_inline_selection):  # type: ignore[truthy-bool]
            res = capture_inline_selection()  # type: ignore[misc]
        else:
            res = {"ok": True, "selections": [], "primary": "foreground", "errors": ["capture_inline_selection_unavailable"]}
    except Exception as e:
        res = {"ok": True, "selections": [], "primary": "foreground", "errors": [str(e)[:160]]}

    # Best-effort return of focus back to the previous app (Alt+Tab once)
    try:
        if callable(focus_previous_window):  # type: ignore[truthy-bool]
            restored_ok = bool(focus_previous_window())  # type: ignore[misc]
    except Exception:
        restored_ok = False

    if isinstance(res, dict):
        res.setdefault('ok', True)
        res.setdefault('selections', [])
        res.setdefault('primary', 'foreground')
        res['assisted'] = True
        res['target'] = target
        res['focus'] = {'focused': bool(focused_ok), 'restored': bool(restored_ok)}
        # If nothing captured, provide a clearer reason
        if (not res.get('selections')):
            msg = f"No active selection detected (assisted {target})"
            # Only set reason/message if not already provided
            if 'reason' not in res:
                res['reason'] = msg
            if 'message' not in res:
                res['message'] = msg
        return res
    # Fallback guaranteed shape
    return {
        'ok': True,
        'selections': [],
        'primary': 'foreground',
        'assisted': True,
        'target': target,
        'focus': {'focused': bool(focused_ok), 'restored': bool(restored_ok)},
        'reason': f'No active selection detected (assisted {target})',
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
