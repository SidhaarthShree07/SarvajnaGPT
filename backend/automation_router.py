from __future__ import annotations

"""
Windows-only Word automation via COM (no mouse/keyboard hooks).
This controls Word directly to open a window, insert text, and optionally save.

Requires Microsoft Word installed and comtypes package.
"""
import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Callable, Dict, Any
import time as _time
import re
import threading

try:
    import win32clipboard  # type: ignore
    import win32con  # type: ignore
except Exception:  # pragma: no cover - optional dependency on Windows
    win32clipboard = None  # type: ignore
    win32con = None  # type: ignore

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
router = APIRouter(prefix="/api/automation", tags=["automation"])
# -------------------------- CUA Status Endpoints --------------------------
@router.get("/cua/status")
def cua_status() -> Dict[str, Any]:
    try:
        # Prefer absolute import to avoid "attempted relative import" when run as a script
        import backend.cua_adapter as cua_adapter  # type: ignore
    except Exception:
        try:
            import cua_adapter  # type: ignore
        except Exception as e2:
            return {'error': f'import_failed: {e2}'}
    try:
        status = cua_adapter.cua_runtime_status() if hasattr(cua_adapter, 'cua_runtime_status') else {'available': False}
        status['simple_available'] = bool(getattr(cua_adapter, 'cua_available', lambda: False)())
        # Normalize telemetry flag if present
        if 'telemetry_enabled' in status and status['telemetry_enabled'] is None:
            # Provide explicit False when unknown (older versions)
            status['telemetry_enabled'] = False
        return status
    except Exception as e:
        return {'error': str(e)}

@router.get("/cua/last-diagnostics")
def cua_last_diagnostics() -> Dict[str, Any]:
    try:
        import backend.cua_adapter as cua_adapter  # type: ignore
    except Exception:
        try:
            import cua_adapter  # type: ignore
        except Exception as e2:
            return {'error': f'import_failed: {e2}'}
    try:
        diag = getattr(cua_adapter, '_cua_diag_last', None)
        return {'diagnostics': diag}
    except Exception as e:
        return {'error': str(e)}

@router.get("/cua/enumerate-snap")
def cua_enumerate_snap(max_steps: int = 40) -> Dict[str, Any]:
    """Enumerate current Snap Assist focus cycle without selecting any tile.
    Ensure Snap Assist UI is open (e.g., after triggering Win+Arrow) before calling.
    """
    try:
        import backend.cua_adapter as cua_adapter  # type: ignore
    except Exception:
        try:
            import cua_adapter  # type: ignore
        except Exception as e2:
            return {'error': f'import_failed: {e2}'}
    try:
        if hasattr(cua_adapter, 'enumerate_snap_focus_cycle'):
            data = cua_adapter.enumerate_snap_focus_cycle(max_steps=max_steps)
            return {'enumeration': data}
        return {'error': 'enumerate_snap_focus_cycle_not_available'}
    except Exception as e:
        return {'error': str(e)}

@router.get("/cua/deep-diagnostics")
def cua_deep_diagnostics() -> Dict[str, Any]:
    """Return last diagnostics plus environment flags helpful for low-level debugging."""
    resp: Dict[str, Any] = {}
    try:
        import os as _os
        resp['env_flags'] = {k: v for k, v in _os.environ.items() if k.startswith('CUA_') or k.startswith('WIN_')}
    except Exception:
        resp['env_flags_error'] = True
    try:
        import backend.cua_adapter as cua_adapter  # type: ignore
    except Exception:
        try:
            import cua_adapter  # type: ignore
        except Exception as e2:
            resp['import_error'] = str(e2)
            return resp
    try:
        resp['last_diagnostics'] = getattr(cua_adapter, '_cua_diag_last', None)
        if hasattr(cua_adapter, 'cua_runtime_status'):
            resp['runtime_status'] = cua_adapter.cua_runtime_status()
    except Exception as e:
        resp['diagnostics_error'] = str(e)
    return resp
try:
    import comtypes.client  # type: ignore
except Exception:
    comtypes = None  # type: ignore
    comtypes_client = None  # type: ignore
else:
    comtypes_client = comtypes.client  # type: ignore


def _coinit() -> Optional[Callable[[], None]]:
    """Initialize COM in STA for the current thread and return an uninitializer.
    Tries pythoncom first (pywin32), then falls back to comtypes if available.
    """
    # pythoncom path
    try:
        import pythoncom  # type: ignore
        pythoncom.CoInitialize()
        return getattr(pythoncom, 'CoUninitialize', None)
    except Exception:
        pass
    # comtypes fallback
    try:
        import comtypes as _ct  # type: ignore
        _ci = getattr(_ct, 'CoInitialize', None)
        _cu = getattr(_ct, 'CoUninitialize', None)
        if callable(_ci):
            _ci()
            if callable(_cu):
                return _cu
            else:
                return None
    except Exception:
        pass
    return None


class WordTypeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to insert into a new Word document")
    show_window: bool = Field(True, description="Make Word visible")
    save_target: Optional[str] = Field(None, description="Relative path under agent_output to save .docx (optional)")
    split_screen: bool = Field(True, description="Place Word and current foreground window side-by-side")
    word_side: str = Field('right', description="Which side Word should occupy in split screen: 'left' or 'right'")
    fallback_snap: bool = Field(True, description="If pairing fails, snap Word to requested side anyway")
    arrangement_delay_ms: int = Field(600, ge=0, le=5000, description="Delay before arranging (ms) to let windows settle")
    use_os_snap_keys: bool = Field(True, description="Use OS Win+Arrow snapping for both windows when possible")
    # Default now True so automation prefers CUA path; if agent_ready this will be forced anyway.
    use_cua_for_selection: bool = Field(True, description="Prefer CUA (agent/computer) for Snap Assist selection; ignored (forced True) when CUA agent is ready")
    append: bool = Field(True, description="If save_target exists, append to the existing document instead of replacing its content")
    avoid_rearrange_if_already_split: bool = Field(True, description="Skip arranging windows if Word is already snapped to the requested side")

class WordOpenExistingRequest(BaseModel):
    abs_path: str = Field(..., description="Absolute path to an existing .docx to open")
    split_screen: bool = Field(True, description="Place Word and current foreground window side-by-side")
    word_side: str = Field('right', description="'left' or 'right'")
    fallback_snap: bool = Field(True, description="If pairing fails, snap Word to requested side anyway")
    arrangement_delay_ms: int = Field(600, ge=0, le=5000, description="Delay before arranging (ms) to let windows settle")
    
class VSCodeOpenRequest(BaseModel):
    abs_path: str = Field(..., description="Absolute path to a file to open in VS Code")
    split_screen: bool = Field(True, description="Place VS Code and current foreground window side-by-side")
    code_side: str = Field('right', description="Preferred VS Code side: 'left' or 'right'")
    fallback_snap: bool = Field(True, description="If pairing fails, snap VS Code to requested side anyway")
    use_os_snap_keys: bool = Field(True, description="Use OS Win+Arrow snapping for window arrangement")
    use_cua_for_selection: bool = Field(True, description="Prefer CUA Snap Assist selection when available")
    arrangement_delay_ms: int = Field(1000, ge=0, le=5000, description="Delay before arranging (ms) to let windows settle")


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
AGENT_BASE_DIR = os.path.join(REPO_ROOT, "agent_output")
os.makedirs(AGENT_BASE_DIR, exist_ok=True)


_split_state_lock = threading.Lock()
_split_state: Dict[str, Any] = {
    "flag": 0,
    "primary_hwnd": None,
    "partner_hwnd": None,
    "side": None,
    "target": None,
    "path": None,
    "last_set": 0.0,
    "last_checked": 0.0,
}
_split_monitor_thread: Optional[threading.Thread] = None


def _get_split_state_snapshot() -> Dict[str, Any]:
    with _split_state_lock:
        return dict(_split_state)


def _set_split_state(
    flag: int,
    *,
    primary_hwnd: Optional[int] = None,
    partner_hwnd: Optional[int] = None,
    side: Optional[str] = None,
    target: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    start_monitor = False
    with _split_state_lock:
        _split_state["flag"] = 1 if flag else 0
        _split_state["last_set"] = _time.time()
        if flag:
            _split_state["primary_hwnd"] = primary_hwnd
            _split_state["partner_hwnd"] = partner_hwnd
            _split_state["side"] = side
            _split_state["target"] = target
            _split_state["path"] = path
            start_monitor = True
        else:
            _split_state["primary_hwnd"] = None
            _split_state["partner_hwnd"] = None
            _split_state["side"] = None
            _split_state["target"] = None
            _split_state["path"] = None
    if start_monitor:
        _ensure_split_monitor_started()


def _ensure_split_monitor_started() -> None:
    """Lazily start the background checker that keeps the split flag honest."""
    global _split_monitor_thread
    if os.name != 'nt':
        return
    with _split_state_lock:
        thread = _split_monitor_thread
        if thread and thread.is_alive():
            return
        thread = threading.Thread(target=_split_monitor_loop, name="split-monitor", daemon=True)
        _split_monitor_thread = thread
    thread.start()


def _split_monitor_loop() -> None:
    while True:
        _time.sleep(5.0)
        if os.name != 'nt':
            continue
        state = _get_split_state_snapshot()
        if not state.get("flag"):
            continue
        if not _check_split_state_active(state):
            _set_split_state(0)
            continue
        with _split_state_lock:
            _split_state["last_checked"] = _time.time()


def _should_skip_automation(target: str, desired_path: Optional[str] = None) -> tuple[bool, Dict[str, Any]]:
    state = _get_split_state_snapshot()
    skip = False
    if state.get("flag") == 1 and state.get("target") == target:
        skip = True
        if desired_path:
            state_path = state.get("path")
            try:
                desired_abs = os.path.abspath(desired_path)
                state_abs = os.path.abspath(state_path) if state_path else None
                if state_abs and state_abs != desired_abs:
                    skip = False
            except Exception:
                skip = False
        if skip and not _check_split_state_active(state):
            skip = False
            _set_split_state(0)
    return skip, state


def _resolve_under_base(path_like: str) -> str:
    p = path_like
    if not os.path.isabs(p):
        p = os.path.join(AGENT_BASE_DIR, p)
    p = os.path.abspath(p)
    base = os.path.abspath(AGENT_BASE_DIR)
    if os.path.commonpath([p, base]) != base:
        raise ValueError("Target path outside agent base directory")
    return p


# -------------------------- Text Cleaning --------------------------
def _clean_markdown_to_text(text: str) -> str:
    """Best-effort: convert common Markdown to plain text that's safe to type into Word.
    - Remove heading markers (###, ##, #) but keep the text
    - Strip bold/italic markers (** __ * _)
    - Convert [label](url) to 'label (url)'; images to 'alt (url)'
    - Remove inline/backtick fences while keeping code content
    - Normalize list markers to bullets
    - Remove blockquote markers '>'
    - Tolerate long lines by keeping newlines as-is
    """
    if not text:
        return ''
    s = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove fenced code ticks but keep contents
    s = re.sub(r"```[\w-]*\n([\s\S]*?)\n```", r"\1", s)
    s = re.sub(r"```([\s\S]*?)```", r"\1", s)
    # Inline code
    s = re.sub(r"`([^`]*)`", r"\1", s)
    # Images ![alt](url)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1 (\2)", s)
    # Links [text](url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
    # Headings: remove leading #
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.MULTILINE)
    # Blockquotes: strip leading >
    s = re.sub(r"^\s*>\s?", "", s, flags=re.MULTILINE)
    # Bold/italic markers
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"__([^_]+)__", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"_([^_]+)_", r"\1", s)
    # Horizontal rules -> a dashed line
    s = re.sub(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", "──────────", s, flags=re.MULTILINE)
    # Lists: normalize leading -/* to bullets, preserve numbering
    s = re.sub(r"^(\s*)[-*]\s+", r"\1• ", s, flags=re.MULTILINE)
    # Do NOT collapse blank lines; preserve author's spacing
    return s

def _wordify_newlines(text: str) -> str:
    """Convert generic newlines to Word-friendly paragraph breaks.
    Word expects CR ("\r") for new paragraphs. We normalize any CRLF/CR/LF to CR.
    """
    if not text:
        return ''
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    t = t.replace('\n', '\r')
    return t


def get_word_selection_info(require_active: bool = True) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "ok": False,
        "selection": "",
        "has_selection": False,
        "collapsed": True,
        "hwnd": None,
        "is_active": False,
        "error": None,
    }
    if os.name != 'nt' or comtypes_client is None:
        info["error"] = "Word selection automation only available on Windows with comtypes"
        return info
    uninit = _coinit()
    app = None
    try:
        try:
            app = comtypes_client.GetActiveObject('Word.Application')  # type: ignore[arg-type]
        except Exception as exc:
            info["error"] = str(exc)
            return info
        hwnd = _get_word_hwnd(app, max_wait_ms=2000)
        info["hwnd"] = hwnd
        try:
            active_hwnd = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            active_hwnd = 0
        is_active = bool(hwnd and active_hwnd and int(active_hwnd) == int(hwnd))
        info["is_active"] = is_active
        if require_active and not is_active:
            info["error"] = "Word window is not the active foreground window"
            return info
        try:
            sel = app.Selection  # type: ignore[attr-defined]
        except Exception as exc:
            info["error"] = f"Selection unavailable: {exc}"
            return info
        try:
            start = getattr(sel, 'Start', None)
            end = getattr(sel, 'End', None)
            collapsed = (start is not None and end is not None and start == end)
        except Exception:
            collapsed = False
        try:
            text = str(getattr(sel, 'Text', '') or '')
        except Exception:
            text = ''
        selection_norm = text.replace('\r', '\n')
        has_selection = bool(selection_norm.strip()) and not collapsed
        info.update({
            "selection": selection_norm,
            "has_selection": has_selection,
            "collapsed": collapsed,
        })
        if has_selection:
            info["ok"] = True
        else:
            info["error"] = "No active selection detected in Word"
        return info
    finally:
        if uninit:
            try:
                uninit()
            except Exception:
                pass


def replace_word_selection(new_text: str) -> bool:
    if os.name != 'nt' or comtypes_client is None:
        return False
    uninit = _coinit()
    app = None
    try:
        try:
            app = comtypes_client.GetActiveObject('Word.Application')  # type: ignore[arg-type]
        except Exception:
            return False
        try:
            sel = app.Selection  # type: ignore[attr-defined]
        except Exception:
            return False
        try:
            sel.Text = _wordify_newlines(new_text or '')
            return True
        except Exception:
            return False
    finally:
        if uninit:
            try:
                uninit()
            except Exception:
                pass


def _focus_window_light(hwnd: int) -> bool:
    if not _is_window(hwnd):
        return False
    try:
        user32 = ctypes.windll.user32
        try:
            user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
        if user32.SetForegroundWindow(wintypes.HWND(hwnd)):
            return True
        try:
            fg = user32.GetForegroundWindow()
            kernel32 = ctypes.windll.kernel32
            if fg and int(fg) != int(hwnd):
                tid_fore = user32.GetWindowThreadProcessId(wintypes.HWND(fg), None)
                tid_cur = kernel32.GetCurrentThreadId()
                if tid_fore and tid_cur and user32.AttachThreadInput(tid_fore, tid_cur, True):
                    try:
                        if user32.SetForegroundWindow(wintypes.HWND(hwnd)):
                            return True
                    finally:
                        user32.AttachThreadInput(tid_fore, tid_cur, False)
        except Exception:
            pass
        try:
            user32.BringWindowToTop(wintypes.HWND(hwnd))
        except Exception:
            pass
        try:
            fg_now = user32.GetForegroundWindow()
            return bool(fg_now and int(fg_now) == int(hwnd))
        except Exception:
            return False
    except Exception:
        return False


def get_vscode_selection_info(require_active: bool = True, copy_delay: float = 0.12, preserve_layout: bool = False) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "ok": False,
        "selection": "",
        "has_selection": False,
        "hwnd": None,
        "title": "",
        "is_active": False,
        "error": None,
    }
    if os.name != 'nt':
        info["error"] = "VS Code automation is only supported on Windows"
        return info
    if win32clipboard is None or win32con is None:
        info["error"] = "System clipboard module unavailable"
        return info
    hwnd, title, is_foreground = _detect_vscode_window(require_foreground=require_active)
    if not hwnd:
        info["error"] = "Could not locate a VS Code window"
        return info
    if not _is_window(hwnd):
        info["error"] = "Detected VS Code window handle is invalid"
        return info
    info.update({
        "hwnd": hwnd,
        "title": title,
        "is_active": bool(is_foreground),
    })
    if require_active and not is_foreground:
        info["error"] = "VS Code window is not in the foreground"
        return info
    if preserve_layout:
        if not _focus_window_light(hwnd):
            info["error"] = "Unable to focus VS Code without disturbing layout"
            return info
    else:
        _force_foreground(hwnd)
        _wait_for_ready_window(hwnd, timeout_ms=800)
    had_clipboard, original_clip = _clipboard_read_text()
    _time.sleep(0.05)
    _send_ctrl_combo(VK_C)
    _time.sleep(max(0.05, copy_delay))
    copied_ok, copied_text = _clipboard_read_text()
    if had_clipboard:
        if original_clip is None:
            _clipboard_clear()
        else:
            _clipboard_set_text(original_clip)
    if not copied_ok:
        info["error"] = "Failed to read clipboard after copy"
        return info
    selection = (copied_text or '').replace('\r\n', '\n')
    has_selection = bool(selection.strip())
    info.update({
        "selection": selection,
        "has_selection": has_selection,
        "ok": has_selection,
    })
    if not has_selection:
        info["error"] = "No text selected in VS Code"
    return info


def replace_vscode_selection(new_text: str, hwnd: Optional[int] = None) -> bool:
    if os.name != 'nt':
        return False
    if win32clipboard is None or win32con is None:
        return False
    target_hwnd = hwnd
    if not target_hwnd or not _is_window(target_hwnd):
        detected, _, _ = _detect_vscode_window(require_foreground=False)
        target_hwnd = detected if detected and _is_window(detected) else None
    if not target_hwnd or not _is_window(target_hwnd):
        return False
    _force_foreground(target_hwnd)
    _wait_for_ready_window(target_hwnd, timeout_ms=800)
    had_clipboard, original_clip = _clipboard_read_text()
    normalized = (new_text or '').replace('\r\n', '\n')
    if not _clipboard_set_text(normalized):
        if had_clipboard:
            if original_clip is None:
                _clipboard_clear()
            else:
                _clipboard_set_text(original_clip)
        return False
    _time.sleep(0.05)
    _send_ctrl_combo(VK_V)
    _time.sleep(0.05)
    if had_clipboard:
        if original_clip is None:
            _clipboard_clear()
        else:
            _clipboard_set_text(original_clip)
    return True


def _preview_selection(text: str, limit: int = 180) -> str:
    if not text:
        return ''
    normalized = text.replace('\r', '\n').strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + '…'


@router.get("/inline-selection")
def inline_selection_snapshot() -> Dict[str, Any]:
    if os.name != 'nt':
        return {"available": False, "reason": "Windows-only", "selections": []}

    snapshot_ts = _time.time()
    selections: list[Dict[str, Any]] = []
    errors: list[Dict[str, str]] = []

    # Word selection (does not require window to remain in foreground)
    if comtypes_client is not None:
        try:
            word_info = get_word_selection_info(require_active=False)
        except Exception as exc:  # pragma: no cover - best-effort diagnostics
            errors.append({"source": "word", "error": str(exc)})
        else:
            if word_info:
                if word_info.get("has_selection"):
                    selection_text = (word_info.get("selection") or '').replace('\r', '\n')
                    selections.append({
                        "source": "word",
                        "label": "Microsoft Word",
                        "is_active": bool(word_info.get("is_active")),
                        "length": len(selection_text),
                        "preview": _preview_selection(selection_text),
                        "timestamp": snapshot_ts,
                    })
                elif word_info.get("error"):
                    errors.append({"source": "word", "error": str(word_info.get("error"))})
    else:
        errors.append({"source": "word", "error": "comtypes unavailable"})

    # VS Code selection (temporarily focuses window to copy selection, restore afterwards)
    if win32clipboard is not None and win32con is not None:
        original_hwnd = 0
        try:
            original_hwnd = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            original_hwnd = 0
        try:
            code_info = get_vscode_selection_info(require_active=False, copy_delay=0.08, preserve_layout=True)
        except Exception as exc:  # pragma: no cover - best-effort diagnostics
            errors.append({"source": "vscode", "error": str(exc)})
            code_info = None
        finally:
            if original_hwnd and _is_window(original_hwnd):
                _focus_window_light(original_hwnd)
        if code_info:
            if code_info.get("has_selection"):
                selection_text = (code_info.get("selection") or '').replace('\r', '\n')
                label = code_info.get("title") or "VS Code"
                selections.append({
                    "source": "vscode",
                    "label": label,
                    "is_active": bool(code_info.get("is_active")),
                    "length": len(selection_text),
                    "preview": _preview_selection(selection_text),
                    "timestamp": snapshot_ts,
                })
            elif code_info.get("error"):
                errors.append({"source": "vscode", "error": str(code_info.get("error"))})
    else:
        errors.append({"source": "vscode", "error": "clipboard automation unavailable"})

    payload: Dict[str, Any] = {
        "available": True,
        "timestamp": snapshot_ts,
        "selections": selections,
        "primary": None,
    }
    if selections:
        primary_source = next((sel.get("source") for sel in selections if sel.get("is_active")), selections[0].get("source"))
        payload["primary"] = primary_source
    if errors:
        payload["errors"] = errors
    if not selections:
        payload["message"] = "No active selections detected"
    return payload


# -------------------------- Window Management (Windows only) --------------------------

# Constants for Windows API
SW_RESTORE = 9
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOREPOSITION = 0x0200
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SW_SHOW = 5
VK_LWIN = 0x5B
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_C = 0x43
VK_V = 0x56
VK_P = 0x50
KEYEVENTF_KEYUP = 0x0002
MONITOR_DEFAULTTONEAREST = 0x00000002
GWL_EXSTYLE = -20


def _clipboard_read_text(max_retries: int = 6, delay: float = 0.05) -> tuple[bool, Optional[str]]:
    if win32clipboard is None or win32con is None:
        return False, None
    for _ in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                else:
                    data = ''
            finally:
                win32clipboard.CloseClipboard()
            return True, data
        except Exception:
            _time.sleep(delay)
    return False, None


def _clipboard_set_text(text: str, max_retries: int = 6, delay: float = 0.05) -> bool:
    if win32clipboard is None or win32con is None:
        return False
    for _ in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception:
            _time.sleep(delay)
    return False


def _clipboard_clear(max_retries: int = 6, delay: float = 0.05) -> bool:
    if win32clipboard is None:
        return False
    for _ in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception:
            _time.sleep(delay)
    return False


def _send_ctrl_combo(vk_key: int, delay: float = 0.03) -> None:
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _time.sleep(delay)
        user32.keybd_event(vk_key, 0, 0, 0)
        _time.sleep(delay)
        user32.keybd_event(vk_key, 0, KEYEVENTF_KEYUP, 0)
        _time.sleep(delay)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass

def _is_window(hwnd: int) -> bool:
    try:
        return bool(ctypes.windll.user32.IsWindow(wintypes.HWND(hwnd)))
    except Exception:
        return False

def _get_word_hwnd(app, max_wait_ms: int = 2500) -> int:
    """Try app.Hwnd repeatedly, fallback to FindWindowW('OpusApp', None)."""
    hwnd_word = 0
    import time as _t
    deadline = _time.time() + (max_wait_ms / 1000.0)
    while _time.time() < deadline:
        try:
            hwnd_word = int(getattr(app, 'Hwnd', 0))
        except Exception:
            hwnd_word = 0
        if hwnd_word and _is_window(hwnd_word):
            break
        _t.sleep(0.05)
    if not hwnd_word:
        try:
            # Typical Word top-level class name is 'OpusApp'
            hwnd_word = int(ctypes.windll.user32.FindWindowW('OpusApp', None))
        except Exception:
            hwnd_word = 0
    try:
        print(f"WORD_HWND: resolved hwnd_word={int(hwnd_word)}")
    except Exception:
        pass
    return hwnd_word

def _is_window_visible_and_normal(hwnd: int) -> bool:
    try:
        user32 = ctypes.windll.user32
        if not user32.IsWindowVisible(wintypes.HWND(hwnd)):
            return False
        if user32.IsIconic(wintypes.HWND(hwnd)):
            return False
        return True
    except Exception:
        return False


_BROWSER_CLASS_HINTS = {
    'Chrome_WidgetWin_0',
    'Chrome_WidgetWin_1',
    'MozillaWindowClass',
    'OperaWindowClass',
    'ApplicationFrameWindow',  # Edge (Win32 host)
    'Windows.UI.Core.CoreWindow',  # Edge (UWP)
    'Qt5QWindowIcon',  # Brave/Vivaldi variants
}

_BROWSER_TITLE_TOKENS = (
    'chrome',
    'edge',
    'firefox',
    'brave',
    'vivaldi',
    'opera',
    'safari',
    'browser',
)


def _get_window_class(hwnd: int) -> str:
    try:
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(wintypes.HWND(hwnd), buf, 256)
        return buf.value or ''
    except Exception:
        return ''


def _is_browser_window(hwnd: Optional[int]) -> bool:
    try:
        if not hwnd or not _is_window(hwnd):
            return False
        class_name = _get_window_class(hwnd)
        if class_name:
            if class_name in _BROWSER_CLASS_HINTS:
                return True
            prefix = class_name.split('#', 1)[0]
            if prefix in _BROWSER_CLASS_HINTS:
                return True
            if class_name.startswith('Chrome_WidgetWin_'):
                return True
        title_low = (_get_window_title(hwnd) or '').lower()
        if title_low and any(tok in title_low for tok in _BROWSER_TITLE_TOKENS):
            return True
    except Exception:
        pass
    return False

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]

def _get_work_area_for_window(hwnd: int) -> tuple[int, int, int, int]:
    user32 = ctypes.windll.user32
    try:
        monitor = user32.MonitorFromWindow(wintypes.HWND(hwnd), MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(wintypes.HMONITOR(monitor), ctypes.byref(mi)):
            return (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
    except Exception:
        pass
    # Fallback to primary screen
    cx = user32.GetSystemMetrics(0)
    cy = user32.GetSystemMetrics(1)
    return (0, 0, cx, cy)

def _move_window(hwnd: int, x: int, y: int, w: int, h: int):
    user32 = ctypes.windll.user32
    try:
        user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)
    except Exception:
        pass
    # Move/resize and allow activation
    user32.SetWindowPos(wintypes.HWND(hwnd), None, x, y, w, h, SWP_NOZORDER)

def _wait_for_ready_window(hwnd: int, timeout_ms: int = 1500, min_size: int = 150) -> bool:
    """Wait until window is visible, restored (not iconic), and has at least min_size width/height."""
    try:
        user32 = ctypes.windll.user32
        end = _time.time() + (timeout_ms / 1000.0)
        while _time.time() < end:
            if not _is_window(hwnd):
                return False
            if not user32.IsWindowVisible(wintypes.HWND(hwnd)):
                _time.sleep(0.05); continue
            if user32.IsIconic(wintypes.HWND(hwnd)):
                user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)
                _time.sleep(0.05); continue
            rect = RECT()
            if user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
                w = max(0, rect.right - rect.left)
                h = max(0, rect.bottom - rect.top)
                if w >= min_size and h >= min_size:
                    return True
            _time.sleep(0.05)
        return False
    except Exception:
        return False

def _force_foreground(hwnd: int) -> bool:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        # Restore and show
        user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)
        # Allow this process to set foreground
        try:
            user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
        # Try SetForegroundWindow directly
        if user32.SetForegroundWindow(wintypes.HWND(hwnd)):
            return True
        # Attach to foreground thread and retry
        try:
            fg = user32.GetForegroundWindow()
            tid_fore = user32.GetWindowThreadProcessId(wintypes.HWND(fg), None)
            tid_cur = kernel32.GetCurrentThreadId()
            if tid_fore and tid_cur and user32.AttachThreadInput(tid_fore, tid_cur, True):
                try:
                    if user32.SetForegroundWindow(wintypes.HWND(hwnd)):
                        return True
                finally:
                    user32.AttachThreadInput(tid_fore, tid_cur, False)
        except Exception:
            pass
        # Topmost toggle trick
        try:
            user32.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
            user32.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(HWND_NOTOPMOST), 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
        except Exception:
            pass
        # BringWindowToTop as last resort
        try:
            user32.BringWindowToTop(wintypes.HWND(hwnd))
        except Exception:
            pass
        return True
    except Exception:
        return False

def _send_win_arrow(side: str = 'right') -> bool:
    try:
        user32 = ctypes.windll.user32
        arrow = VK_RIGHT if str(side).lower() != 'left' else VK_LEFT
        # Press Win down
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        _time.sleep(0.02)
        # Press Arrow down
        user32.keybd_event(arrow, 0, 0, 0)
        _time.sleep(0.02)
        # Release Arrow
        user32.keybd_event(arrow, 0, KEYEVENTF_KEYUP, 0)
        _time.sleep(0.02)
        # Release Win
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False

def _press_key(vk_code: int, repeats: int = 1, delay: float = 0.02) -> None:
    """Press and release a virtual key a number of times."""
    try:
        user32 = ctypes.windll.user32
        for _ in range(max(1, int(repeats))):
            user32.keybd_event(vk_code, 0, 0, 0)
            _time.sleep(delay)
            user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            _time.sleep(delay)
    except Exception:
        pass

def _count_visible_windows(exclude_hwnds: list[int] | None = None) -> int:
    """Approximate count of candidate windows Snap Assist might show: visible, not minimized, exclude Word and listed hwnds."""
    try:
        exclude = set([h for h in (exclude_hwnds or []) if h])
        user32 = ctypes.windll.user32
        count = 0
        for hwnd in _enum_windows_collect():
            if hwnd in exclude:
                continue
            if not _is_window_visible_and_normal(hwnd):
                continue
            # Skip Word windows (class 'OpusApp')
            try:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(wintypes.HWND(hwnd), buf, 256)
                if 'OpusApp' in (buf.value or ''):
                    continue
            except Exception:
                pass
            count += 1
        return count
    except Exception:
        return 0

def _uia_select_snap_word(name_tokens: list[str], max_steps: int = 16, delay: float = 0.08) -> bool:
    """Use UI Automation to navigate Snap Assist tiles and select the one matching Word/doc title.
    Returns True if Enter was sent on a matching tile; False if UIA failed or not found in steps.
    """
    try:
        # Prepare UIA client
        try:
            from comtypes.client import GetModule, CreateObject  # type: ignore
            GetModule('UIAutomationCore.dll')
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
            automation = CreateObject(UIA.CUIAutomation)
        except Exception:
            return False
    except Exception as e:
        print(f"UIA_ERROR: {e}")
        return False
            
def _uia_select_snap_vscode(name_tokens: list[str], max_steps: int = 16, delay: float = 0.08) -> bool:
    """Use UI Automation to navigate Snap Assist tiles and select the one matching VS Code window title.
    Returns True if Enter was sent on a matching tile; False if UIA failed or not found in steps.
    """
    import time
    try:
        # Prepare UIA client
        try:
            from comtypes.client import GetModule, CreateObject  # type: ignore
            GetModule('UIAutomationCore.dll')
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
            automation = CreateObject(UIA.CUIAutomation)
        except Exception:
            return False
            
        tokens = [t.lower() for t in (name_tokens or []) if isinstance(t, str) and t.strip()]
        if not tokens:
            tokens = ['code', 'vscode']
        last_name = None
        stagnate = 0
        for i in range(max_steps):
            try:
                elem = automation.GetFocusedElement()
            except Exception:
                elem = None
            cur_name = ''
            try:
                if elem is not None:
                    cur_name = (elem.CurrentName or '')
            except Exception:
                cur_name = ''
            cur_name_l = cur_name.lower()
            if any(tok in cur_name_l for tok in tokens):
                _press_key(VK_RETURN, repeats=1, delay=0.03)
                return True
            # Move selection through grid: try Right, if stagnant for a few steps, try Down
            _press_key(VK_RIGHT, repeats=1, delay=0.03)
            if cur_name == last_name:
                stagnate += 1
                if stagnate >= 3:
                    _press_key(VK_DOWN, repeats=1, delay=0.03)
                    stagnate = 0
            else:
                stagnate = 0
            last_name = cur_name
            time.sleep(delay)
        return False
    except Exception as e:
        print(f"UIA_ERROR: {e}")
        return False
        return False
    except Exception:
        return False

def _cua_select_snap_word(name_tokens: list[str]) -> bool:
    """Delegate Snap Assist tile selection to CUA adapter if available."""
    try:
        try:
            import backend.cua_adapter as cua_adapter  # type: ignore
        except Exception:
            try:
                import cua_adapter  # type: ignore
            except Exception:
                cua_adapter = None  # type: ignore
        if hasattr(cua_adapter, 'select_snap_assist_tile'):
            return bool(cua_adapter.select_snap_assist_tile(name_tokens))
    except Exception:
        pass
    return False
    
def _cua_select_snap_vscode(name_tokens: list[str]) -> bool:
    """Delegate Snap Assist tile selection for VS Code to CUA adapter if available."""
    try:
        try:
            import backend.cua_adapter as cua_adapter  # type: ignore
        except Exception:
            try:
                import cua_adapter  # type: ignore
            except Exception:
                cua_adapter = None  # type: ignore
        if hasattr(cua_adapter, 'select_snap_assist_tile'):
            return bool(cua_adapter.select_snap_assist_tile(name_tokens))
    except Exception:
        pass
    return False


def _iter_top_level_windows() -> list[int]:
    """Return top-level window handles in Z-order (foreground first)."""
    try:
        user32 = ctypes.windll.user32
        GW_HWNDNEXT = 2
        seen = set()
        hwnd = user32.GetTopWindow(None)
        handles: list[int] = []
        while hwnd and hwnd not in seen:
            handles.append(int(hwnd))
            seen.add(int(hwnd))
            hwnd = user32.GetWindow(hwnd, GW_HWNDNEXT)
        return handles
    except Exception:
        return []


def _get_window_title(hwnd: int) -> str:
    try:
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ''
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ''
    except Exception:
        return ''


def _title_is_vscode(title: str) -> bool:
    if not title:
        return False
    low = title.lower()
    if 'visual studio code' in low:
        return True
    if 'vs code' in low:
        return True
    if low.endswith(' - code') or low.startswith('code - '):
        return True
    return False


def _is_vscode_window(hwnd: Optional[int]) -> bool:
    try:
        if not hwnd or not _is_window(hwnd):
            return False
        title = _get_window_title(int(hwnd))
        return _title_is_vscode(title)
    except Exception:
        return False


def _detect_vscode_window(require_foreground: bool = True) -> tuple[Optional[int], str, bool]:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
    except Exception:
        hwnd = 0
    title = _get_window_title(hwnd) if hwnd else ''
    if hwnd and _title_is_vscode(title):
        return int(hwnd), title, True
    if require_foreground:
        return None, title, False
    # Fall back to enumerating visible windows
    for candidate in _iter_top_level_windows():
        title_cand = _get_window_title(candidate)
        if _title_is_vscode(title_cand):
            return candidate, title_cand, False
    return None, '', False


def _score_vscode_window(title_low: str, file_basename_low: str) -> int:
    score = 0
    if 'visual studio code' in title_low:
        score += 40
    if 'vs code' in title_low:
        score += 15
    if 'code' in title_low:
        score += 5
    if file_basename_low:
        if file_basename_low in title_low:
            score += 200
            if title_low.startswith(file_basename_low):
                score += 60
            if f"{file_basename_low} - " in title_low:
                score += 40
        stem = file_basename_low.rsplit('.', 1)[0] if '.' in file_basename_low else file_basename_low
        if stem and stem in title_low:
            score += 120
    return score


def _list_vscode_windows() -> list[tuple[int, str]]:
    """Return (hwnd,title) for visible VS Code top-level windows."""
    out: list[tuple[int, str]] = []
    try:
        user32 = ctypes.windll.user32
        for hwnd in _iter_top_level_windows():
            if not user32.IsWindow(hwnd):
                continue
            if not user32.IsWindowVisible(hwnd):
                continue
            title = _get_window_title(hwnd)
            if not title:
                continue
            low = title.lower()
            if ('visual studio code' in low) or ('vs code' in low) or low.endswith(' - visual studio'):
                out.append((hwnd, title))
    except Exception:
        return []
    return out


def _pick_best_vscode_window(file_basename: str, max_attempts: int = 8, sleep_seconds: float = 0.4, before_handles: Optional[set[int]] = None) -> tuple[Optional[int], list[tuple[int, str]]]:
    """Locate the VS Code window most likely associated with file_basename.

    Improvements:
    - If a new VS Code window appeared since before_handles, strongly prefer it.
    - Retain scoring by filename tokens.
    """
    try:
        user32 = ctypes.windll.user32
        file_base_low = (file_basename or '').lower()
        snapshots: list[tuple[int, str]] = []
        before_handles = before_handles or set()
        for attempt in range(max_attempts):
            candidates: list[tuple[int, int, str]] = []  # (score, hwnd, title)
            foreground = user32.GetForegroundWindow()
            for hwnd in _iter_top_level_windows():
                if not user32.IsWindow(hwnd):
                    continue
                if not user32.IsWindowVisible(hwnd):
                    continue
                title = _get_window_title(hwnd)
                title_low = title.lower()
                if not title_low:
                    continue
                if ('visual studio code' not in title_low and 'vs code' not in title_low and
                        not (file_base_low and 'code' in title_low and file_base_low in title_low)):
                    continue
                score = _score_vscode_window(title_low, file_base_low)
                if hwnd == foreground:
                    score += 30  # Foreground preference
                if hwnd not in before_handles:
                    score += 500  # Strong boost for newly created window
                candidates.append((score, hwnd, title))
            if candidates:
                candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
                snapshots = [(hwnd, title) for _, hwnd, title in candidates]
                best_score, best_hwnd, best_title = candidates[0]
                # Early exit if very confident (>300) or filename present
                if best_score >= 300 or (file_base_low and file_base_low in best_title.lower()):
                    return best_hwnd, snapshots
                if attempt >= max_attempts - 2:
                    return best_hwnd, snapshots
            _time.sleep(sleep_seconds)
        return None, snapshots
    except Exception:
        return None, []


def _ensure_vscode_tab_for_path(hwnd: int, abs_path: str, wait_after_open: float = 0.18) -> bool:
    """Use VS Code's Quick Open to focus the tab that matches the requested absolute path."""
    if os.name != 'nt' or not abs_path:
        return False
    if not hwnd or not _is_window(hwnd):
        return False
    if win32clipboard is None or win32con is None:
        return False
    file_path = os.path.abspath(abs_path)
    # Allow VS Code to create new files that do not yet exist
    clip_payload = file_path if os.path.exists(file_path) else abs_path
    had_clipboard, original_clip = _clipboard_read_text()
    wrote_clipboard = False
    try:
        if not _clipboard_set_text(clip_payload):
            return False
        wrote_clipboard = True
        if not _focus_window_light(hwnd):
            _force_foreground(hwnd)
        _wait_for_ready_window(hwnd, timeout_ms=900)
        _send_ctrl_combo(VK_P)
        _time.sleep(0.12)
        _send_ctrl_combo(VK_V)
        _time.sleep(0.12)
        _press_key(VK_RETURN, repeats=1, delay=0.05)
        _time.sleep(wait_after_open)
        return True
    finally:
        if wrote_clipboard:
            if had_clipboard:
                if original_clip is None:
                    _clipboard_clear()
                else:
                    _clipboard_set_text(original_clip)
            else:
                _clipboard_clear()

def _arrange_side_by_side(hwnd_a: int, hwnd_b: int, b_on_right: bool = True) -> bool:
    try:
        l, t, r, b = _get_work_area_for_window(hwnd_a)
        width = max(200, r - l)
        height = max(200, b - t)
        half = width // 2
        # Left rect
        left_rect = (l, t, half, height)
        # Right rect
        right_rect = (l + half, t, width - half, height)
        if b_on_right:
            _move_window(hwnd_a, *left_rect)
            _move_window(hwnd_b, *right_rect)
        else:
            _move_window(hwnd_b, *left_rect)
            _move_window(hwnd_a, *right_rect)
        return True
    except Exception:
        return False

def _snap_single_window(hwnd: int, side: str = 'right') -> bool:
    try:
        l, t, r, b = _get_work_area_for_window(hwnd)
        width = max(200, r - l)
        height = max(200, b - t)
        half = width // 2
        if str(side).lower() == 'left':
            rect = (l, t, half, height)
        else:
            rect = (l + half, t, width - half, height)
        _move_window(hwnd, *rect)
        return True
    except Exception:
        return False

def _enum_windows_collect() -> list[int]:
    user32 = ctypes.windll.user32
    res: list[int] = []
    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, lparam):
        try:
            res.append(int(hwnd))
        except Exception:
            pass
        return True
    user32.EnumWindows(CMPFUNC(_cb), 0)
    return res

def _is_snapped_to_side(hwnd: int, side: str = 'right', tol: int = 60) -> bool:
    """Heuristically check if hwnd occupies the left or right half of its monitor work area."""
    try:
        if not _is_window(hwnd):
            return False
        l, t, r, b = _get_work_area_for_window(hwnd)
        width = max(1, r - l)
        height = max(1, b - t)
        rect = RECT()
        if not ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
            return False
        wl, wt, wr, wb = rect.left, rect.top, rect.right, rect.bottom
        half = width // 2
        if str(side).lower() == 'left':
            return abs(wl - l) <= tol and abs(wr - (l + half)) <= tol and abs(wt - t) <= tol and abs(wb - b) <= tol
        else:
            return abs(wl - (l + half)) <= tol and abs(wr - r) <= tol and abs(wt - t) <= tol and abs(wb - b) <= tol
    except Exception:
        return False


def _check_split_state_active(state: Dict[str, Any]) -> bool:
    """Best-effort validation that the stored split layout is still in effect."""
    try:
        if not state:
            return False
        primary = state.get('primary_hwnd')
        if not primary or not _is_window(primary):
            return False
        if not _is_window_visible_and_normal(primary):
            return False
        side = state.get('side') or 'right'
        side_str = str(side).lower() if side else 'right'
        if not _is_snapped_to_side(primary, side=side_str):
            return False
        partner = state.get('partner_hwnd')
        if partner and _is_window(partner):
            opposite = 'left' if side_str == 'right' else 'right'
            if not _is_snapped_to_side(partner, side=opposite):
                return False
        return True
    except Exception:
        return False

def _find_alternate_window(
    exclude_hwnds: list[int],
    prefer_monitor_of: Optional[int] = None,
    *,
    prefer_browser: bool = False,
    browser_only: bool = False,
    allowed_types: Optional[set[str]] = None,
) -> Optional[int]:
    try:
        all_hwnds = _enum_windows_collect()
        exclude = set([h for h in (exclude_hwnds or []) if h])
        user32 = ctypes.windll.user32

        # Deterministic hard rule: if a single browser window contains the project token 'SarvajñaGPT' (accent-insensitive), pick it immediately.
        # Collect browser windows first for this check.
        try:
            import unicodedata as _ud
            def _strip_diacritics(s: str) -> str:
                return ''.join(c for c in _ud.normalize('NFD', s) if not _ud.combining(c))
            target_tokens = { 'sarvajñagpt', 'sarvajnagpt', 'sarvajna gpt' }
            matching_browser_hwnds: list[tuple[int,int]] = []  # (hwnd, area)
            for _hw in list(all_hwnds):
                if _hw in exclude:
                    continue
                if not _is_window_visible_and_normal(_hw):
                    continue
                # Get title first (even if _is_browser_window fails) so we can fallback by title heuristics
                try:
                    buf_t = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(wintypes.HWND(_hw), buf_t, 512)
                    title_raw = (buf_t.value or '').strip()
                except Exception:
                    title_raw = ''
                norm_title = _strip_diacritics(title_raw).lower()
                is_browser_flag = _is_browser_window(_hw)
                # Fallback: treat as browser if title indicates Chrome even when detection missed
                if (not is_browser_flag) and ('chrome' in norm_title and ' - ' in title_raw):
                    try:
                        print(f"ALT_PICK_FALLBACK_BROWSER_DETECT: hwnd={_hw} title='{title_raw}'")
                    except Exception:
                        pass
                    is_browser_flag = True
                if not is_browser_flag:
                    continue
                if any(tok in norm_title for tok in target_tokens):
                    # compute area for tie-breaker
                    try:
                        rect = RECT()
                        area = 0
                        if user32.GetWindowRect(wintypes.HWND(_hw), ctypes.byref(rect)):
                            area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                    except Exception:
                        area = 0
                    matching_browser_hwnds.append((_hw, area))
            if matching_browser_hwnds:
                # Choose largest area (likely main active tab) deterministically
                matching_browser_hwnds.sort(key=lambda x: x[1], reverse=True)
                chosen = matching_browser_hwnds[0][0]
                try:
                    print(f"ALT_PICK_HARD_MATCH: Selected SarvajñaGPT browser hwnd={chosen}")
                except Exception:
                    pass
                return chosen
        except Exception:
            pass

        best = None
        best_area = -1
        best_browser = None  # hwnd with highest adjusted score among browsers
        best_browser_score = -1
        # Compute target monitor work area to prioritize same screen
        target_rect = None
        if prefer_monitor_of and _is_window(prefer_monitor_of):
            l, t, r, b = _get_work_area_for_window(prefer_monitor_of)
            target_rect = (l, t, r, b)

        # Heuristic title token preferences / penalties
        prefer_tokens_env = os.environ.get('POWER_BROWSER_PRIORITY_TOKENS', '')
        prefer_tokens = [t.strip().lower() for t in prefer_tokens_env.split(',') if t.strip()] or []
        # Always include some generic dev tokens if not explicitly provided
        if not prefer_tokens:
            prefer_tokens = ['sarvajña', 'sarvajna', 'localhost', 'index', 'vite', 'dev', 'docs']
        penalty_patterns = [
            r"\.mkv", r"\.mp4", r"\.avi", r"1080p", r"720p", r"movies?", r"s\d{2}e\d{2}",
            r"\.webm", r"download", r"torrent", r"subs?", r"episode"
        ]
        penalty_regex = [re.compile(p, re.I) for p in penalty_patterns]
        debug_scores = os.environ.get('POWER_DEBUG_ALT_PICK', '0').lower() in ('1','true','yes')
        for hwnd in all_hwnds:
            if hwnd in exclude:
                continue
            if not _is_window_visible_and_normal(hwnd):
                continue
            is_vscode = _is_vscode_window(hwnd)
            is_browser = _is_browser_window(hwnd)
            # Word detection by class
            is_word = False
            try:
                buf_cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(wintypes.HWND(hwnd), buf_cls, 256)
                cls = buf_cls.value or ''
                if 'OpusApp' in cls:
                    is_word = True
            except Exception:
                pass

            if allowed_types is not None:
                # Map booleans to type strings
                type_name = None
                if is_browser:
                    type_name = 'browser'
                elif is_vscode:
                    type_name = 'vscode'
                elif is_word:
                    type_name = 'word'
                else:
                    type_name = 'other'
                if type_name not in allowed_types:
                    continue

            if is_vscode and (allowed_types is None):
                # Original behavior: skip VS Code windows unless explicitly allowed via allowed_types
                continue
            if browser_only and not is_browser:
                continue
            # Skip Word windows (class is typically 'OpusApp')
            if not allowed_types and is_word:
                continue
            # Compute area overlap with target monitor (prefer same monitor)
            try:
                rect = RECT()
                if user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
                    area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                    score = area  # base
                    title = ''
                    try:
                        buf_t = ctypes.create_unicode_buffer(512)
                        user32.GetWindowTextW(wintypes.HWND(hwnd), buf_t, 512)
                        title = (buf_t.value or '').strip()
                    except Exception:
                        title = ''
                    title_low = title.lower()
                    token_hits = 0
                    penalties = 0
                    if is_browser:
                        for tok in prefer_tokens:
                            if tok and tok in title_low:
                                token_hits += 1
                        if token_hits:
                            score += 400_000 * min(token_hits, 4)  # cap to avoid runaway
                        for rgx in penalty_regex:
                            if rgx.search(title):
                                penalties += 1
                        if penalties:
                            score -= 350_000 * min(penalties, 3)
                        # Long noisy media-like titles get a small extra penalty when no hits
                        if len(title) > 100 and token_hits == 0:
                            score -= 150_000
                        if prefer_browser:
                            score += 2_000_000
                        # Track best browser by adjusted score
                        if score > best_browser_score:
                            best_browser_score = score
                            best_browser = hwnd
                    if target_rect:
                        l, t, r, b = target_rect
                        # add small bias if hwnd is on same monitor (rough check by center point)
                        cx = (rect.left + rect.right) // 2
                        cy = (rect.top + rect.bottom) // 2
                        if (cx >= l and cx <= r and cy >= t and cy <= b):
                            score += 1_000_000
                    if debug_scores and is_browser:
                        try:
                            print(f"ALT_BROWSER_SCORE hwnd={hwnd} score={score} area={area} hits={token_hits} penalties={penalties} title='{title}'")
                        except Exception:
                            pass
                    if score > best_area:
                        best_area = score
                        best = hwnd
            except Exception:
                continue
        # If we found ANY browser and the current best is a VS Code window, override with browser to avoid two VS Codes.
        try:
            if best and _is_vscode_window(best) and best_browser:
                print(f"ALT_PICK_ADJUST: Replacing VS Code partner hwnd={best} with browser hwnd={best_browser}")
                return best_browser
        except Exception:
            pass
        # Choose highest scored browser if we prefer browsers or if best is VS Code / None
        if best_browser and (best is None or _is_vscode_window(best)):
            return best_browser
        # If both are browsers, pick the one with higher adjusted score (best_browser_score already reflects that)
        if best and best_browser and _is_browser_window(best) and best_browser != best:
            # Compare base best_area (which used unified scoring) vs best_browser_score
            if best_browser_score >= best_area:
                return best_browser
        return best
    except Exception:
        return None


@router.get("/word/available")
def word_available() -> dict:
    ok = False
    reason = None
    if os.name != 'nt':
        reason = "Windows-only"
    else:
        try:
            # quick COM probe
            if comtypes_client is not None:
                ok = True
            else:
                reason = "comtypes not available"
        except Exception as e:
            reason = str(e)
    return {"available": ok, "reason": reason}


@router.post("/word/preview")
def word_preview(req: WordTypeRequest) -> dict:
    out = {"summary": f"Open Word, insert {len(req.text)} chars"}
    if req.save_target:
        if not str(req.save_target).lower().endswith('.docx'):
            raise HTTPException(status_code=400, detail="save_target must end with .docx")
        out["save_target"] = req.save_target
        out["save_abs"] = _resolve_under_base(req.save_target)
    return out


def _word_execute_impl(req: WordTypeRequest) -> dict:
    if os.name != 'nt':
        raise HTTPException(status_code=400, detail="Word COM automation is Windows-only")
    if comtypes_client is None:
        raise HTTPException(status_code=500, detail="comtypes is not installed; add it to backend/requirements.txt and pip install")
    uninit = None
    try:
        # Ensure COM initialized in STA (best-effort)
        uninit = _coinit()
        # Capture current foreground window before bringing Word to front
        hwnd_fore = None
        try:
            hwnd_fore = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            hwnd_fore = None
        requested_word_side = str(getattr(req, 'word_side', 'right') or 'right').lower()
        if requested_word_side not in ('left', 'right'):
            requested_word_side = 'right'
        word_side_effective = requested_word_side
        # Reuse existing Word if already running to reduce startup delay
        app = None
        try:
            app = comtypes_client.GetActiveObject('Word.Application')
        except Exception:
            app = comtypes_client.CreateObject('Word.Application')
        # Reduce pop-ups and make visible if requested
        app.Visible = bool(req.show_window)
        try:
            app.DisplayAlerts = 0  # wdAlertsNone
        except Exception:
            pass
        try:
            app.Activate()
        except Exception:
            pass
        # Ensure normal window state if visible (0 = wdWindowStateNormal)
        try:
            if bool(req.show_window):
                app.WindowState = 0
        except Exception:
            pass
        # Determine save path and whether to open existing
        target_abs = None
        open_existing = False
        if req.save_target:
            target = req.save_target
            if not str(target).lower().endswith('.docx'):
                target = f"{target}.docx"
            if os.path.isabs(target):
                target_abs = target
            else:
                target_abs = _resolve_under_base(target)
            try:
                os.makedirs(os.path.dirname(target_abs), exist_ok=True)
            except Exception:
                pass
            open_existing = os.path.isfile(target_abs)

        # Open document: existing or new
        if open_existing:
            doc = app.Documents.Open(target_abs)
        else:
            doc = app.Documents.Add()

        # Insert or append text
        try:
            _plain = _wordify_newlines(_clean_markdown_to_text(req.text))
            if open_existing and bool(getattr(req, 'append', True)):
                # Append two newlines then text
                try:
                    doc.Content.InsertAfter("\r\r" + _plain)
                except Exception:
                    sel = app.Selection
                    sel.EndKey(Unit=6)  # wdStory
                    sel.TypeParagraph()
                    sel.TypeParagraph()
                    sel.TypeText(_plain)
            else:
                # Replace content
                doc.Content.Text = _plain
        except Exception:
            sel = app.Selection
            if open_existing and bool(getattr(req, 'append', True)):
                sel.EndKey(Unit=6)
                sel.TypeParagraph(); sel.TypeParagraph()
            sel.TypeText(_wordify_newlines(_clean_markdown_to_text(req.text)))

        saved_path = None
        desktop_info = {"desktop_copied": False, "desktop_path": None, "opened": False}
        if target_abs:
            # Save existing or new to target_abs
            try:
                if open_existing:
                    doc.Save()
                else:
                    wdFormatDocumentDefault = 16
                    doc.SaveAs(target_abs, FileFormat=wdFormatDocumentDefault)
                saved_path = target_abs
            except Exception:
                # Best-effort alternative save
                try:
                    doc.Save()
                    saved_path = target_abs
                except Exception:
                    saved_path = target_abs
            # Best-effort copy to Desktop and open default app
            try:
                home = os.path.expanduser('~')
                desktop_dir = None
                if os.name == 'nt':
                    userprofile = os.environ.get('USERPROFILE') or home
                    candidate = os.path.join(userprofile, 'Desktop')
                    if os.path.isdir(candidate):
                        desktop_dir = candidate
                if desktop_dir is None:
                    candidate2 = os.path.join(home, 'Desktop')
                    if os.path.isdir(candidate2):
                        desktop_dir = candidate2
                if desktop_dir:
                    dest_path = os.path.join(desktop_dir, os.path.basename(saved_path))
                    try:
                        import shutil as _sh
                        _sh.copy2(saved_path, dest_path)
                        desktop_info["desktop_copied"] = True
                        desktop_info["desktop_path"] = dest_path
                        # Force-open to foreground
                        try:
                            if os.name == 'nt':
                                os.startfile(dest_path)  # type: ignore[attr-defined]
                                desktop_info["opened"] = True
                            else:
                                import subprocess as _sub
                                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                                _sub.Popen([opener, dest_path])
                                desktop_info["opened"] = True
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
        # If saved and visible requested, best-effort bring to front again and arrange side-by-side
        split_applied = False
        cua_attempted = False
        cua_selected = False
        flow_label = "none"
        try:
            if bool(req.show_window):
                app.Activate()
                # Resolve Word window handle robustly
                hwnd_word = _get_word_hwnd(app, max_wait_ms=2500)
                # Optional delay to let rendering settle
                if getattr(req, 'arrangement_delay_ms', 0) and req.arrangement_delay_ms > 0:
                    _time.sleep(min(5.0, req.arrangement_delay_ms / 1000.0))
                # Ensure Word window is ready (visible/restored/sized)
                _wait_for_ready_window(hwnd_word, timeout_ms=1500)
                # Arrange split screen with previously active window or alternate
                pre_already_split = False
                if bool(getattr(req, 'avoid_rearrange_if_already_split', True)) and _is_snapped_to_side(hwnd_word, side=word_side_effective):
                    pre_already_split = True
                    split_applied = True
                    flow_label = "already_split"
                if bool(req.split_screen) and os.name == 'nt' and hwnd_word and not pre_already_split:
                    try:
                        print(f"SPLIT_PRECHECK: show={bool(req.show_window)} split={bool(req.split_screen)} hwnd_word={int(hwnd_word)}")
                    except Exception:
                        pass
                    try:
                        print(f"SPLIT_FLAGS: split={req.split_screen} side={word_side_effective} os_keys={getattr(req,'use_os_snap_keys',True)} cua={getattr(req,'use_cua_for_selection',False)}")
                    except Exception:
                        pass
                    # Only treat a foreground browser as a valid partner; never VS Code when Word is opening
                    valid_pair = (
                        hwnd_fore and _is_window(hwnd_fore) and (hwnd_fore != hwnd_word) and _is_window_visible_and_normal(hwnd_fore)
                        and _is_browser_window(hwnd_fore)
                    )
                    target_hwnd = None
                    if valid_pair and _is_browser_window(hwnd_fore):
                        # Immediate use if it's a browser (highest priority partner)
                        target_hwnd = hwnd_fore
                    if target_hwnd is None:
                        # Only search for browsers; if none, we'll snap Word alone
                        target_hwnd = _find_alternate_window(
                            [hwnd_word],
                            prefer_monitor_of=hwnd_word,
                            prefer_browser=True,
                            browser_only=True,
                            allowed_types={'browser'}
                        )
                    try:
                        print(f"SPLIT_WINDOWS: hwnd_fore={int(hwnd_fore) if hwnd_fore else 0} hwnd_word={int(hwnd_word)} target={int(target_hwnd) if target_hwnd else 0}")
                    except Exception:
                        pass
                    if target_hwnd:
                        if _is_browser_window(target_hwnd) and word_side_effective != 'left':
                            try:
                                print("SPLIT_ADJUST: keeping browser on right; forcing Word to left")
                            except Exception:
                                pass
                            word_side_effective = 'left'
                        opposite_side = 'left' if word_side_effective == 'right' else 'right'
                        _wait_for_ready_window(target_hwnd, timeout_ms=1000)
                        if getattr(req, 'use_os_snap_keys', True):
                            try:
                                print("SPLIT_FLOW: using OS snap keys for both windows")
                            except Exception:
                                pass
                            # OS snap flow with Snap Assist navigation to select Word automatically
                            _force_foreground(target_hwnd)
                            _send_win_arrow(side=opposite_side)
                            _time.sleep(0.25)
                            flow_label = "os_snap"
                            # Try CUA-backed selection first (if enabled), then UIA fallback to select Word/doc tile
                            doc_name_tokens = []
                            try:
                                # Attempt to read document name via COM properties
                                name = ''
                                try:
                                    name = str(getattr(app.ActiveDocument, 'Name', '') or '')
                                except Exception:
                                    name = ''
                                if name:
                                    base = os.path.splitext(name)[0]
                                    doc_name_tokens = [base, 'microsoft word', 'word']
                            except Exception:
                                doc_name_tokens = ['microsoft word', 'word']
                            selected = False
                            _force_cua = False
                            try:
                                try:
                                    import backend.cua_adapter as cua_adapter  # type: ignore
                                except Exception:
                                    try:
                                        import cua_adapter  # type: ignore
                                    except Exception:
                                        cua_adapter = None  # type: ignore
                                if hasattr(cua_adapter, 'cua_runtime_status') and cua_adapter.cua_runtime_status().get('agent_ready'):
                                    _force_cua = True
                            except Exception:
                                _force_cua = False
                            if _force_cua or getattr(req, 'use_cua_for_selection', False):
                                cua_attempted = True
                                try:
                                    print(f"CUA_SELECT: attempting with tokens={doc_name_tokens}")
                                    selected = _cua_select_snap_word(doc_name_tokens)
                                    cua_selected = bool(selected)
                                    print(f"CUA_SELECT: result selected={selected}")
                                except Exception as _e:
                                    print(f"CUA_SELECT: exception: {_e}")
                                    selected = False
                            if (not selected) and (not _uia_select_snap_word(doc_name_tokens, max_steps=20)):
                                # Fallback to position-based strategy
                                candidates = _count_visible_windows(exclude_hwnds=[target_hwnd, hwnd_word])
                                if candidates > 0:
                                    _press_key(VK_DOWN, repeats=candidates, delay=0.03)
                                    _press_key(VK_RETURN, repeats=1, delay=0.03)
                                else:
                                    _force_foreground(hwnd_word)
                                    _send_win_arrow(side=word_side_effective)
                            split_applied = True
                        else:
                            split_applied = _arrange_side_by_side(target_hwnd, hwnd_word, b_on_right=(word_side_effective != 'left'))
                            if split_applied:
                                flow_label = "manual_arrange"
                    elif bool(req.fallback_snap):
                        try:
                            print("SPLIT_FLOW: no target window; snapping Word only")
                        except Exception:
                            pass
                        split_applied = _snap_single_window(hwnd_word, side=word_side_effective)
                        flow_label = "single_snap"
                # Ensure Word is visible in foreground
                _force_foreground(hwnd_word)
                # As a last resort, use OS snap via Win+Arrow to surface Word
                if not split_applied and bool(req.fallback_snap):
                    # Try with current foreground via OS snap if enabled
                    try:
                        cur_fg = ctypes.windll.user32.GetForegroundWindow()
                    except Exception:
                        cur_fg = None
                    if cur_fg and _is_window(cur_fg) and cur_fg != hwnd_word and getattr(req, 'use_os_snap_keys', True):
                        try:
                            print(f"SPLIT_FALLBACK: snapping current foreground={int(cur_fg)} then Word")
                        except Exception:
                            pass
                        opposite_side = 'left' if word_side_effective == 'right' else 'right'
                        _force_foreground(cur_fg)
                        _send_win_arrow(side=opposite_side)
                        _time.sleep(0.15)
                        _force_foreground(hwnd_word)
                        _send_win_arrow(side=word_side_effective)
                        split_applied = True
                        flow_label = "fallback_os"
                    if not split_applied:
                        # Fallback to manual arrange or single snap
                        if cur_fg and _is_window(cur_fg) and cur_fg != hwnd_word:
                            split_applied = _arrange_side_by_side(cur_fg, hwnd_word, b_on_right=(word_side_effective != 'left'))
                            if split_applied:
                                flow_label = "manual_arrange"
                        if not split_applied:
                            _snap_single_window(hwnd_word, side=word_side_effective)
                            flow_label = "single_snap"
        except Exception:
            pass
        if bool(req.split_screen):
            if split_applied or _is_snapped_to_side(hwnd_word, side=word_side_effective):
                _set_split_state(1, primary_hwnd=hwnd_word, partner_hwnd=None, side=word_side_effective, target='word', path=getattr(req, 'abs_path', None))
            else:
                _set_split_state(0)
        else:
            _set_split_state(0)
        result_payload = {"launched": True, "visible": bool(req.show_window), "saved_path": saved_path, "split_screen": split_applied, "cua_attempted": cua_attempted, "cua_selected": cua_selected, "flow": flow_label, **desktop_info}
        try:
            try:
                import backend.cua_adapter as _cua_adapter_mode  # type: ignore
            except Exception:
                try:
                    import cua_adapter as _cua_adapter_mode  # type: ignore
                except Exception:
                    _cua_adapter_mode = None  # type: ignore
            _cua_status_mode = _cua_adapter_mode.cua_runtime_status() if hasattr(_cua_adapter_mode, 'cua_runtime_status') else {}
            _cua_forced_mode = bool(_cua_status_mode.get('agent_ready'))
        except Exception:
            _cua_forced_mode = False
        result_payload['cua_forced'] = _cua_forced_mode and bool(getattr(req, 'use_cua_for_selection', True))
        result_payload['automation_mode'] = 'cua_forced' if result_payload['cua_forced'] else ('cua' if getattr(req, 'use_cua_for_selection', True) else 'legacy')
        if cua_attempted and not cua_selected:
            result_payload["cua_reason"] = "tokens_not_found_or_snap_assist_absent"
        # Inline CUA diagnostics if available
        if cua_attempted:
            try:
                try:
                    import backend.cua_adapter as _cua_adapter  # type: ignore
                except Exception:
                    import cua_adapter as _cua_adapter  # type: ignore
                diag = getattr(_cua_adapter, '_cua_diag_last', None)
                if isinstance(diag, dict):
                    _diag = dict(diag)
                    attempts = _diag.get('attempts') or []
                    if isinstance(attempts, list) and len(attempts) > 6:
                        _diag['attempts'] = attempts[:6]
                    result_payload['cua_diagnostics'] = _diag
            except Exception:
                pass
        return result_payload
    except Exception as e:
        _set_split_state(0)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if callable(uninit):
                uninit()
        except Exception:
            pass


@router.post("/word/execute")
def word_execute(req: WordTypeRequest) -> dict:
    # Use the shared implementation so logs and CUA flow are consistent
    return _word_execute_impl(req)


@router.post("/word/open_existing")
def word_open_existing(req: WordOpenExistingRequest) -> dict:
    if os.name != 'nt':
        raise HTTPException(status_code=400, detail="Windows-only")
    if comtypes_client is None:
        raise HTTPException(status_code=500, detail="comtypes not installed")
    if not req.abs_path or not os.path.isfile(req.abs_path):
        raise HTTPException(status_code=400, detail="abs_path not found")
    uninit = None
    try:
        uninit = _coinit()
        hwnd_fore = None
        try:
            hwnd_fore = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            hwnd_fore = None
        try:
            app = comtypes_client.GetActiveObject('Word.Application')
        except Exception:
            app = comtypes_client.CreateObject('Word.Application')
        app.Visible = True
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        try:
            app.WindowState = 0
        except Exception:
            pass
        requested_word_side = str(getattr(req, 'word_side', 'right') or 'right').lower()
        if requested_word_side not in ('left', 'right'):
            requested_word_side = 'right'
        word_side_effective = requested_word_side
        # Open document
        doc = app.Documents.Open(req.abs_path)
        try:
            app.Activate()
        except Exception:
            pass
        # Resolve Word window handle robustly
        hwnd_word = _get_word_hwnd(app, max_wait_ms=2500)
        # Optional delay to let rendering settle
        if getattr(req, 'arrangement_delay_ms', 0) and req.arrangement_delay_ms > 0:
            _time.sleep(min(5.0, req.arrangement_delay_ms / 1000.0))
        _wait_for_ready_window(hwnd_word, timeout_ms=1500)
        split_applied = False
        cua_attempted = False
        cua_selected = False
        flow_label = "none"
        pre_already_split = False
        if _is_snapped_to_side(hwnd_word, side=word_side_effective):
            pre_already_split = True
            split_applied = True
            flow_label = "already_split"
        if bool(req.split_screen) and hwnd_word and not pre_already_split:
            try:
                print(f"SPLIT_PRECHECK: show=True split={bool(req.split_screen)} hwnd_word={int(hwnd_word)}")
            except Exception:
                pass
            # Only allow a browser as partner for Word
            valid_pair = (
                hwnd_fore and _is_window(hwnd_fore) and (hwnd_fore != hwnd_word) and _is_window_visible_and_normal(hwnd_fore)
                and _is_browser_window(hwnd_fore)
            )
            target_hwnd = None
            if valid_pair and _is_browser_window(hwnd_fore):
                target_hwnd = hwnd_fore
            if target_hwnd is None:
                target_hwnd = _find_alternate_window(
                    [hwnd_word],
                    prefer_monitor_of=hwnd_word,
                    prefer_browser=True,
                    browser_only=True,
                    allowed_types={'browser'}
                )
            if target_hwnd:
                partner_hwnd = target_hwnd
                if _is_browser_window(partner_hwnd) and word_side_effective != 'left':
                    try:
                        print("SPLIT_ADJUST: keeping browser on right; forcing Word to left")
                    except Exception:
                        pass
                    word_side_effective = 'left'
                opposite_side = 'left' if word_side_effective == 'right' else 'right'
                _wait_for_ready_window(partner_hwnd, timeout_ms=1000)
                if getattr(req, 'use_os_snap_keys', True):
                    try:
                        print("SPLIT_FLOW: using OS snap keys (browser then word)")
                    except Exception:
                        pass
                    # Snap browser
                    _force_foreground(partner_hwnd)
                    _send_win_arrow(side=opposite_side)
                    _time.sleep(0.18)
                    # Snap word
                    _force_foreground(hwnd_word)
                    _send_win_arrow(side=word_side_effective)
                    _time.sleep(0.18)
                    # Retry if needed
                    if not _is_snapped_to_side(hwnd_word, side=word_side_effective):
                        _force_foreground(hwnd_word)
                        _send_win_arrow(side=word_side_effective)
                        _time.sleep(0.12)
                    if not _is_snapped_to_side(partner_hwnd, side=opposite_side):
                        _force_foreground(partner_hwnd)
                        _send_win_arrow(side=opposite_side)
                        _time.sleep(0.12)
                    flow_label = "os_snap_dual"
                    doc_name_tokens = []
                    try:
                        name = ''
                        try:
                            name = str(getattr(app.ActiveDocument, 'Name', '') or '')
                        except Exception:
                            name = ''
                        if name:
                            base = os.path.splitext(name)[0]
                            doc_name_tokens = [base, 'microsoft word', 'word']
                        else:
                            doc_name_tokens = ['microsoft word', 'word']
                    except Exception:
                        doc_name_tokens = ['word']
                    selected = False
                    _force_cua = False
                    try:
                        try:
                            import backend.cua_adapter as cua_adapter  # type: ignore
                        except Exception:
                            try:
                                import cua_adapter  # type: ignore
                            except Exception:
                                cua_adapter = None  # type: ignore
                        if hasattr(cua_adapter, 'cua_runtime_status') and cua_adapter.cua_runtime_status().get('agent_ready'):
                            _force_cua = True
                    except Exception:
                        _force_cua = False
                    if _force_cua or getattr(req, 'use_cua_for_selection', False):
                        cua_attempted = True
                        try:
                            print(f"CUA_SELECT: attempting with tokens={doc_name_tokens}")
                            selected = _cua_select_snap_word(doc_name_tokens)
                            cua_selected = bool(selected)
                            print(f"CUA_SELECT: result selected={selected}")
                        except Exception as _e:
                            print(f"CUA_SELECT: exception: {_e}")
                            selected = False
                    if (not selected) and (not _uia_select_snap_word(doc_name_tokens, max_steps=20)):
                        # Ensure windows remain snapped
                        if not _is_snapped_to_side(hwnd_word, side=word_side_effective):
                            _force_foreground(hwnd_word)
                            _send_win_arrow(side=word_side_effective)
                        if not _is_snapped_to_side(partner_hwnd, side=opposite_side):
                            _force_foreground(partner_hwnd)
                            _send_win_arrow(side=opposite_side)
                    split_applied = True
                else:
                    split_applied = _arrange_side_by_side(target_hwnd, hwnd_word, b_on_right=(word_side_effective != 'left'))
                    if split_applied:
                        flow_label = "manual_arrange"
            elif bool(req.fallback_snap):
                split_applied = _snap_single_window(hwnd_word, side=word_side_effective)
                flow_label = "single_snap"
        if bool(req.split_screen) and (split_applied or _is_snapped_to_side(hwnd_word, side=word_side_effective)):
            _set_split_state(1, primary_hwnd=hwnd_word, partner_hwnd=None, side=word_side_effective, target='word', path=req.abs_path)
        if not split_applied and bool(req.fallback_snap):
            try:
                cur_fg = ctypes.windll.user32.GetForegroundWindow()
            except Exception:
                cur_fg = None
            if cur_fg and _is_window(cur_fg) and cur_fg != hwnd_word and getattr(req, 'use_os_snap_keys', True):
                opposite_side = 'left' if word_side_effective == 'right' else 'right'
                _force_foreground(cur_fg)
                _send_win_arrow(side=opposite_side)
                _time.sleep(0.15)
                _force_foreground(hwnd_word)
                _send_win_arrow(side=word_side_effective)
                split_applied = True
                flow_label = "fallback_os"
            if not split_applied:
                if cur_fg and _is_window(cur_fg) and cur_fg != hwnd_word:
                    split_applied = _arrange_side_by_side(cur_fg, hwnd_word, b_on_right=(word_side_effective != 'left'))
                    if split_applied:
                        flow_label = "manual_arrange"
                if not split_applied:
                    _snap_single_window(hwnd_word, side=word_side_effective)
                    flow_label = "single_snap"
        if bool(req.split_screen):
            if split_applied or _is_snapped_to_side(hwnd_word, side=word_side_effective):
                _set_split_state(1, primary_hwnd=hwnd_word, partner_hwnd=None, side=word_side_effective, target='word', path=req.abs_path)
            else:
                _set_split_state(0)
        else:
            _set_split_state(0)
        # Build result metadata (include side and partner info for parity with VS Code flow)
        result_payload = {"opened": True, "path": req.abs_path, "split_screen": split_applied, "cua_attempted": cua_attempted, "cua_selected": cua_selected, "flow": flow_label, "side": word_side_effective}
        try:
            if 'partner_hwnd' in locals() and partner_hwnd:
                result_payload['partner_hwnd'] = int(partner_hwnd)
                # Add a lightweight partner title
                try:
                    buf_t2 = ctypes.create_unicode_buffer(512)
                    ctypes.windll.user32.GetWindowTextW(wintypes.HWND(partner_hwnd), buf_t2, 512)
                    partner_title = (buf_t2.value or '').strip()
                    if partner_title:
                        result_payload['partner_title'] = partner_title
                except Exception:
                    pass
        except Exception:
            pass
        try:
            try:
                import backend.cua_adapter as _cua_adapter_we2  # type: ignore
            except Exception:
                try:
                    import cua_adapter as _cua_adapter_we2  # type: ignore
                except Exception:
                    _cua_adapter_we2 = None  # type: ignore
            _cua_status_we2 = _cua_adapter_we2.cua_runtime_status() if hasattr(_cua_adapter_we2, 'cua_runtime_status') else {}
            _cua_forced_we2 = bool(_cua_status_we2.get('agent_ready'))
        except Exception:
            _cua_forced_we2 = False
        result_payload['cua_forced'] = _cua_forced_we2 and bool(getattr(req, 'use_cua_for_selection', True))
        result_payload['automation_mode'] = 'cua_forced' if result_payload['cua_forced'] else ('cua' if getattr(req, 'use_cua_for_selection', True) else 'legacy')
        if cua_attempted and not cua_selected:
            result_payload["cua_reason"] = "tokens_not_found_or_snap_assist_absent"
        if cua_attempted:
            try:
                try:
                    import backend.cua_adapter as _cua_adapter  # type: ignore
                except Exception:
                    import cua_adapter as _cua_adapter  # type: ignore
                diag = getattr(_cua_adapter, '_cua_diag_last', None)
                if isinstance(diag, dict):
                    _diag = dict(diag)
                    attempts = _diag.get('attempts') or []
                    if isinstance(attempts, list) and len(attempts) > 6:
                        _diag['attempts'] = attempts[:6]
                    result_payload['cua_diagnostics'] = _diag
            except Exception:
                pass
        return result_payload
    except Exception as e:
        _set_split_state(0)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if callable(uninit):
                uninit()
        except Exception:
            pass


@router.post("/word/snap_keys")
def word_snap_keys(req: WordOpenExistingRequest) -> dict:
    """Snap Word using OS Win+Arrow keys. Opens doc if provided, focuses Word, and sends snap.
    Request body is same as open_existing; abs_path optional here.
    """
    if os.name != 'nt':
        raise HTTPException(status_code=400, detail="Windows-only")
    if comtypes_client is None:
        raise HTTPException(status_code=500, detail="comtypes not installed")
    uninit = None
    try:
        uninit = _coinit()
        try:
            app = comtypes_client.GetActiveObject('Word.Application')
        except Exception:
            app = comtypes_client.CreateObject('Word.Application')
        app.Visible = True
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        try:
            app.WindowState = 0
        except Exception:
            pass
        if getattr(req, 'abs_path', None):
            try:
                app.Documents.Open(req.abs_path)
            except Exception:
                pass
        hwnd_word = 0
        for _ in range(10):
            try:
                hwnd_word = int(getattr(app, 'Hwnd', 0))
            except Exception:
                hwnd_word = 0
            if hwnd_word and _is_window(hwnd_word):
                break
            _time.sleep(0.05)
        _force_foreground(hwnd_word)
        ok = _send_win_arrow(side=str(req.word_side))
        return {"snapped": bool(ok), "word_side": req.word_side}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if callable(uninit):
                uninit()
        except Exception:
            pass


# Export functions to be used by power_router.py
def word_preview(req):
    """Preview function for word.open_and_type automation."""
    # Normalize parameter names from different sources
    text = getattr(req, 'text', '') or getattr(req, 'paragraph', '') or ''
    text_len = len(text)
    save_target = getattr(req, 'save_target', None)
    return {
        "summary": f"Open Word and type {text_len} chars{' and save' if save_target else ''}",
        "save_target": save_target,
        "show_window": getattr(req, 'show_window', True),
        "split_screen": getattr(req, 'split_screen', True),
    }

def word_execute(req):
    """Execute function for word.open_and_type automation (shared with API route)."""
    # Build a WordTypeRequest-like object to retain defaults and validation semantics
    # But accept that req may be a simple object with attributes; map fields carefully.
    try:
        print(f"WORD EXECUTE CALLED with parameters: {dir(req)}")
        # Log all attributes
        attr_values = {}
        for attr in dir(req):
            if not attr.startswith('__'):
                try:
                    attr_values[attr] = getattr(req, attr)
                except Exception:
                    attr_values[attr] = "<error getting value>"
        print(f"Request attributes: {attr_values}")

        # Normalize incoming fields
        text_content = getattr(req, 'text', '') or getattr(req, 'paragraph', '') or ''
        show_window = bool(getattr(req, 'show_window', True))
        save_target = getattr(req, 'save_target', None)
        split_screen = bool(getattr(req, 'split_screen', True))
        word_side = getattr(req, 'word_side', 'right')
        arrangement_delay_ms = int(getattr(req, 'arrangement_delay_ms', 600))
        use_os_snap_keys = bool(getattr(req, 'use_os_snap_keys', True))
        use_cua_for_selection = bool(getattr(req, 'use_cua_for_selection', True))
        append_flag = bool(getattr(req, 'append', True))

        req2 = WordTypeRequest(
            text=text_content,
            show_window=show_window,
            save_target=save_target,
            split_screen=split_screen,
            word_side=word_side,
            arrangement_delay_ms=arrangement_delay_ms,
            use_os_snap_keys=use_os_snap_keys,
            use_cua_for_selection=use_cua_for_selection,
            append=append_flag,
        )
        return _word_execute_impl(req2)
    except Exception as e:
        return {"error": str(e)}

@router.post("/vscode/open_existing")
def vscode_open_existing(req: VSCodeOpenRequest) -> dict:
    """Open an existing file in VS Code and optionally arrange it side-by-side with the current window."""
    from power_router import _open_vscode_path
    import time
    
    if os.name != 'nt':
        raise HTTPException(status_code=400, detail="Windows-only")
    abs_path_real = os.path.abspath(req.abs_path) if req.abs_path else ''
    if not abs_path_real or not os.path.isfile(abs_path_real):
        raise HTTPException(status_code=400, detail="abs_path not found")

    requested_code_side = str(getattr(req, 'code_side', 'right') or 'right').lower()
    if requested_code_side not in ('left', 'right'):
        requested_code_side = 'right'
    code_side_effective = 'left'
    if requested_code_side != 'left':
        try:
            print(f"VSCODE_SIDE_ADJUST: forcing left side instead of '{requested_code_side}'")
        except Exception:
            pass
    opposite_side = 'right'

    arrangement_delay_ms = max(0, int(getattr(req, 'arrangement_delay_ms', 1000)))
    use_os_snap = bool(getattr(req, 'use_os_snap_keys', True))
    use_cua_requested = bool(getattr(req, 'use_cua_for_selection', True))
    use_cua = use_cua_requested
    # Force-enable CUA when embedded agent reports ready
    try:
        try:
            import backend.cua_adapter as cua_adapter  # type: ignore
        except Exception:
            try:
                import cua_adapter  # type: ignore
            except Exception:
                cua_adapter = None  # type: ignore
        if hasattr(cua_adapter, 'cua_runtime_status') and cua_adapter.cua_runtime_status().get('agent_ready'):
            use_cua = True
        elif not use_cua and hasattr(cua_adapter, 'cua_available') and cua_adapter.cua_available():
            # Backward compatibility: still attempt if available
            use_cua = True
    except Exception:
        pass

    split_requested = bool(getattr(req, 'split_screen', True))
    fallback_snap = bool(getattr(req, 'fallback_snap', True))
    skip_state = False
    existing_state: Dict[str, Any] = {}
    if split_requested:
        skip_state, existing_state = _should_skip_automation('vscode', abs_path_real)
        if skip_state:
            existing_hwnd = existing_state.get('primary_hwnd')
            tab_ok = False
            if existing_hwnd and _is_window(existing_hwnd):
                tab_ok = _ensure_vscode_tab_for_path(existing_hwnd, abs_path_real)
            if tab_ok:
                existing_side = 'left'
                if str(existing_state.get('side') or '').lower() != 'left':
                    try:
                        print("VSCODE_SIDE_ADJUST: cached split adjusted to 'left'")
                    except Exception:
                        pass
                _set_split_state(
                    1,
                    primary_hwnd=existing_hwnd,
                    partner_hwnd=existing_state.get('partner_hwnd'),
                    side=existing_side,
                    target='vscode',
                    path=abs_path_real,
                )
                return {
                    "opened": True,
                    "reused": True,
                    "snapped": True,
                    "skip_reason": "split_window_already_active",
                    "vscode_hwnd": existing_hwnd,
                    "tab_matched": True,
                    "path": abs_path_real,
                }
            _set_split_state(0)

    try:
        # Capture foreground and existing VS Code windows BEFORE launching (for delta detection)
        hwnd_fore = None
        try:
            hwnd_fore = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            hwnd_fore = None
        before_vscode = {hwnd for hwnd, _ in _list_vscode_windows()}

        # Launch VS Code with the file (may reuse existing window or spawn new)
        result = _open_vscode_path(
            abs_path=abs_path_real,
            side=code_side_effective,
            split=False,  # We'll handle split screen ourselves for better control
            new_window=False  # Reuse existing VS Code window to avoid duplicate windows
        )
        
        if not result.get("opened"):
            _set_split_state(0)
            return result
            
        # Allow VS Code time to open
        time.sleep(arrangement_delay_ms / 1000)

        # Find the VS Code window most closely associated with the target file
        file_basename = os.path.basename(abs_path_real)
        file_stem = os.path.splitext(file_basename)[0] if file_basename else ''
        vscode_hwnd, window_snapshot = _pick_best_vscode_window(file_basename, before_handles=before_vscode)
        if window_snapshot:
            try:
                print("VSCODE_WINDOWS_CANDIDATES:")
                for hwnd, title in window_snapshot[:6]:
                    print(f"  hwnd={hwnd} title='{title}'")
            except Exception:
                pass

        result["vscode_hwnd"] = vscode_hwnd
        result["requested_side"] = requested_code_side
        result["effective_side"] = code_side_effective
        result["use_cua_requested"] = use_cua_requested
        result["use_cua_applied"] = use_cua
        result["use_os_snap"] = use_os_snap
        
        # Skip if we can't find the VS Code window
        if not vscode_hwnd:
            result["error"] = "Could not find VS Code window"
            _set_split_state(0)
            return result
            
        pair_hwnd: Optional[int] = None
        cua_attempted = False
        cua_selected = False

        # Check if VS Code is already snapped to the requested side
        if _is_snapped_to_side(vscode_hwnd, side=code_side_effective):
            result["snapped"] = True
            result["already_snapped"] = True
            tab_ok = _ensure_vscode_tab_for_path(vscode_hwnd, abs_path_real)
            result["tab_matched"] = bool(tab_ok)
            if split_requested:
                _set_split_state(1, primary_hwnd=vscode_hwnd, partner_hwnd=None, side=code_side_effective, target='vscode', path=abs_path_real)
            else:
                _set_split_state(0)
            return result
            
        # Handle split screen if requested
        if split_requested:
            valid_pair = (
                hwnd_fore
                and _is_window(hwnd_fore)
                and (hwnd_fore != vscode_hwnd)
                and _is_window_visible_and_normal(hwnd_fore)
                and _is_browser_window(hwnd_fore)
            )
            target_hwnd = None
            if valid_pair:
                target_hwnd = hwnd_fore
            if target_hwnd is None:
                # First pass: browsers only
                target_hwnd = _find_alternate_window(
                    [vscode_hwnd],
                    prefer_monitor_of=vscode_hwnd,
                    prefer_browser=True,
                    browser_only=True,
                    allowed_types={'browser','vscode','word'}
                )
            if target_hwnd is None:
                # Second pass: any allowed type, prefer browsers
                target_hwnd = _find_alternate_window(
                    [vscode_hwnd],
                    prefer_monitor_of=vscode_hwnd,
                    prefer_browser=True,
                    browser_only=False,
                    allowed_types={'browser','vscode','word'}
                )
            # If we somehow picked another VS Code window (should normally be excluded), try again excluding it
            if target_hwnd and _is_vscode_window(target_hwnd):
                target_hwnd = _find_alternate_window(
                    [vscode_hwnd, target_hwnd],
                    prefer_monitor_of=vscode_hwnd,
                    prefer_browser=True,
                    browser_only=False,
                    allowed_types={'browser','vscode','word'}
                )

            if target_hwnd:
                pair_hwnd = target_hwnd
                try:
                    print(f"VSCODE_PARTNER: hwnd={int(target_hwnd)} browser={_is_browser_window(target_hwnd)} title='{_get_window_title(target_hwnd)}'")
                except Exception:
                    pass
                # SAFEGUARD: If partner is another VS Code but a browser is visible, swap.
                try:
                    if _is_vscode_window(target_hwnd):
                        # scan for any browser window not excluded
                        for _h in _enum_windows_collect():
                            if _h in (vscode_hwnd, target_hwnd):
                                continue
                            if not _is_window_visible_and_normal(_h):
                                continue
                            if _is_browser_window(_h):
                                print(f"PARTNER_SWAP: replacing secondary VS Code ({target_hwnd}) with browser {_h}")
                                pair_hwnd = _h
                                target_hwnd = _h
                                break
                except Exception:
                    pass
                _wait_for_ready_window(target_hwnd, timeout_ms=1000)

                if use_os_snap:
                    print("VSCODE_SPLIT: Using OS snap keys for window arrangement")
                    # Global deterministic dual snap bypass (faster). If FORCE_CUA_VSCODE env set, we skip this.
                    force_env = os.environ.get('FORCE_CUA_VSCODE', '').lower() in {'1','true','yes','on'}
                    if not force_env:
                        try:
                            print("VSCODE_DUAL_SNAP_BYPASS(global): snapping VS Code + partner directly")
                        except Exception:
                            pass
                        _force_foreground(vscode_hwnd)
                        _send_win_arrow(side=code_side_effective)
                        time.sleep(0.12)
                        _force_foreground(target_hwnd)
                        _send_win_arrow(side=opposite_side)
                        result["snapped"] = True
                        result["snap_method"] = "direct_dual_snap_global"
                        result["cua_attempted"] = False
                        result["cua_selected"] = False
                        result["cua_reason"] = "global_bypass"
                        selected = True
                        # Skip local bypass / CUA path entirely
                        goto_tab_match = True
                    else:
                        goto_tab_match = False
                    if 'goto_tab_match' in locals() and goto_tab_match:
                        # Jump to rest of logic (skip Snap Assist token work)
                        pass
                    else:
                        _force_foreground(target_hwnd)
                        _send_win_arrow(side=opposite_side)
                        time.sleep(0.25)

                    # Fast-path dual snap bypass section (properly indented)
                    bypass_cua = False
                    try:
                        allowed_ct = 0
                        for _h in _enum_windows_collect():
                            if _h in (vscode_hwnd, target_hwnd):
                                continue
                            if not _is_window_visible_and_normal(_h):
                                continue
                            # Identify Word windows (class contains OpusApp)
                            is_word = False
                            try:
                                buf_cls = ctypes.create_unicode_buffer(256)
                                ctypes.windll.user32.GetClassNameW(wintypes.HWND(_h), buf_cls, 256)
                                if 'OpusApp' in (buf_cls.value or ''):
                                    is_word = True
                            except Exception:
                                pass
                            if _is_browser_window(_h) or _is_vscode_window(_h) or is_word:
                                allowed_ct += 1
                                if allowed_ct > 0:
                                    break
                        if allowed_ct == 0 and _is_browser_window(target_hwnd):
                            bypass_cua = True
                    except Exception:
                        bypass_cua = False

                    if bypass_cua:
                        try:
                            print("CUA_BYPASS: Direct dual snap (no Snap Assist selection needed)")
                        except Exception:
                            pass
                        _force_foreground(vscode_hwnd)
                        _send_win_arrow(side=code_side_effective)
                        time.sleep(0.18)
                        _force_foreground(target_hwnd)
                        _send_win_arrow(side=opposite_side)
                        result["snapped"] = True
                        result["snap_method"] = "direct_dual_snap"
                        result["cua_attempted"] = False
                        result["cua_selected"] = False
                        result["cua_reason"] = "bypassed_direct_pair"
                        selected = True
                    else:
                        # Build an augmented token list for CUA selection
                        vscode_tokens = [tok for tok in [file_basename, file_stem] if tok]
                        # (Rest of token generation and CUA attempt logic continues below)
                    # If bypass_cua executed or global bypass, skip CUA token logic entirely.
                    if ('bypass_cua' in locals() and bypass_cua) or ('goto_tab_match' in locals() and goto_tab_match):
                        pass
                    else:
                        # Derive workspace candidates from existing VS Code window title(s)
                        workspace_candidates: list[str] = []
                        try:
                            if window_snapshot:
                                for _h, _title in window_snapshot:
                                    if not _title:
                                        continue
                                    parts_ws = [p.strip() for p in _title.split(' - ') if p.strip()]
                                    if len(parts_ws) >= 2 and 'visual studio code' in parts_ws[-1].lower():
                                        middle = parts_ws[1:-1]
                                        for seg in middle:
                                            if seg and seg.lower() not in [w.lower() for w in workspace_candidates]:
                                                workspace_candidates.append(seg)
                        except Exception:
                            pass

                        # Build pattern tokens for expected tile text formats
                        pattern_tokens: list[str] = []
                        try:
                            if file_basename:
                                pattern_tokens.append(f"{file_basename} - Visual Studio Code")
                                for ws in workspace_candidates:
                                    pattern_tokens.append(f"{file_basename} - {ws} - Visual Studio Code")
                        except Exception:
                            pass

                        for pt in pattern_tokens:
                            if pt.lower() not in [t.lower() for t in vscode_tokens]:
                                vscode_tokens.append(pt)

                    # Prepend tokens derived from doc_info (highest priority for selection)
                    try:
                        doc_info_raw = None
                        try:
                            doc_info_raw = getattr(req, 'doc_info', None)
                        except Exception:
                            doc_info_raw = None
                        if doc_info_raw:
                            if isinstance(doc_info_raw, str):
                                doc_items = [d.strip() for d in doc_info_raw.split(',') if d.strip()]
                            elif isinstance(doc_info_raw, (list, tuple, set)):
                                doc_items = []
                                for d in doc_info_raw:
                                    if isinstance(d, str) and d.strip():
                                        doc_items.append(d.strip())
                            else:
                                doc_items = []
                            doc_tokens: list[str] = []
                            import os as _os_doc
                            for item in doc_items:
                                # Break possible paths and names
                                base = _os_doc.path.basename(item)
                                stem = base.rsplit('.', 1)[0] if '.' in base else base
                                for cand in [item, base, stem]:
                                    if cand and cand.lower() not in [t.lower() for t in doc_tokens]:
                                        doc_tokens.append(cand)
                            # Prepend doc-specific tokens to ensure they are treated as "specific" before generic app labels
                            if doc_tokens:
                                vscode_tokens = doc_tokens + vscode_tokens
                    except Exception:
                        pass

                    # Prepare generic tokens separately so we can attempt a specific-first pass
                    generic_token_pool = ['visual studio code', 'vs code', 'visual studio']
                    for generic_tok in generic_token_pool:
                        # We'll append later conditionally
                        pass
                    # Add pieces of current VS Code window title (pre-snap) to increase match likelihood
                    try:
                        cur_title = (_get_window_title(vscode_hwnd) or '').strip()
                        if cur_title:
                            parts = [p.strip() for p in re.split(r" - |\\|/", cur_title) if p.strip()]
                            for p in parts:
                                if p and p.lower() not in [t.lower() for t in vscode_tokens]:
                                    vscode_tokens.append(p)
                    except Exception:
                        pass
                    # De-duplicate prelim specific tokens
                    seen_lower = set(); dedup_specific = []
                    for t in vscode_tokens:
                        tl = t.lower()
                        if tl not in seen_lower:
                            seen_lower.add(tl)
                            dedup_specific.append(t)
                    vscode_tokens = dedup_specific

                    # Remove tokens that are clearly from other open VS Code windows (e.g., currently focused different file)
                    try:
                        if window_snapshot:
                            other_titles = [(_h, _title) for _h, _title in window_snapshot if _title]
                            other_file_tokens = set()
                            for _h, _title in other_titles:
                                parts = [p.strip() for p in _title.split(' - ') if p.strip()]
                                if parts:
                                    first = parts[0]
                                    if file_basename and first.lower() != file_basename.lower():
                                        other_file_tokens.add(first.lower())
                            if other_file_tokens:
                                vscode_tokens = [t for t in vscode_tokens if t.lower() not in other_file_tokens]
                    except Exception:
                        pass

                    # Add a lightweight diacritic-stripped variant for any token containing non-ascii (workspace may have accents)
                    try:
                        import unicodedata as _ud
                        extra_norm: list[str] = []
                        for t in vscode_tokens:
                            if any(ord(ch) > 127 for ch in t):
                                norm = ''.join(c for c in _ud.normalize('NFD', t) if _ud.category(c) != 'Mn')
                                if norm and norm.lower() not in [x.lower() for x in vscode_tokens] and norm.lower() not in [x.lower() for x in extra_norm]:
                                    extra_norm.append(norm)
                        vscode_tokens.extend(extra_norm)
                    except Exception:
                        pass

                    # Determine if multiple VS Code windows exist (potential ambiguity)
                    multiple_vscode = False
                    try:
                        if window_snapshot:
                            vs_count = 0
                            for _h, _title in window_snapshot:
                                if _title and 'visual studio code' in _title.lower():
                                    vs_count += 1
                            multiple_vscode = vs_count > 1
                    except Exception:
                        multiple_vscode = False

                    # Build ordered token attempt sets: specific first, then add generics if needed
                    token_attempt_sets: list[list[str]] = []
                    if multiple_vscode:
                        token_attempt_sets.append(vscode_tokens[:])  # specific only
                        # second attempt adds generic labels
                        extended = vscode_tokens[:] + [g for g in generic_token_pool if g not in [t.lower() for t in vscode_tokens]]
                        token_attempt_sets.append(extended)
                    else:
                        full = vscode_tokens[:] + [g for g in generic_token_pool if g not in [t.lower() for t in vscode_tokens]]
                        token_attempt_sets.append(full)
                    selected = False
                    attempted_token_sets: list[list[str]] = []

                    # Force-enable CUA if agent_ready, even if use_cua flag was false earlier
                    _force_cua = False
                    try:
                        try:
                            import backend.cua_adapter as cua_adapter  # type: ignore
                        except Exception:
                            try:
                                import cua_adapter  # type: ignore
                            except Exception:
                                cua_adapter = None  # type: ignore
                        if hasattr(cua_adapter, 'cua_runtime_status') and cua_adapter.cua_runtime_status().get('agent_ready'):
                            _force_cua = True
                    except Exception:
                        _force_cua = False
                    if use_cua or _force_cua:
                        cua_attempted = True
                        try:
                            # Short extra delay to let Snap Assist grid populate fully
                            time.sleep(0.10)
                            for attempt_index, token_set in enumerate(token_attempt_sets, start=1):
                                print(f"CUA_SELECT: attempt {attempt_index} tokens={token_set}")
                                attempted_token_sets.append(token_set)
                                selected = _cua_select_snap_vscode(token_set)
                                if selected:
                                    cua_selected = True
                                    print(f"CUA_SELECT: success on attempt {attempt_index}")
                                    break
                                else:
                                    print(f"CUA_SELECT: no match attempt {attempt_index}")
                        except Exception as e:
                            print(f"CUA_SELECT: exception: {e}")
                            selected = False
                        # Retry once if diagnostics indicate snap assist might not have populated yet
                        if (not selected):
                            try:
                                import backend.cua_adapter as _cua_adapter  # type: ignore
                            except Exception:
                                try:
                                    import cua_adapter as _cua_adapter  # type: ignore
                                except Exception:
                                    _cua_adapter = None  # type: ignore
                            diag = getattr(_cua_adapter, '_cua_diag_last', None) if '_cua_adapter' in locals() else None
                            reason = ''
                            if isinstance(diag, dict):
                                reason = str(diag.get('reason') or '')
                                try:
                                    print(f"CUA_SELECT: diagnostics reason='{reason}' attempts={len(diag.get('attempts') or [])}")
                                except Exception:
                                    pass
                            # Broaden retry trigger to generic reasons surfaced at higher layer
                            if reason in {'snap_ui_absent', 'tokens_not_found', 'tokens_not_found_or_snap_ui_absent', 'tokens_not_found_or_snap_assist_absent'}:
                                try:
                                    print("CUA_SELECT: retrying after initial miss (reason=%s)" % reason)
                                except Exception:
                                    pass
                                time.sleep(0.25)
                                # Retry cycle through token sets again (sometimes focus reset helps)
                                if not selected:
                                    for attempt_index, token_set in enumerate(token_attempt_sets, start=1):
                                        try:
                                            print(f"CUA_SELECT: retry attempt {attempt_index} tokens={token_set}")
                                            selected = _cua_select_snap_vscode(token_set)
                                            if selected:
                                                cua_selected = True
                                                print(f"CUA_SELECT: retry success on attempt {attempt_index}")
                                                break
                                        except Exception as e2:
                                            print(f"CUA_SELECT: retry exception attempt {attempt_index}: {e2}")
                                    if not selected:
                                        print("CUA_SELECT: retry cycle complete without match")

                            # If still not selected after retry, attempt passive enumeration for deeper debugging
                            if not selected:
                                try:
                                    if hasattr(_cua_adapter, 'enumerate_snap_focus_cycle'):
                                        enum = _cua_adapter.enumerate_snap_focus_cycle(max_steps=30)
                                        unique_names = enum.get('unique_names') or []
                                        print(f"CUA_ENUM_SNAPSHOT: focus_changes={enum.get('focus_changes')} unique={len(unique_names)}")
                                        try:
                                            if unique_names:
                                                trimmed_names = [u if u else '<blank>' for u in unique_names[:10]]
                                                print("CUA_ENUM_TILES: " + " | ".join(trimmed_names))
                                        except Exception:
                                            pass
                                        # Attach a trimmed snapshot to result later (avoid huge payloads)
                                        result.setdefault('cua_enumeration', {
                                            'unique_names': enum.get('unique_names', [])[:12],
                                            'first_attempts': enum.get('attempts', [])[:12],
                                            'focus_changes': enum.get('focus_changes'),
                                            'reason': enum.get('reason'),
                                        })
                                except Exception as _e_enum:
                                    try:
                                        print(f"CUA_ENUM_ERROR: {_e_enum}")
                                    except Exception:
                                        pass

                    if not selected and not ('bypass_cua' in locals() and bypass_cua):
                        if not _uia_select_snap_vscode(vscode_tokens, max_steps=16):
                            candidates = _count_visible_windows(exclude_hwnds=[target_hwnd, vscode_hwnd])
                            if candidates > 0:
                                _press_key(VK_DOWN, repeats=candidates, delay=0.03)
                                _press_key(VK_RETURN, repeats=1, delay=0.03)
                            else:
                                _force_foreground(vscode_hwnd)
                                _send_win_arrow(side=code_side_effective)

                    if 'bypass_cua' in locals() and bypass_cua:
                        # Already snapped in bypass path
                        pass
                    else:
                        result["snapped"] = True
                        result["snap_method"] = "os_snap_keys"
                        if attempted_token_sets:
                            try:
                                result['cua_token_attempts'] = attempted_token_sets
                            except Exception:
                                pass
                else:
                    # manual arrangement path when OS snap keys not used
                    result["snapped"] = _arrange_side_by_side(target_hwnd, vscode_hwnd, b_on_right=(code_side_effective != 'left'))
                    result["snap_method"] = "manual_arrange"
            elif fallback_snap:
                _force_foreground(vscode_hwnd)
                _send_win_arrow(side=code_side_effective)
                result["snapped"] = True
                result["snap_method"] = "solo_snap"

        tab_ok = _ensure_vscode_tab_for_path(vscode_hwnd, abs_path_real)
        # After QuickOpen, verify the window title reflects the file; if not, try alternate windows
        title_after = (_get_window_title(vscode_hwnd) or '').lower()
        title_has_file = False
        if file_basename and file_basename.lower() in title_after:
            title_has_file = True
        elif file_stem and file_stem.lower() in title_after:
            title_has_file = True

        window_switched = False
        if not title_has_file and window_snapshot:
            for alt_hwnd, alt_title in window_snapshot:
                if alt_hwnd == vscode_hwnd:
                    continue
                if not _is_window(alt_hwnd):
                    continue
                # Attempt to focus alternate window and open tab there
                alt_ok = _ensure_vscode_tab_for_path(alt_hwnd, abs_path_real)
                alt_title_after = (_get_window_title(alt_hwnd) or '').lower()
                if file_basename.lower() in alt_title_after or (file_stem and file_stem.lower() in alt_title_after):
                    vscode_hwnd = alt_hwnd
                    window_switched = True
                    tab_ok = tab_ok or alt_ok
                    break

        result["tab_matched"] = bool(tab_ok)
        if window_switched:
            result["window_switched"] = True
            result["vscode_hwnd"] = vscode_hwnd
        result["cua_attempted"] = cua_attempted
        result["cua_selected"] = cua_selected
        if cua_attempted and not cua_selected:
            # Basic heuristic reason; deeper instrumentation would require adapter changes
            result["cua_reason"] = "snap_assist_tokens_not_found_or_snap_ui_absent"
        if cua_attempted:
            try:
                try:
                    import backend.cua_adapter as _cua_adapter  # type: ignore
                except Exception:
                    import cua_adapter as _cua_adapter  # type: ignore
                diag = getattr(_cua_adapter, '_cua_diag_last', None)
                if isinstance(diag, dict):
                    _diag = dict(diag)
                    attempts = _diag.get('attempts') or []
                    if isinstance(attempts, list) and len(attempts) > 6:
                        _diag['attempts'] = attempts[:6]
                    result['cua_diagnostics'] = _diag
            except Exception:
                pass
        # Annotate automation mode summary
        try:
            try:
                import backend.cua_adapter as _cua_adapter2  # type: ignore
            except Exception:
                try:
                    import cua_adapter as _cua_adapter2  # type: ignore
                except Exception:
                    _cua_adapter2 = None  # type: ignore
            _cua_status_tmp = _cua_adapter2.cua_runtime_status() if hasattr(_cua_adapter2, 'cua_runtime_status') else {}
            cua_forced_flag_tmp = bool(_cua_status_tmp.get('agent_ready'))
        except Exception:
            cua_forced_flag_tmp = False
        result['cua_forced'] = cua_forced_flag_tmp and bool(result.get('use_cua_applied'))
        result['automation_mode'] = 'cua_forced' if result['cua_forced'] else ('cua' if result.get('use_cua_applied') else 'legacy')

        if split_requested:
            if result.get("snapped") or result.get("already_snapped"):
                _set_split_state(1, primary_hwnd=vscode_hwnd, partner_hwnd=pair_hwnd, side=code_side_effective, target='vscode', path=abs_path_real)
            else:
                _set_split_state(0)
        else:
            _set_split_state(0)

        return result
    except Exception as e:
        _set_split_state(0)
        return {"error": str(e), "opened": False, "snapped": False}
