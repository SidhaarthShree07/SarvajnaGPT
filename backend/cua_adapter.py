from __future__ import annotations
import os
import sys
import datetime as dt
from typing import Optional, Dict, Any
import logging
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(level=logging.INFO)

import threading
_thread_local = threading.local()

def _ensure_com_initialized() -> bool:
    """Ensure COM is initialized for this thread.
    Returns True if already or now initialized, False if all init attempts failed.
    """
    if getattr(_thread_local, 'com_inited', False):
        return True
    try:
        import pythoncom  # type: ignore
        pythoncom.CoInitialize()
        _thread_local.com_inited = True
        try:
            print("CUA_COM: Initialized via pythoncom.CoInitialize()")
        except Exception:
            pass
        return True
    except Exception:
        pass
    # Try comtypes
    try:
        import comtypes  # type: ignore
        if hasattr(comtypes, 'CoInitialize'):
            comtypes.CoInitialize()  # type: ignore
            _thread_local.com_inited = True
            try:
                print("CUA_COM: Initialized via comtypes.CoInitialize()")
            except Exception:
                pass
            return True
    except Exception:
        pass
    # Try ole32 directly
    try:
        import ctypes as _ct
        ole32 = _ct.windll.ole32
        # COINIT_APARTMENTTHREADED = 0x2
        hr = ole32.CoInitializeEx(None, 0x2)
        if hr in (0, 1):  # S_OK or S_FALSE
            _thread_local.com_inited = True
            try:
                print("CUA_COM: Initialized via ole32.CoInitializeEx(APT)")
            except Exception:
                pass
            return True
        else:
            try:
                print(f"CUA_COM: ole32.CoInitializeEx failed hr=0x{hr:X}")
            except Exception:
                pass
    except Exception:
        pass
    return False


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
AGENT_BASE_DIR = os.path.join(REPO_ROOT, "agent_output")
CUA_REPO_DIR = os.path.join(os.path.dirname(__file__), "cua")
# Potential embedded Python library roots inside the cloned CUA monorepo
CUA_LIBS_PY = os.path.join(CUA_REPO_DIR, 'libs', 'python')
_CUA_MODULE_PATHS = [
    os.path.join(CUA_LIBS_PY, 'core'),
    os.path.join(CUA_LIBS_PY, 'computer'),
    os.path.join(CUA_LIBS_PY, 'agent'),
]
for _p in _CUA_MODULE_PATHS:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Optional high-level kill switch for telemetry before any core imports happen.
if os.environ.get('DISABLE_CUA_TELEMETRY', '').lower() in {'1','true','yes','on'}:
    # Core checks CUA_TELEMETRY ("off" disables) and CUA_TELEMETRY_ENABLED (must be true-ish to enable)
    os.environ['CUA_TELEMETRY'] = 'off'
    os.environ['CUA_TELEMETRY_ENABLED'] = 'false'

os.makedirs(AGENT_BASE_DIR, exist_ok=True)


_cua_diag_last: dict | None = None
# Debounce repeated snap/select to avoid post-success overrides
_last_snap_success_ts: float = 0.0

def cua_available() -> bool:
    """Return True if embedded CUA repo exists and at least core module import is possible."""
    if not os.path.isdir(CUA_REPO_DIR):
        return False
    try:
        import core  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False

def cua_runtime_status() -> Dict[str, Any]:
    """Detailed runtime capability inspection for embedded CUA repo."""
    status: Dict[str, Any] = {
        'repo_dir_present': os.path.isdir(CUA_REPO_DIR),
        'module_paths_added': [p for p in _CUA_MODULE_PATHS if p in sys.path],
        'core_import': False,
        'computer_import': False,
        'agent_import': False,
        'telemetry_enabled': None,
        'agent_import_error': None,
        'agent_missing_deps': [],
        'python_version': sys.version.split()[0],
        'agent_python_requirement': None,
        'agent_supported': None,
        'agent_ready': False,
        'litellm_import': None,
    }
    if status['repo_dir_present']:
        # Attempt to parse all candidate pyproject.toml locations for requires-python
        pyproject_candidates = []
        for p in _CUA_MODULE_PATHS:
            cand = os.path.join(p, 'pyproject.toml')
            if os.path.isfile(cand):
                pyproject_candidates.append(cand)
        parsed_req = None
        for cand in pyproject_candidates:
            try:
                # Prefer tomllib if available (Py3.11+ as tomllib)
                try:
                    import tomllib  # type: ignore
                    with open(cand, 'rb') as f:
                        data = tomllib.load(f)
                    proj = data.get('project') or {}
                    req = proj.get('requires-python')
                    if req:
                        parsed_req = req
                        break
                except Exception:
                    # Fallback simple line scan
                    with open(cand, 'r', encoding='utf-8') as ftxt:
                        for line in ftxt:
                            ls = line.strip()
                            if ls.startswith('requires-python') and '=' in ls:
                                right = ls.split('=',1)[1].strip()
                                right = right.strip('"').strip("'")
                                if right:
                                    parsed_req = right
                                    raise StopIteration  # break outer
            except StopIteration:
                break
            except Exception:
                continue
        if parsed_req:
            status['agent_python_requirement'] = parsed_req
        # Determine if current interpreter satisfies requirement (simple >= pattern or PEP 440 lower bound)
        try:
            req = status.get('agent_python_requirement') or ''
            cur = status['python_version']
            agent_supported = True
            # Support patterns like ">=3.12" or ">=3.12,<4.0"
            if '>=' in req:
                part = req.split(',')[0]  # take first segment
                needed = part.split('>=',1)[1].strip()
                def _ver_tuple(s: str):
                    return tuple(int(p) for p in s.split('.') if p and p[0].isdigit())
                if _ver_tuple(cur) < _ver_tuple(needed):
                    agent_supported = False
            status['agent_supported'] = agent_supported
        except Exception:
            status['agent_supported'] = None
        try:
            import core  # type: ignore  # noqa: F401
            status['core_import'] = True
        except Exception:
            pass
        try:
            import computer  # type: ignore  # noqa: F401
            status['computer_import'] = True
        except Exception:
            pass
        try:
            if status.get('agent_supported') is False:
                status['agent_import_error'] = 'python_version_not_supported'
            else:
                try:
                    import agent  # type: ignore  # noqa: F401
                    status['agent_import'] = True
                except SyntaxError as se:  # Provide clearer guidance for syntax errors from newer Python features
                    msg = f"syntax_error_importing_agent: {str(se).splitlines()[0]}"
                    status['agent_import_error'] = msg[:400]
                except Exception as e:
                    status['agent_import_error'] = str(e).split('\n')[0][:400]
            # Heuristic missing deps detection
            lower_err = (status.get('agent_import_error') or '').lower()
            missing = []
            for dep_name in ('litellm', 'pydantic', 'httpx'):
                if dep_name in lower_err and dep_name not in missing:
                    missing.append(dep_name)
            status['agent_missing_deps'] = missing
        except Exception:
            pass
        # Telemetry status (best-effort); replicate core logic without forcing import side-effects
        try:
            # If core already imported we can query PostHog client, otherwise emulate env logic
            from core.telemetry.posthog import PostHogTelemetryClient  # type: ignore
            status['telemetry_enabled'] = PostHogTelemetryClient.is_telemetry_enabled()
        except Exception:
            # Fallback: environment-based inference
            telem_env = (os.environ.get('CUA_TELEMETRY', '').lower() != 'off') and (
                os.environ.get('CUA_TELEMETRY_ENABLED', 'true').lower() in {'1','true','yes','on'}
            )
            status['telemetry_enabled'] = bool(telem_env)
        # litellm presence
        try:
            import litellm  # type: ignore  # noqa: F401
            status['litellm_import'] = True
        except Exception:
            status['litellm_import'] = False
        status['agent_ready'] = bool(status['agent_import'])
    return status


def preview_objective(objective: str, target_rel: str) -> Dict[str, Any]:
    """Prepare a minimal preview for a CUA run.
    We describe what will happen and where artifacts will be saved.
    """
    target_abs = _resolve_under_base(target_rel)
    return {
        "objective": objective,
        "target_rel": target_rel,
        "target_abs": target_abs,
        "uses_cua": cua_available(),
        "summary": f"Run UI-automation to produce artifact at '{target_rel}'",
    }


def execute_objective(objective: str, target_rel: str, seed_files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a UI-automation style task. If CUA is not available, write a stub file offline to simulate output.
    This keeps behavior deterministic and offline-safe until full CUA integration is enabled.
    """
    target_abs = _resolve_under_base(target_rel)
    os.makedirs(os.path.dirname(target_abs), exist_ok=True)

    # For MVP: if no CUA, just assemble a simple artifact that records the objective and seeds
    if not cua_available():
        content_lines = [
            f"Objective: {objective}",
            f"Generated: {dt.datetime.utcnow().isoformat()}Z",
        ]
        if seed_files:
            content_lines.append("\nSeed files:")
            for name, text in seed_files.items():
                # Save each seed under a sibling path
                seed_abs = _resolve_under_base(os.path.join(os.path.dirname(target_rel), name))
                os.makedirs(os.path.dirname(seed_abs), exist_ok=True)
                with open(seed_abs, "w", encoding="utf-8") as f:
                    f.write(text)
                content_lines.append(f"- {name} -> {os.path.relpath(seed_abs, AGENT_BASE_DIR)}")
        # Write target artifact (txt/markdown recommended for MVP)
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
        return {"used_cua": False, "path": target_abs}

    # Placeholder: CUA present — in future, call into the repo SDK (Python) to run the session
    with open(target_abs, "w", encoding="utf-8") as f:
        f.write(f"[CUA PLACEHOLDER]\nObjective: {objective}\nTimestamp: {dt.datetime.utcnow().isoformat()}Z\n")
    return {"used_cua": True, "path": target_abs}


def select_snap_assist_tile(name_tokens: list[str]) -> bool:
    """Select a Snap Assist tile matching provided tokens.

    Order of matching phases:
      1. specific tokens (likely document/file names)
      2. all tokens (specific + generic labels)
      3. relaxed generic fallback
    """
    global _cua_diag_last, _last_snap_success_ts
    logger = logging.getLogger(__name__)
    try:
        print(f"CUA: select_snap_assist_tile called with tokens={name_tokens}")
    except Exception:
        pass

    import os as _os_env
    VERBOSE = bool(_os_env.environ.get('CUA_DEBUG_VERBOSE'))

    # Hard timeout to prevent long scans (default 2000 ms, configurable)
    try:
        import time as _t_sel
        _timeout_ms = int(_os_env.environ.get('CUA_SNAP_SELECT_TIMEOUT_MS', '2000') or '2000')
    except Exception:
        # Fallback defaults
        import time as _t_sel  # type: ignore
        _timeout_ms = 2000
    _deadline = _t_sel.time() + max(0, _timeout_ms) / 1000.0

    def _timed_out() -> bool:
        try:
            return _t_sel.time() >= _deadline
        except Exception:
            return False

    # Debounce: if a snap+select just succeeded, ignore follow-up selection attempts briefly
    try:
        _debounce_ms = int(_os_env.environ.get('CUA_SNAP_DEBOUNCE_MS', '6000') or '6000')
    except Exception:
        _debounce_ms = 6000
    try:
        if _last_snap_success_ts and (_t_sel.time() - _last_snap_success_ts) < (max(0, _debounce_ms) / 1000.0):
            _cua_diag_last = {
                'matched': False,
                'reason': 'debounced_recent_success',
                'specific_tokens': [],
                'all_tokens': [],
            }
            return False
    except Exception:
        pass

    raw_tokens = [t for t in (name_tokens or []) if isinstance(t, str) and t.strip()]
    # Group generic labels by app family so we only include groups relevant to provided tokens
    generic_groups = {
        'word': {"word", "microsoft word", "ms word"},
        'code': {"visual studio code", "vs code", "vscode", "code"},
        'browser': {"chrome", "edge", "browser"},
    }
    generic_all = set()
    for _gset in generic_groups.values():
        generic_all.update(_gset)

    def _norm(s: str) -> str:
        try:
            import unicodedata as _ud
            s = _ud.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not _ud.combining(ch))
        except Exception:
            pass
        s = s.lower()
        # keep alnum and spaces
        import re as _re
        s = _re.sub(r"[^a-z0-9\s]+", " ", s)
        s = " ".join(s.split())
        return s
    specific: list[str] = []
    seen_lower = set()
    for t in raw_tokens:
        tl = _norm(t)
        if tl in seen_lower:
            continue
        seen_lower.add(tl)
        if tl not in generic_all and any(c.isalpha() for c in tl) and len(tl) > 2:
            specific.append(tl)
            if '.' in tl:
                stem = tl.split('.')[0]
                stem = stem.strip()
                if stem and _norm(stem) not in [s for s in specific] and stem not in generic_all:
                    specific.append(_norm(stem))
    # Include only generic groups that the caller hinted at via tokens
    hinted = set(_norm(x) for x in raw_tokens)
    include_groups = set()
    if hinted & generic_groups['word']:
        include_groups.add('word')
    if hinted & generic_groups['code']:
        include_groups.add('code')
    if hinted & generic_groups['browser']:
        include_groups.add('browser')
    # If no explicit hint, choose no generic group to avoid accidental matches (caller should include a hint like 'word')
    selected_generics = set()
    for g in include_groups:
        selected_generics.update(generic_groups[g])
    specific_tokens = list(dict.fromkeys(_norm(s) for s in specific))
    generic_tokens = [g for g in selected_generics if g not in specific_tokens]
    all_tokens = specific_tokens + [g for g in generic_tokens if g not in specific_tokens]
    if not all_tokens:
        all_tokens = ["word"]

    # Initialize COM first
    com_ok = _ensure_com_initialized()
    if not com_ok:
        _cua_diag_last = {
            'matched': False,
            'reason': 'com_init_failed',
            'specific_tokens': specific_tokens,
            'all_tokens': all_tokens,
        }
        return False
    # Initialize UIA
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
    except Exception as e:
        # One more attempt: re-init COM and retry once
        _ensure_com_initialized()
        try:
            from comtypes.client import GetModule, CreateObject  # type: ignore
            GetModule('UIAutomationCore.dll')
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
            automation = CreateObject(UIA.CUIAutomation)
        except Exception as e2:
            _cua_diag_last = {
                'matched': False,
                'reason': 'uia_init_failed',
                'exception': f"{str(e)[:120]} | retry: {str(e2)[:120]}",
                'specific_tokens': specific_tokens,
                'all_tokens': all_tokens,
            }
            return False

    # Small stabilization delay + optional extra from env
    try:
        import time as _t_init, os as _os_delay
        base_delay = 0.08
        extra_ms = int(_os_delay.environ.get('CUA_SNAP_EXTRA_DELAY_MS', '0') or '0')
        total = base_delay + max(0, extra_ms) / 1000.0
        _t_init.sleep(total)
    except Exception:
        pass

    import time as _t
    import ctypes as _ct
    VK_RIGHT = 0x27; VK_DOWN = 0x28; VK_RETURN = 0x0D; KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002; MOUSEEVENTF_LEFTUP = 0x0004

    def press(vk):
        try:
            _ct.windll.user32.keybd_event(vk, 0, 0, 0); _t.sleep(0.03)
            _ct.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.03)
        except Exception:
            pass

    def click_xy(x: int, y: int):
        try:
            _ct.windll.user32.SetCursorPos(int(x), int(y))
            _ct.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            _ct.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pass

    diag_attempts = []
    focus_changes = 0
    unique_names: list[str] = []

    phases: list[tuple[str, list[str], int]] = []
    # Dynamic max steps: allow a bit more time before declaring failure
    BASE_MAX = 20 if specific_tokens else 26
    MAX_STEPS = BASE_MAX
    if specific_tokens:
        phases.append(("specific", specific_tokens, MAX_STEPS))
    phases.append(("all", all_tokens, MAX_STEPS))

    # Track when a new unique name last appeared to detect repetition cycles
    last_new_unique_step = -1
    repetition_break_triggered = False

    for phase_name, phase_tokens, phase_limit in phases:
        last_name = None
        stagnate = 0
        for step in range(phase_limit):
            if _timed_out():
                _cua_diag_last = {
                    'matched': False,
                    'reason': 'timeout',
                    'phase': phase_name,
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return False
            try:
                elem = automation.GetFocusedElement()
            except Exception:
                elem = None
            name = ''
            try:
                if elem is not None:
                    name = (elem.CurrentName or '')
            except Exception:
                name = ''
            name_l = name.lower()
            if name != last_name:
                focus_changes += 1
                if name and name not in unique_names:
                    unique_names.append(name)
                    last_new_unique_step = step
            rect = None; pid = None; ctl_type = None
            try:
                if elem is not None:
                    rect_obj = getattr(elem, 'CurrentBoundingRectangle', None)
                    if rect_obj:
                        rect = [int(rect_obj.left), int(rect_obj.top), int(rect_obj.right), int(rect_obj.bottom)]
                    pid = getattr(elem, 'CurrentProcessId', None)
                    ctl_type = getattr(elem, 'CurrentControlType', None)
            except Exception:
                pass
            # Normalized contains check; when caller provides a small, specific token set (<=2), require ALL tokens to match
            nname = _norm(name)
            _ptoks = list(phase_tokens or [])
            if 0 < len(_ptoks) <= 2:
                matched = all(tok in nname for tok in _ptoks)
            else:
                matched = any(tok in nname for tok in _ptoks)
            attempt_rec = {
                'phase': phase_name,
                'step': step,
                'name': name,
                'matched': matched,
                'rect': rect,
                'pid': pid,
                'control_type': ctl_type,
                'tokens_used': phase_tokens,
            }
            diag_attempts.append(attempt_rec)
            if VERBOSE:
                try:
                    print(f"CUA_ATTEMPT: {attempt_rec}")
                except Exception:
                    pass
            if matched:
                # Prefer click if we have a rect
                if rect:
                    try:
                        cx = int((rect[0] + rect[2]) / 2)
                        cy = int((rect[1] + rect[3]) / 2)
                        click_xy(cx, cy)
                        method = 'click'
                    except Exception:
                        press(VK_RETURN); method = 'enter'
                else:
                    press(VK_RETURN); method = 'enter'
                _cua_diag_last = {
                    'matched': True,
                    'phase': phase_name,
                    'method': method,
                    'final_name': name,
                    'focus_changes': focus_changes,
                    'attempts': diag_attempts,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return True
            # Early repetition detection: if we have a very small stable set of tiles and no token matches, bail out.
            if not matched:
                small_set = 0 < len(unique_names) <= 3
                no_new_names_for = (step - last_new_unique_step) if last_new_unique_step >= 0 else step
                # If we seem to be cycling a tiny set without any token presence, bail from THIS PHASE only
                if step >= 8 and small_set and no_new_names_for >= 6:
                    joined_lower = _norm(" | ".join(unique_names))
                    any_token_present = any(tok in joined_lower for tok in (phase_tokens or []))
                    if not any_token_present:
                        repetition_break_triggered = True
                        # break out of current phase to try broader matching/relaxed paths
                        break

            # Move to next tile
            press(VK_RIGHT)
            _t.sleep(0.08)
            if _timed_out():
                _cua_diag_last = {
                    'matched': False,
                    'reason': 'timeout',
                    'phase': phase_name,
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return False
            if name == last_name:
                stagnate += 1
                if stagnate % 2 == 1:
                    press(VK_DOWN); _t.sleep(0.08)
                    if _timed_out():
                        _cua_diag_last = {
                            'matched': False,
                            'reason': 'timeout',
                            'phase': phase_name,
                            'attempts': diag_attempts,
                            'focus_changes': focus_changes,
                            'unique_names': unique_names,
                            'specific_tokens': specific_tokens,
                            'all_tokens': all_tokens,
                        }
                        return False
            else:
                stagnate = 0
            last_name = name

    # If zero focus changes -> UI absent
    if focus_changes == 0:
        _cua_diag_last = {
            'matched': False,
            'reason': 'snap_ui_absent',
            'attempts': diag_attempts,
            'focus_changes': focus_changes,
            'unique_names': unique_names,
            'specific_tokens': specific_tokens,
            'all_tokens': all_tokens,
        }
        return False

    # Relaxed pass (generic only)
    relaxed_tokens = [t for t in ("visual studio code", "vs code", "vscode", "code", "word", "chrome", "edge", "browser") if t in all_tokens]
    if relaxed_tokens:
        for rstep in range(10):
            if _timed_out():
                _cua_diag_last = {
                    'matched': False,
                    'reason': 'timeout',
                    'phase': 'relaxed',
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return False
            try:
                elem = automation.GetFocusedElement()
            except Exception:
                elem = None
            name = ''
            try:
                if elem is not None:
                    name = (elem.CurrentName or '')
            except Exception:
                name = ''
            if any(rt in _norm(name) for rt in relaxed_tokens):
                press(VK_RETURN)
                _cua_diag_last = {
                    'matched': True,
                    'relaxed': True,
                    'method': 'enter',
                    'phase': 'relaxed',
                    'final_name': name,
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return True
            press(VK_RIGHT); _t.sleep(0.07)
            if _timed_out():
                _cua_diag_last = {
                    'matched': False,
                    'reason': 'timeout',
                    'phase': 'relaxed',
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                }
                return False

    # Fallback BFS descendant search (direct tree walk) if focus-based traversal failed.
    bfs_candidates: list[dict] = []
    try:
        root = automation.GetRootElement()
    except Exception:
        root = None
    MAX_NODES = 800
    if root is not None:
        try:
            # We'll walk ControlView (broader) manually using GetFirstChildElement / GetNextSiblingElement.
            stack = [(root, 0)]
            visited = 0
            matched_elem = None; matched_name = ''
            tokens_list = list(all_tokens)
            token_set = set(tokens_list)
            while stack and visited < MAX_NODES and matched_elem is None:
                if _timed_out():
                    break
                elem, depth = stack.pop()
                visited += 1
                name = ''
                try:
                    name = (elem.CurrentName or '')
                except Exception:
                    name = ''
                low = name.lower()
                if name:
                    if name not in unique_names:
                        unique_names.append(name)
                    # For small, specific token sets (<=2), require ALL tokens to be present; else allow ANY
                    if (0 < len(tokens_list) <= 2 and all(tok in low for tok in tokens_list)) or \
                       (len(tokens_list) > 2 and any(tok in low for tok in token_set)):
                        matched_elem = elem
                        matched_name = name
                        break
                    if len(bfs_candidates) < 40:
                        # Capture sample for diagnostics
                        try:
                            rect_obj = getattr(elem, 'CurrentBoundingRectangle', None)
                            rect = None
                            if rect_obj:
                                rect = [int(rect_obj.left), int(rect_obj.top), int(rect_obj.right), int(rect_obj.bottom)]
                        except Exception:
                            rect = None
                        bfs_candidates.append({'name': name, 'depth': depth, 'rect': rect})
                # Push children
                try:
                    child = elem.GetFirstChildElement()
                except Exception:
                    child = None
                children = []
                while child is not None and len(children) < 50:  # limit siblings per node to avoid explosion
                    children.append(child)
                    try:
                        child = child.GetNextSiblingElement()
                    except Exception:
                        break
                # Reverse to maintain left-to-right order when using stack (depth-first)
                for c in reversed(children):
                    stack.append((c, depth + 1))
            if matched_elem is not None:
                # Try click by rect, else Enter
                method = 'enter'
                try:
                    rect_obj = getattr(matched_elem, 'CurrentBoundingRectangle', None)
                    if rect_obj:
                        cx = int((rect_obj.left + rect_obj.right) / 2)
                        cy = int((rect_obj.top + rect_obj.bottom) / 2)
                        click_xy(cx, cy)
                        method = 'bfs_click'
                except Exception:
                    press(VK_RETURN)
                _cua_diag_last = {
                    'matched': True,
                    'method': method,
                    'phase': 'bfs_fallback',
                    'final_name': matched_name,
                    'attempts': diag_attempts,
                    'focus_changes': focus_changes,
                    'unique_names': unique_names,
                    'specific_tokens': specific_tokens,
                    'all_tokens': all_tokens,
                    'bfs_visited': visited,
                    'bfs_sample': bfs_candidates,
                }
                return True
            else:
                reason = 'timeout' if _timed_out() else 'no_match_in_bfs'
                diag_attempts.append({'phase': 'bfs_fallback', 'step': 0, 'name': '', 'matched': False, 'info': reason})
        except Exception as _bfs_e:
            diag_attempts.append({'phase': 'bfs_fallback', 'step': -1, 'name': '', 'matched': False, 'exception': str(_bfs_e)[:160]})

    _cua_diag_last = {
        'matched': False,
        'reason': 'tokens_not_found',
        'attempts': diag_attempts,
        'focus_changes': focus_changes,
        'unique_names': unique_names,
        'specific_tokens': specific_tokens,
        'all_tokens': all_tokens,
        'bfs_sample': bfs_candidates,
    }
    return False


# -------------------------- New CUA convenience API --------------------------
def trigger_snap(side: str) -> bool:
    """Trigger OS snap assist by sending Win+Arrow to the current foreground window.

    side: 'left' or 'right'
    Returns True if the key sequence was sent without exception.
    Note: This is still a UI action but kept inside the CUA adapter per user spec.
    """
    try:
        import ctypes as _ct, time as _t
        VK_LEFT = 0x25; VK_RIGHT = 0x27; KEYEVENTF_KEYUP = 0x0002
        vk = VK_RIGHT if str(side).lower() == 'right' else VK_LEFT

        # Press Win+Arrow using SendInput-like sequence
        # Using keybd_event for simplicity and parity with existing code above
        VK_LWIN = 0x5B
        _ct.windll.user32.keybd_event(VK_LWIN, 0, 0, 0); _t.sleep(0.02)
        _ct.windll.user32.keybd_event(vk, 0, 0, 0); _t.sleep(0.03)
        _ct.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.02)
        return True
    except Exception:
        return False


def snap_current_and_select(tokens: list[str], snap_side: str = 'right') -> Dict[str, Any]:
    """Snap the current foreground window to a side, then attempt to select a Snap Assist tile.

    Returns a dict with attempted/selected info and last diagnostics (if available).
    """
    global _cua_diag_last, _last_snap_success_ts
    # Debounce: if we recently completed a snap+select successfully, skip any new attempt
    try:
        import time as _t_deb, os as _os_deb
        debounce_ms = int(_os_deb.environ.get('CUA_SNAP_DEBOUNCE_MS', '6000') or '6000')
        if _last_snap_success_ts and (_t_deb.time() - _last_snap_success_ts) < (max(0, debounce_ms) / 1000.0):
            diag = _cua_diag_last if isinstance(_cua_diag_last, dict) else None
            return {
                'snap_sent': False,
                'selected': False,
                'tokens': tokens,
                'side': snap_side,
                'diagnostics': diag,
                'error': None,
                'verified': False,
                'debounced': True,
            }
    except Exception:
        pass
    ok = trigger_snap(snap_side)
    sel = False
    reason = None
    verified = False
    verify_reason = None

    def _get_foreground_rect():
        try:
            import ctypes as _ct
            user32 = _ct.windll.user32
            hwnd = user32.GetForegroundWindow()
            rect = _ct.wintypes.RECT()
            if user32.GetWindowRect(hwnd, _ct.byref(rect)):
                return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        except Exception:
            return None
        return None

    def _get_screen_size():
        try:
            import ctypes as _ct
            SM_CXSCREEN = 0; SM_CYSCREEN = 1
            w = _ct.windll.user32.GetSystemMetrics(SM_CXSCREEN)
            h = _ct.windll.user32.GetSystemMetrics(SM_CYSCREEN)
            return (int(w), int(h))
        except Exception:
            return None

    def _is_current_window_snapped(expected_side: str) -> tuple[bool, str | None]:
        rect = _get_foreground_rect()
        scr = _get_screen_size()
        if not rect or not scr:
            return (False, 'no_rect_or_screen')
        x1, y1, x2, y2 = rect
        w = max(1, x2 - x1)
        sw, sh = scr
        if sw <= 0:
            return (False, 'invalid_screen')
        ratio = w / float(sw)
        # Expect roughly half width when snapped (40–60%)
        halfish = 0.4 <= ratio <= 0.6
        if not halfish:
            return (False, f'ratio_off:{ratio:.2f}')
        mid = sw // 2
        rightish = x1 >= (mid - int(0.1 * sw))
        leftish = x2 <= (mid + int(0.1 * sw))
        if expected_side.lower() == 'right' and rightish:
            return (True, None)
        if expected_side.lower() == 'left' and leftish:
            return (True, None)
        return (False, 'side_mismatch')

    if ok:
        try:
            sel = bool(select_snap_assist_tile(tokens))
        except Exception as e:
            reason = str(e)
        # Do not re-trigger snap on verification failure; avoid late overrides
        try:
            verified, verify_reason = _is_current_window_snapped(snap_side)
        except Exception:
            verified, verify_reason = (False, None)
    # Update debounce marker on any selection success
    if sel:
        try:
            import time as _t_mark
            _last_snap_success_ts = _t_mark.time()
        except Exception:
            pass
    diag = _cua_diag_last if isinstance(_cua_diag_last, dict) else None
    out = {
        'snap_sent': bool(ok),
        'selected': bool(sel),
        'tokens': tokens,
        'side': snap_side,
        'diagnostics': diag,
        'error': reason,
        'verified': bool(verified),
    }
    if not verified and verify_reason:
        out['verify_reason'] = verify_reason
    return out


def open_path(path: str) -> Dict[str, Any]:
    """Open a file using the OS default association (Windows only).

    Returns {ok, launched, path}. This is not deep automation; it complements CUA flows.
    """
    p = os.path.abspath(os.path.expanduser(path or ''))
    if not os.path.isfile(p):
        return {'ok': False, 'launched': False, 'path': p, 'error': 'path_not_found'}
    if os.name != 'nt':
        return {'ok': False, 'launched': False, 'path': p, 'error': 'windows_only'}
    try:
        os.startfile(p)  # type: ignore[attr-defined]
        return {'ok': True, 'launched': True, 'path': p}
    except Exception as e:
        return {'ok': False, 'launched': False, 'path': p, 'error': f'launch_failed: {e}'}


def open_vscode(path: Optional[str] = None, new_window: bool = False) -> Dict[str, Any]:
    """Launch VS Code optionally opening a path. Minimal, best-effort.

    Prefers 'code' on PATH; otherwise falls back to os.startfile on a file.
    """
    try:
        import shutil as _sh, subprocess as _sp
        cmd = _sh.which('code')
        args = []
        if cmd:
            if path:
                if new_window:
                    args = [cmd, '--new-window', path]
                else:
                    args = [cmd, path]
            else:
                args = [cmd]
            _sp.Popen(args, shell=False)
            return {'ok': True, 'launched': True, 'path': path, 'command': args}
        # Fallback: open file via OS association (may still open in Code if default)
        if path and os.path.exists(path) and os.name == 'nt':
            os.startfile(path)  # type: ignore[attr-defined]
            return {'ok': True, 'launched': True, 'path': path, 'command': None}
        return {'ok': False, 'launched': False, 'path': path, 'error': 'code_not_found'}
    except Exception as e:  # pragma: no cover
        return {'ok': False, 'launched': False, 'path': path, 'error': str(e)}


def open_path_background(path: str) -> Dict[str, Any]:
    """Open a file via ShellExecuteEx without activating the new window (best-effort).

    Uses SW_SHOWNOACTIVATE so the current foreground window remains active.
    Returns {ok, launched, path} and does not wait for the process to exit.
    """
    p = os.path.abspath(os.path.expanduser(path or ''))
    if not os.path.isfile(p):
        return {'ok': False, 'launched': False, 'path': p, 'error': 'path_not_found'}
    if os.name != 'nt':
        return {'ok': False, 'launched': False, 'path': p, 'error': 'windows_only'}
    try:
        import ctypes as _ct
        from ctypes import wintypes as _wt

        class SHELLEXECUTEINFOW(_ct.Structure):
            _fields_ = [
                ('cbSize', _wt.DWORD),
                ('fMask', _wt.ULONG),
                ('hwnd', _wt.HWND),
                ('lpVerb', _wt.LPCWSTR),
                ('lpFile', _wt.LPCWSTR),
                ('lpParameters', _wt.LPCWSTR),
                ('lpDirectory', _wt.LPCWSTR),
                ('nShow', _wt.INT),
                ('hInstApp', _wt.HINSTANCE),
                ('lpIDList', _wt.LPVOID),
                ('lpClass', _wt.LPCWSTR),
                ('hkeyClass', _wt.HKEY),
                ('dwHotKey', _wt.DWORD),
                ('hIcon', _wt.HANDLE),  # part of union
                ('hProcess', _wt.HANDLE),
            ]

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SEE_MASK_FLAG_NO_UI = 0x00000400
        SW_SHOWNOACTIVATE = 4

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = _ct.sizeof(SHELLEXECUTEINFOW)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI
        sei.hwnd = None
        sei.lpVerb = None
        sei.lpFile = p
        sei.lpParameters = None
        sei.lpDirectory = None
        sei.nShow = SW_SHOWNOACTIVATE
        sei.hInstApp = None
        sei.lpIDList = None
        sei.lpClass = None
        sei.hkeyClass = None
        sei.dwHotKey = 0
        sei.hIcon = None
        sei.hProcess = None

        ok = _ct.windll.shell32.ShellExecuteExW(_ct.byref(sei))
        if not ok:
            return {'ok': False, 'launched': False, 'path': p, 'error': 'ShellExecuteExW_failed'}
        # We won't keep the handle open
        try:
            if sei.hProcess:
                _ct.windll.kernel32.CloseHandle(sei.hProcess)
        except Exception:
            pass
        return {'ok': True, 'launched': True, 'path': p}
    except Exception as e:
        return {'ok': False, 'launched': False, 'path': p, 'error': f'background_launch_failed: {e}'}


def open_browser_to_path(path: str, new_window: bool = False) -> Dict[str, Any]:
    """Open a file (e.g., .html) in a preferred browser.

    Preference order: Google Chrome, Microsoft Edge, Mozilla Firefox, Brave.
    Falls back to os.startfile.
    Returns {ok, launched, path, browser}.
    """
    p = os.path.abspath(os.path.expanduser(path or ''))
    if not os.path.isfile(p):
        return {'ok': False, 'launched': False, 'path': p, 'error': 'path_not_found'}
    url = p
    try:
        # Use file:// URL for browsers
        if not p.lower().startswith(('http://', 'https://', 'file://')):
            url = 'file://' + p.replace('\\', '/')
    except Exception:
        url = p
    try:
        import shutil as _sh, subprocess as _sp, os as _os
        def _try_launch(cmd_path: str, name: str) -> bool:
            try:
                args = [cmd_path]
                if new_window:
                    if name in ('chrome', 'edge', 'brave'):
                        args.append('--new-window')
                    elif name == 'firefox':
                        args.append('-new-window')
                args.append(url)
                _sp.Popen(args, shell=False)
                return True
            except Exception:
                return False
        # Prefer Microsoft Edge (Bing) first as requested
        order = [
            ('msedge', 'edge'),
            ('chrome', 'chrome'),
            ('firefox', 'firefox'),
            ('brave', 'brave'),
        ]
        # Known install paths for common browsers (when not on PATH)
        known_paths = {
            'edge': [
                r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            ],
            'chrome': [
                r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            ],
            'firefox': [
                r"C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                r"C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
            ],
            'brave': [
                r"C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                r"C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            ],
        }
        for exe, name in order:
            cmd = _sh.which(exe)
            if cmd and _try_launch(cmd, name):
                return {'ok': True, 'launched': True, 'path': p, 'browser': name}
            # Try known install paths
            for kp in known_paths.get(name, []):
                kp_exp = _os.path.expandvars(kp)
                if _os.path.isfile(kp_exp) and _try_launch(kp_exp, name):
                    return {'ok': True, 'launched': True, 'path': p, 'browser': name}
        # Fallback: OS default
        if os.name == 'nt':
            os.startfile(p)  # type: ignore[attr-defined]
            return {'ok': True, 'launched': True, 'path': p, 'browser': 'default'}
        return {'ok': False, 'launched': False, 'path': p, 'error': 'no_browser_found'}
    except Exception as e:
        return {'ok': False, 'launched': False, 'path': p, 'error': f'browser_launch_failed: {e}'}


def enumerate_snap_focus_cycle(max_steps: int = 40, include_rect: bool = True) -> dict:
    """Enumerate the current Snap Assist focus cycle (requires Snap UI to be open already).

    Walks focus with RIGHT (and periodic DOWN) capturing element names and metadata without activating any tile.
    Returns diagnostics dictionary similar to _cua_diag_last but never selects a tile.
    """
    out = {
        'attempts': [],
        'focus_changes': 0,
        'unique_names': [],
        'steps': max_steps,
        'reason': None,
    }
    if not _ensure_com_initialized():
        out['reason'] = 'com_init_failed'
        return out
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
    except Exception as e:
        out['reason'] = f'uia_init_failed: {e}'
        return out
    import time as _t
    import ctypes as _ct
    VK_RIGHT = 0x27; VK_DOWN = 0x28; KEYEVENTF_KEYUP = 0x0002
    def press(vk):
        try:
            _ct.windll.user32.keybd_event(vk, 0, 0, 0); _t.sleep(0.03)
            _ct.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.03)
        except Exception:
            pass
    last = None; stagnate = 0
    for step in range(max_steps):
        try:
            elem = automation.GetFocusedElement()
        except Exception:
            elem = None
        name = ''
        try:
            if elem is not None:
                name = (elem.CurrentName or '')
        except Exception:
            name = ''
        if name != last:
            out['focus_changes'] += 1
            if name and name not in out['unique_names']:
                out['unique_names'].append(name)
        rect = None; pid = None; ctl_type = None
        try:
            if elem is not None:
                rect_obj = getattr(elem, 'CurrentBoundingRectangle', None)
                if rect_obj and include_rect:
                    rect = [int(rect_obj.left), int(rect_obj.top), int(rect_obj.right), int(rect_obj.bottom)]
                pid = getattr(elem, 'CurrentProcessId', None)
                ctl_type = getattr(elem, 'CurrentControlType', None)
        except Exception:
            pass
        out['attempts'].append({
            'step': step,
            'name': name,
            'rect': rect,
            'pid': pid,
            'control_type': ctl_type,
        })
        press(VK_RIGHT)
        _t.sleep(0.05)
        if name == last:
            stagnate += 1
            if stagnate % 2 == 1:
                press(VK_DOWN)
                _t.sleep(0.05)
        else:
            stagnate = 0
        last = name
    out['reason'] = 'completed'
    return out


def _resolve_under_base(path_like: str) -> str:
    p = path_like
    if not os.path.isabs(p):
        p = os.path.join(AGENT_BASE_DIR, p)
    p = os.path.abspath(p)
    base = os.path.abspath(AGENT_BASE_DIR)
    if os.path.commonpath([p, base]) != base:
        raise ValueError("Target path outside agent base directory")
    return p


# -------------- Optional helpers to improve launch→snap sequencing --------------
def get_focused_window_name() -> str:
    """Return the CurrentName of the focused UIA element, or empty string."""
    if not _ensure_com_initialized():
        return ''
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
        elem = automation.GetFocusedElement()
        name = ''
        try:
            if elem is not None:
                name = (elem.CurrentName or '')
        except Exception:
            name = ''
        return name
    except Exception:
        return ''


def wait_for_focus(tokens: list[str], timeout_ms: int = 700) -> bool:
    """Wait briefly until the focused window name contains any of the tokens (normalized).

    Helps when app launch is slightly delayed relative to snap actions.
    """
    import time as _t
    end = _t.time() + max(0, timeout_ms) / 1000.0
    def _norm(s: str) -> str:
        try:
            import unicodedata as _ud
            s = _ud.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not _ud.combining(ch))
        except Exception:
            pass
        s = s.lower()
        import re as _re
        s = _re.sub(r"[^a-z0-9\s]+", " ", s)
        s = " ".join(s.split())
        return s
    toks = [_norm(t) for t in (tokens or []) if t]
    if not toks:
        return False
    while _t.time() < end:
        name = get_focused_window_name()
        nname = _norm(name)
        if any(tok in nname for tok in toks):
            return True
        _t.sleep(0.05)
    return False


def focus_previous_window(delay_ms: int = 80) -> bool:
    """Bring focus back to the previously active window using Alt+Tab once.

    Useful after launching a new app (which steals focus) to return to our app
    before snapping so our app becomes the snapped window.
    """
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        VK_MENU = 0x12  # Alt
        VK_TAB = 0x09
        _ct.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(max(0, delay_ms) / 1000.0)
        _ct.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.02)
        return True
    except Exception:
        return False


def focus_window_by_tokens(tokens: list[str], max_nodes: int = 1000) -> bool:
    """Find a top-level window whose name contains any of the tokens (normalized) and set focus.

    More deterministic than Alt+Tab for returning to a known app like Chrome.
    """
    if not _ensure_com_initialized():
        return False
    def _norm(s: str) -> str:
        try:
            import unicodedata as _ud
            s = _ud.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not _ud.combining(ch))
        except Exception:
            pass
        s = s.lower()
        import re as _re
        s = _re.sub(r"[^a-z0-9\s]+", " ", s)
        s = " ".join(s.split())
        return s
    toks = set(_norm(t) for t in (tokens or []) if t)
    if not toks:
        return False
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
        root = automation.GetRootElement()
        if root is None:
            return False
        stack = [(root, 0)]
        visited = 0
        while stack and visited < max_nodes:
            elem, depth = stack.pop()
            visited += 1
            name = ''
            try:
                name = (elem.CurrentName or '')
            except Exception:
                name = ''
            if name:
                if any(t in _norm(name) for t in toks):
                    try:
                        elem.SetFocus()
                        return True
                    except Exception:
                        return False
            # Walk children (ControlView)
            try:
                child = elem.GetFirstChildElement()
            except Exception:
                child = None
            children = []
            # Limit siblings per node for safety
            while child is not None and len(children) < 50:
                children.append(child)
                try:
                    child = child.GetNextSiblingElement()
                except Exception:
                    break
            for c in reversed(children):
                stack.append((c, depth + 1))
        return False
    except Exception:
        return False


def focus_window_by_tokens_top(tokens: list[str]) -> bool:
    """Focus a top-level window by title using EnumWindows; more reliable than deep UIA walks.

    Returns True if a visible window matching tokens is found and brought to foreground.
    """
    if os.name != 'nt':
        return False
    toks = [_norm_token(t) for t in (tokens or []) if t]
    if not toks:
        return False
    try:
        import ctypes as _ct
        from ctypes import wintypes as _wt
        user32 = _ct.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = _ct.WINFUNCTYPE(_wt.BOOL, _wt.HWND, _wt.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible
        SetForegroundWindow = user32.SetForegroundWindow
        ShowWindow = user32.ShowWindow
        SW_RESTORE = 9
        found = _ct.c_int(0)
        best = _ct.c_void_p()
        def callback(hwnd, lParam):
            try:
                if not IsWindowVisible(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = _ct.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value or ''
                n = _norm_token(title)
                if n and any(t in n for t in toks):
                    best.value = hwnd
                    found.value = 1
                    return False
            except Exception:
                return True
            return True
        EnumWindows(EnumWindowsProc(callback), 0)
        if found.value and best.value:
            hwnd = int(_ct.cast(best, _ct.c_void_p).value or 0)
            if hwnd:
                ShowWindow(hwnd, SW_RESTORE)
                _ct.windll.user32.SetForegroundWindow(hwnd)
                return True
        return False
    except Exception:
        return False


def ensure_focus_top(tokens: list[str], attempts: int = 3, verify_timeout_ms: int = 600) -> bool:
    """Try focusing via top-level EnumWindows, verify with UIA-focused name."""
    import time as _t
    ok = False
    for _ in range(max(1, attempts)):
        try:
            ok = focus_window_by_tokens_top(tokens)
        except Exception:
            ok = False
        # verify
        end = _t.time() + max(0, verify_timeout_ms) / 1000.0
        while _t.time() < end:
            name = get_focused_window_name()
            if any(_norm_token(t) in _norm_token(name) for t in (tokens or [])):
                return True
            _t.sleep(0.05)
        _t.sleep(0.1)
    return False


def wait_for_window_appearance(tokens: list[str], timeout_ms: int = 2000, max_nodes_per_scan: int = 1200) -> bool:
    """Poll UIA until any window/control name contains one of the tokens (normalized).

    Does not change focus; safe to use after background launch to ensure the app window exists
    before triggering Snap Assist. Returns True if found within timeout.
    """
    if not _ensure_com_initialized():
        return False
    def _norm(s: str) -> str:
        try:
            import unicodedata as _ud
            s = _ud.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not _ud.combining(ch))
        except Exception:
            pass
        s = s.lower()
        import re as _re
        s = _re.sub(r"[^a-z0-9\s]+", " ", s)
        s = " ".join(s.split())
        return s
    # Allow environment to extend the watch tokens
    import os as _os
    extra_env = _os.environ.get('CUA_WORD_APPEAR_TOKENS', '')
    extra_toks = []
    if extra_env:
        extra_toks = [s.strip() for s in extra_env.split(';') if s.strip()]
    toks = set(_norm(t) for t in ((tokens or []) + extra_toks) if t)
    # Allow environment to override/increase timeout
    try:
        env_to = int(_os.environ.get('CUA_WORD_APPEAR_TIMEOUT_MS', '0') or '0')
        if env_to and env_to > timeout_ms:
            timeout_ms = env_to
    except Exception:
        pass
    if not toks:
        return False
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
    except Exception:
        return False
    import time as _t
    end = _t.time() + max(0, timeout_ms) / 1000.0
    while _t.time() < end:
        try:
            root = automation.GetRootElement()
        except Exception:
            root = None
        if root is None:
            _t.sleep(0.05)
            continue
        # BFS scan with node cap
        try:
            stack = [root]
            visited = 0
            while stack and visited < max_nodes_per_scan:
                elem = stack.pop()
                visited += 1
                name = ''
                try:
                    name = (elem.CurrentName or '')
                except Exception:
                    name = ''
                if name:
                    n = _norm(name)
                    if any(t in n for t in toks):
                        return True
                # Push children (limit breadth)
                try:
                    child = elem.GetFirstChildElement()
                except Exception:
                    child = None
                c = []
                while child is not None and len(c) < 50:
                    c.append(child)
                    try:
                        child = child.GetNextSiblingElement()
                    except Exception:
                        break
                for ch in c:
                    stack.append(ch)
        except Exception:
            pass
        _t.sleep(0.06)
    return False


def ensure_focus(tokens: list[str], attempts: int = 3, verify_timeout_ms: int = 600, env_token_var: str = 'CUA_APP_FOCUS_TOKENS') -> bool:
    """Try to bring a window matching tokens to foreground and verify it holds focus.

    - Optionally extends tokens from environment variable (semicolon-separated)
    - Verifies with get_focused_window_name()
    - Retries a few times with short delays
    Returns True if focus appears to match.
    """
    import time as _t
    import os as _os
    def _norm(s: str) -> str:
        try:
            import unicodedata as _ud
            s = _ud.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not _ud.combining(ch))
        except Exception:
            pass
        s = s.lower()
        import re as _re
        s = _re.sub(r"[^a-z0-9\s]+", " ", s)
        s = " ".join(s.split())
        return s
    base = list(tokens or [])
    extra = _os.environ.get(env_token_var, '')
    if extra:
        base += [s.strip() for s in extra.split(';') if s.strip()]
    norm_toks = [_norm(t) for t in base if t]
    if not norm_toks:
        return False
    ok = False
    for i in range(max(1, attempts)):
        try:
            focus_window_by_tokens(base)  # best-effort
        except Exception:
            pass
        # verify
        end = _t.time() + max(0, verify_timeout_ms) / 1000.0
        while _t.time() < end:
            name = get_focused_window_name()
            if any(t in _norm(name) for t in norm_toks):
                ok = True
                break
            _t.sleep(0.05)
        if ok:
            break
        # small pause before next attempt
        _t.sleep(0.1)
    return ok


# --------------------- Basic clipboard + paste automation ---------------------
def _set_clipboard_text(text: str) -> bool:
    """Set Unicode text to the Windows clipboard using ctypes only.

    Returns True on success. Best-effort with a couple of retries if the clipboard is busy.
    """
    if os.name != 'nt':
        return False
    import ctypes as _ct
    from ctypes import wintypes as _wt
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    # Prepare UTF-16-LE bytes (including terminating NUL)
    try:
        data = (text or '').encode('utf-16le') + b"\x00\x00"
    except Exception:
        return False

    user32 = _ct.windll.user32
    kernel32 = _ct.windll.kernel32

    def _try_once() -> bool:
        if not user32.OpenClipboard(None):
            return False
        try:
            if not user32.EmptyClipboard():
                return False
            h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_global:
                return False
            locked = kernel32.GlobalLock(h_global)
            if not locked:
                kernel32.GlobalFree(h_global)
                return False
            try:
                _ct.memmove(locked, data, len(data))
            finally:
                kernel32.GlobalUnlock(h_global)
            if not user32.SetClipboardData(CF_UNICODETEXT, h_global):
                kernel32.GlobalFree(h_global)
                return False
            # Ownership of h_global has been transferred to the clipboard
            return True
        finally:
            user32.CloseClipboard()

    # Try up to 3 times in case clipboard is temporarily busy
    try:
        import time as _t
        for _ in range(3):
            if _try_once():
                return True
            _t.sleep(0.05)
    except Exception:
        return False
    return False


def _send_ctrl_v() -> bool:
    """Simulate Ctrl+V using keybd_event. Returns True if no exception occurs."""
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        VK_V = 0x56
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(VK_V, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        return True
    except Exception:
        return False


def _send_ctrl_c() -> bool:
    """Simulate Ctrl+C to copy current selection. Returns True if keys were sent."""
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        VK_C = 0x43
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(VK_C, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        return True
    except Exception:
        return False


def _get_clipboard_text() -> str | None:
    """Read Unicode text from the Windows clipboard. Returns None on failure or if empty."""
    if os.name != 'nt':
        return None
    try:
        import ctypes as _ct
        from ctypes import wintypes as _wt
        CF_UNICODETEXT = 13
        user32 = _ct.windll.user32
        kernel32 = _ct.windll.kernel32
        if not user32.OpenClipboard(None):
            return None
        try:
            h_data = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_data:
                return None
            ptr = kernel32.GlobalLock(h_data)
            if not ptr:
                return None
            try:
                data = _ct.wstring_at(ptr)
                return data if data else None
            finally:
                kernel32.GlobalUnlock(h_data)
        finally:
            user32.CloseClipboard()
    except Exception:
        return None

def _send_ctrl_key(vk_key: int) -> bool:
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(vk_key, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(vk_key, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        _ct.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        return True
    except Exception:
        return False

def _send_key(vk_key: int) -> bool:
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        _ct.windll.user32.keybd_event(vk_key, 0, 0, 0)
        _t.sleep(0.02)
        _ct.windll.user32.keybd_event(vk_key, 0, KEYEVENTF_KEYUP, 0)
        _t.sleep(0.01)
        return True
    except Exception:
        return False

def capture_full_document_text_and_restore_selection(original_preview: str | None = None, max_chars: int = 200000) -> dict:
    """Capture entire document text from the foreground app (e.g., Word) and attempt to restore selection.

    Steps:
    - Save clipboard
    - Ctrl+A, Ctrl+C => doc_text
    - If original_preview provided, try to reselect via Ctrl+F -> paste -> Enter -> Esc
    - Restore clipboard
    Returns { ok, text, restored, errors }
    """
    import time as _t
    errors: list[str] = []
    try:
        prior = _get_clipboard_text()
    except Exception as e:
        errors.append(f"clipboard_read_failed:{str(e)[:80]}")
        prior = None
    # Ctrl+A
    try:
        VK_A = 0x41
        _ = _send_ctrl_key(VK_A)
        _t.sleep(0.05)
    except Exception:
        errors.append('ctrl_a_failed')
    # Ctrl+C
    try:
        _ = _send_ctrl_c()
        _t.sleep(0.08)
    except Exception:
        errors.append('ctrl_c_failed')
    doc_text = _get_clipboard_text() or ''
    if doc_text and max_chars and len(doc_text) > max_chars:
        doc_text = doc_text[:max_chars]
    # Try to reselect original preview
    restored = False
    try:
        if (original_preview or '').strip():
            # Ctrl+F
            VK_F = 0x46; VK_RETURN = 0x0D; VK_ESCAPE = 0x1B
            _send_ctrl_key(VK_F); _t.sleep(0.08)
            # Paste the original preview into the Find box
            _set_clipboard_text(original_preview or '')
            _t.sleep(0.02)
            _send_ctrl_v(); _t.sleep(0.06)
            # Enter to search, then Esc to close pane
            _send_key(VK_RETURN); _t.sleep(0.1)
            _send_key(VK_ESCAPE); _t.sleep(0.05)
            restored = True
    except Exception:
        restored = False
    # Restore clipboard
    try:
        if prior is not None:
            _set_clipboard_text(prior)
    except Exception:
        pass
    return {
        'ok': True,
        'text': doc_text,
        'restored': bool(restored),
        'errors': errors,
    }

def capture_inline_selection(max_preview_chars: int = 1200) -> dict:
    """Best-effort capture of current selection text from the foreground app.

    Strategy:
    - Record current clipboard text (Unicode), if any
    - Send Ctrl+C to copy
    - Read clipboard text; if non-empty, treat as selection
    - Restore prior clipboard text (Unicode only) to minimize disruption
    Returns dict with {ok, selections: [{source, label, preview, length, timestamp}], primary}
    """
    import time as _t
    errors: list[str] = []
    try:
        prior = _get_clipboard_text()
    except Exception as e:
        prior = None
        errors.append(f"clipboard_read_failed:{str(e)[:80]}")
    sent = _send_ctrl_c()
    _t.sleep(0.06)
    sel_text = _get_clipboard_text() or ''
    # Restore clipboard to prior state (Unicode only)
    try:
        if prior is not None:
            _set_clipboard_text(prior)
    except Exception:
        pass
    focused_name = ''
    try:
        focused_name = get_focused_window_name()
    except Exception:
        focused_name = ''
    preview = (sel_text or '').strip()
    if preview and len(preview) > max_preview_chars:
        preview = preview[:max_preview_chars]
    ts = int(_t.time())
    out: dict = {
        'ok': True,
        'errors': errors,
        'selections': [],
        'primary': 'foreground',
    }
    if preview:
        out['selections'] = [{
            'source': 'foreground',
            'label': focused_name or 'Target',
            'preview': preview,
            'length': len(sel_text or ''),
            'timestamp': ts,
        }]
    return out

def get_clipboard_text_preview(max_preview_chars: int = 1200) -> dict:
    """Active selection capture: sends Ctrl+C to grab current selection, then restores clipboard.

    Does not change focus, but DOES send Ctrl+C to copy whatever is currently selected
    in the foreground app, then restores the prior clipboard content.
    Returns dict with the same shape as capture_inline_selection but with primary 'clipboard'.
    """
    import time as _t
    errors: list[str] = []
    # Save prior clipboard
    try:
        prior = _get_clipboard_text()
    except Exception as e:
        prior = None
        errors.append(f"clipboard_save_failed:{str(e)[:80]}")
    
    # Send Ctrl+C to copy current selection (without changing focus)
    sent = _send_ctrl_c()
    _t.sleep(0.06)
    
    # Read clipboard
    try:
        clip = _get_clipboard_text() or ''
    except Exception as e:
        clip = ''
        errors.append(f"clipboard_read_failed:{str(e)[:80]}")
    
    # Restore prior clipboard
    try:
        if prior is not None:
            _set_clipboard_text(prior)
    except Exception as e:
        errors.append(f"clipboard_restore_failed:{str(e)[:80]}")
    
    # Determine source from focused window name
    focused_name = ''
    try:
        focused_name = get_focused_window_name()
    except Exception:
        focused_name = ''
    
    preview = (clip or '').strip()
    if preview and len(preview) > max_preview_chars:
        preview = preview[:max_preview_chars]
    ts = int(_t.time())
    out: dict = {
        'ok': True,
        'errors': errors,
        'selections': [],
        'primary': 'foreground',
    }
    if preview:
        out['selections'] = [{
            'source': 'foreground',
            'label': focused_name or 'Target',
            'preview': preview,
            'length': len(clip or ''),
            'timestamp': ts,
        }]
    return out

def _click_center_of_foreground(dx: int = 0, dy: int = 0) -> bool:
    """Click approximately the center of the current foreground window (best-effort)."""
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct
        import time as _t
        user32 = _ct.windll.user32
        rect = _ct.wintypes.RECT()
        hwnd = user32.GetForegroundWindow()
        if not hwnd or not user32.GetWindowRect(hwnd, _ct.byref(rect)):
            return False
        cx = int((rect.left + rect.right) / 2) + int(dx)
        cy = int((rect.top + rect.bottom) / 2) + int(dy)
        user32.SetCursorPos(cx, cy)
        _t.sleep(0.01)
        user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        _t.sleep(0.01)
        return True
    except Exception:
        return False


def _set_clipboard_rtf(rtf: str, plain_fallback: str | None = None) -> bool:
    """Set Rich Text (RTF) and optional Unicode plain-text fallback to the clipboard.

    Returns True on success. Uses RegisterClipboardFormatW("Rich Text Format").
    """
    if os.name != 'nt':
        return False
    import ctypes as _ct
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    try:
        rtf_bytes = (rtf or '').encode('utf-8')  # RTF is ASCII/ANSI-safe; utf-8 works for Word
    except Exception:
        return False
    if plain_fallback is None:
        plain_fallback = ''
    plain_bytes = (plain_fallback or '').encode('utf-16le') + b"\x00\x00"

    user32 = _ct.windll.user32
    kernel32 = _ct.windll.kernel32
    # Register RTF clipboard format
    RegisterClipboardFormatW = user32.RegisterClipboardFormatW
    RegisterClipboardFormatW.restype = _ct.wintypes.UINT  # type: ignore[attr-defined]
    fmt_rtf = RegisterClipboardFormatW("Rich Text Format")
    if not fmt_rtf:
        return False

    if not user32.OpenClipboard(None):
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        # RTF block
        h_rtf = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(rtf_bytes))
        if not h_rtf:
            return False
        ptr = kernel32.GlobalLock(h_rtf)
        if not ptr:
            kernel32.GlobalFree(h_rtf)
            return False
        try:
            _ct.memmove(ptr, rtf_bytes, len(rtf_bytes))
        finally:
            kernel32.GlobalUnlock(h_rtf)
        if not user32.SetClipboardData(fmt_rtf, h_rtf):
            kernel32.GlobalFree(h_rtf)
            return False
        # Plain Unicode fallback
        h_txt = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(plain_bytes))
        if not h_txt:
            return False
        ptr2 = kernel32.GlobalLock(h_txt)
        if not ptr2:
            kernel32.GlobalFree(h_txt)
            return False
        try:
            _ct.memmove(ptr2, plain_bytes, len(plain_bytes))
        finally:
            kernel32.GlobalUnlock(h_txt)
        if not user32.SetClipboardData(CF_UNICODETEXT, h_txt):
            kernel32.GlobalFree(h_txt)
            return False
        return True
    finally:
        user32.CloseClipboard()


def paste_rich_text_to_foreground_app(plain_text: str, rtf: str, click_center: bool = True, focus_tokens: Optional[list[str]] = None) -> Dict[str, Any]:
    """Paste rich text to the focused app by setting both RTF and Unicode clipboard data, then Ctrl+V."""
    try:
        import time as _t
        focused = None
        if focus_tokens:
            try:
                focused = ensure_focus(focus_tokens)
            except Exception:
                focused = False
        else:
            focused = True
        _t.sleep(0.05)
        if click_center:
            _ = _click_center_of_foreground()
            _t.sleep(0.03)
        clip_ok = _set_clipboard_rtf(rtf or '', plain_fallback=plain_text or '')
        _t.sleep(0.02)
        paste_ok = _send_ctrl_v() if clip_ok else False
        return {
            'ok': bool(clip_ok and paste_ok),
            'focused': bool(focused),
            'clicked': bool(click_center),
            'pasted': bool(paste_ok),
            'rich': True,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e), 'rich': True}


def paste_text_to_foreground_app(text: str, click_center: bool = True, focus_tokens: Optional[list[str]] = None) -> Dict[str, Any]:
    """Paste provided text into the currently focused application via clipboard + Ctrl+V.

    - Optionally attempts to focus a window matching focus_tokens before pasting.
    - Optionally clicks the center of the foreground window before Ctrl+V to ensure caret.
    Returns a dict with {ok, focused, clicked, pasted}.
    """
    try:
        import time as _t
        focused = None
        if focus_tokens:
            try:
                focused = ensure_focus(focus_tokens)
            except Exception:
                focused = False
        else:
            focused = True  # assume already focused
        _t.sleep(0.05)
        if click_center:
            _ = _click_center_of_foreground()
            _t.sleep(0.03)
        clip_ok = _set_clipboard_text(text or '')
        _t.sleep(0.02)
        paste_ok = _send_ctrl_v() if clip_ok else False
        return {
            'ok': bool(clip_ok and paste_ok),
            'focused': bool(focused),
            'clicked': bool(click_center),
            'pasted': bool(paste_ok),
        }
    except Exception as e:  # pragma: no cover
        return {'ok': False, 'error': str(e)}


# --------------------- Deterministic 3-column arrangement ---------------------
def _norm_token(s: str) -> str:
    try:
        import unicodedata as _ud
        s = _ud.normalize('NFKD', s)
        s = ''.join(ch for ch in s if not _ud.combining(ch))
    except Exception:
        pass
    s = s.lower()
    import re as _re
    s = _re.sub(r"[^a-z0-9\s]+", " ", s)
    s = " ".join(s.split())
    return s


def _find_hwnd_by_tokens(tokens: list[str], max_nodes: int = 2500) -> int | None:
    """Return a NativeWindowHandle (HWND) for a top-level window whose UIA name contains any token.

    Best-effort BFS over ControlView. Returns the first reasonably matching HWND (>0), else None.
    """
    toks = [_norm_token(t) for t in (tokens or []) if t]
    if not toks:
        return None
    # First try fast top-level EnumWindows
    try:
        import ctypes as _ct
        from ctypes import wintypes as _wt
        user32 = _ct.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = _ct.WINFUNCTYPE(_wt.BOOL, _wt.HWND, _wt.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible
        found = _ct.c_int(0)
        best = _ct.c_void_p()
        def callback(hwnd, lParam):
            try:
                if not IsWindowVisible(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = _ct.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value or ''
                n = _norm_token(title)
                if n and any(t in n for t in toks):
                    best.value = hwnd
                    found.value = 1
                    return False
            except Exception:
                return True
            return True
        EnumWindows(EnumWindowsProc(callback), 0)
        if found.value and best.value:
            return int(_ct.cast(best, _ct.c_void_p).value or 0)
    except Exception:
        pass
    # Fallback to UIA BFS
    if not _ensure_com_initialized():
        return None
    try:
        from comtypes.client import GetModule, CreateObject  # type: ignore
        GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        automation = CreateObject(UIA.CUIAutomation)
    except Exception:
        return None
    try:
        root = automation.GetRootElement()
    except Exception:
        root = None
    if root is None:
        return None
    stack = [root]
    visited = 0
    best_hwnd = None
    while stack and visited < max_nodes:
        elem = stack.pop()
        visited += 1
        try:
            name = (elem.CurrentName or '')
        except Exception:
            name = ''
        nname = _norm_token(name)
        try:
            hwnd = getattr(elem, 'CurrentNativeWindowHandle', 0)
        except Exception:
            hwnd = 0
        # Prefer true top-level windows with titles that match any token
        if hwnd and nname and any(t in nname for t in toks):
            best_hwnd = int(hwnd)
            # Heuristic: if it's a window control, accept immediately
            try:
                ctl = getattr(elem, 'CurrentControlType', None)
                if ctl is not None and int(ctl) == 50032:  # UIA_WindowControlTypeId
                    return best_hwnd
            except Exception:
                pass
        # Push children (bounded)
        try:
            child = elem.GetFirstChildElement()
        except Exception:
            child = None
        c = []
        while child is not None and len(c) < 40:
            c.append(child)
            try:
                child = child.GetNextSiblingElement()
            except Exception:
                break
        for ch in c:
            stack.append(ch)
    return best_hwnd


def _set_window_rect(hwnd: int, x: int, y: int, w: int, h: int) -> bool:
    if os.name != 'nt' or not hwnd:
        return False
    try:
        import ctypes as _ct
        SW_RESTORE = 9
        user32 = _ct.windll.user32
        # Restore if minimized/maximized
        user32.ShowWindow(hwnd, SW_RESTORE)
        SWP_NOZORDER = 0x0004
        SWP_NOOWNERZORDER = 0x0200
        SWP_SHOWWINDOW = 0x0040
        flags = SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_SHOWWINDOW
        ok = user32.SetWindowPos(hwnd, None, int(x), int(y), int(w), int(h), flags)
        return bool(ok)
    except Exception:
        return False


def arrange_three_columns(app_tokens: list[str], browser_tokens: list[str], code_tokens: list[str]) -> Dict[str, Any]:
    """Arrange three windows in equal-width vertical columns: App | Browser | Code.

    Returns a dict with success flags and hwnds. Best-effort; succeeds if at least two windows were placed.
    """
    try:
        import ctypes as _ct
        SM_CXSCREEN = 0; SM_CYSCREEN = 1
        sw = int(_ct.windll.user32.GetSystemMetrics(SM_CXSCREEN))
        sh = int(_ct.windll.user32.GetSystemMetrics(SM_CYSCREEN))
        if sw <= 0 or sh <= 0:
            return {'ok': False, 'reason': 'screen_metrics_failed'}
        third = max(1, sw // 3)
        rects = {
            'app': (0, 0, third, sh),
            'browser': (third, 0, third, sh),
            'code': (third * 2, 0, sw - third * 2, sh),  # right remainder
        }
    except Exception:
        return {'ok': False, 'reason': 'screen_query_failed'}

    # Find hwnds
    app_hwnd = _find_hwnd_by_tokens(app_tokens) or 0
    br_hwnd = _find_hwnd_by_tokens(browser_tokens) or 0
    # Prefer a Code window by explicit Code tokens first to avoid matching browser tabs by file title
    code_hwnd = _find_hwnd_by_tokens(code_tokens) or _find_hwnd_by_tokens(["visual studio code", "vs code", "vscode", "code"]) or 0
    # If browser and code resolved to the same HWND, try to disambiguate with stricter tokens
    if br_hwnd and code_hwnd and br_hwnd == code_hwnd:
        # Re-find Code strictly by Code tokens
        strict_code = _find_hwnd_by_tokens(["visual studio code", "vs code", "vscode", "code"]) or 0
        if strict_code and strict_code != br_hwnd:
            code_hwnd = strict_code
        else:
            # Or re-find Browser strictly by browser tokens
            strict_browser = _find_hwnd_by_tokens(["microsoft edge", "edge", "google chrome", "chrome", "mozilla firefox", "firefox", "brave"]) or 0
            if strict_browser and strict_browser != code_hwnd:
                br_hwnd = strict_browser
    placed = {}
    if app_hwnd:
        x,y,w,h = rects['app']; placed['app'] = _set_window_rect(app_hwnd, x,y,w,h)
    if br_hwnd:
        x,y,w,h = rects['browser']; placed['browser'] = _set_window_rect(br_hwnd, x,y,w,h)
    if code_hwnd:
        x,y,w,h = rects['code']; placed['code'] = _set_window_rect(code_hwnd, x,y,w,h)
    success = sum(1 for v in placed.values() if v) >= 2
    return {
        'ok': bool(success),
        'hwnds': {'app': app_hwnd, 'browser': br_hwnd, 'code': code_hwnd},
        'placed': placed,
        'screen': {'w': sw, 'h': sh},
    }


def arrange_right_stack(app_tokens: list[str], browser_tokens: list[str], code_tokens: list[str]) -> Dict[str, Any]:
    """Arrange windows deterministically using SetWindowPos as:
    - App: left half (full height)
    - Browser: right-top quadrant (right half width x top half height)
    - Code: right-bottom quadrant (right half width x bottom half height)

    Returns a dict {'ok': bool, 'hwnds': {...}, 'placed': {...}, 'screen': {...}}
    Succeeds if at least two windows were placed.
    """
    try:
        import ctypes as _ct
        SM_CXSCREEN = 0; SM_CYSCREEN = 1
        sw = int(_ct.windll.user32.GetSystemMetrics(SM_CXSCREEN))
        sh = int(_ct.windll.user32.GetSystemMetrics(SM_CYSCREEN))
        if sw <= 0 or sh <= 0:
            return {'ok': False, 'reason': 'screen_metrics_failed'}
        left_w = max(1, sw // 2)
        right_w = max(1, sw - left_w)
        top_h = max(1, sh // 2)
        bottom_h = max(1, sh - top_h)
        rects = {
            'app': (0, 0, left_w, sh),
            'browser': (left_w, 0, right_w, top_h),
            'code': (left_w, top_h, right_w, bottom_h),
        }
    except Exception:
        return {'ok': False, 'reason': 'screen_query_failed'}

    # Resolve hwnds robustly
    app_hwnd = _find_hwnd_by_tokens(app_tokens) or 0
    br_hwnd = _find_hwnd_by_tokens(browser_tokens) or 0
    code_hwnd = _find_hwnd_by_tokens(code_tokens) or _find_hwnd_by_tokens(["visual studio code", "vs code", "vscode", "code"]) or 0
    # Disambiguate if browser and code collide
    if br_hwnd and code_hwnd and br_hwnd == code_hwnd:
        strict_code = _find_hwnd_by_tokens(["visual studio code", "vs code", "vscode", "code"]) or 0
        if strict_code and strict_code != br_hwnd:
            code_hwnd = strict_code
        else:
            strict_browser = _find_hwnd_by_tokens(["microsoft edge", "edge", "google chrome", "chrome", "mozilla firefox", "firefox", "brave"]) or 0
            if strict_browser and strict_browser != code_hwnd:
                br_hwnd = strict_browser

    placed: Dict[str, bool] = {}
    if app_hwnd:
        x,y,w,h = rects['app']; placed['app'] = _set_window_rect(app_hwnd, x,y,w,h)
    if br_hwnd:
        x,y,w,h = rects['browser']; placed['browser'] = _set_window_rect(br_hwnd, x,y,w,h)
    if code_hwnd:
        x,y,w,h = rects['code']; placed['code'] = _set_window_rect(code_hwnd, x,y,w,h)
    success = sum(1 for v in placed.values() if v) >= 2
    return {
        'ok': bool(success),
        'hwnds': {'app': app_hwnd, 'browser': br_hwnd, 'code': code_hwnd},
        'placed': placed,
        'screen': {'w': sw, 'h': sh},
    }


def snap_to(side: str, vertical: str | None = None) -> bool:
    """Send Windows snap keys to place current foreground window.

    side: 'left' | 'right'
    vertical: None | 'top' | 'bottom' (applies on Windows 11 to target top/bottom on the chosen side)
    """
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct, time as _t
        KEYEVENTF_KEYUP = 0x0002
        VK_LWIN = 0x5B; VK_LEFT = 0x25; VK_RIGHT = 0x27; VK_UP = 0x26; VK_DOWN = 0x28
        vk_side = VK_RIGHT if str(side).lower() == 'right' else VK_LEFT
        # Win + side
        _ct.windll.user32.keybd_event(VK_LWIN, 0, 0, 0); _t.sleep(0.02)
        _ct.windll.user32.keybd_event(vk_side, 0, 0, 0); _t.sleep(0.03)
        _ct.windll.user32.keybd_event(vk_side, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.02)
        _ct.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.04)
        # Optional vertical refinement
        if vertical:
            vk_vert = VK_UP if str(vertical).lower() == 'top' else VK_DOWN
            _ct.windll.user32.keybd_event(VK_LWIN, 0, 0, 0); _t.sleep(0.02)
            _ct.windll.user32.keybd_event(vk_vert, 0, 0, 0); _t.sleep(0.03)
            _ct.windll.user32.keybd_event(vk_vert, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.02)
            _ct.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0); _t.sleep(0.02)
        return True
    except Exception:
        return False


def layout_left_right_stack(app_tokens: list[str], browser_tokens: list[str], code_tokens: list[str]) -> Dict[str, Any]:
    """Arrange as: App (left half) | Browser (right-top) | Code (right-bottom) using Win+Arrow keys.

    Returns {'ok': bool, 'steps': [...]} with per-step success. Works around Snap Assist tile flakiness.
    """
    import time as _t
    steps = []
    ok_all = True
    # 1) App left
    s1 = {'action': 'focus_app', 'ok': (ensure_focus_top(app_tokens) or ensure_focus(app_tokens))}
    steps.append(s1); ok_all = ok_all and s1['ok']
    _t.sleep(0.08)
    s2 = {'action': 'snap_app_left', 'ok': snap_to('left')}
    steps.append(s2); ok_all = ok_all and s2['ok']
    _t.sleep(0.12)
    # 2) Browser right-top
    s3 = {'action': 'focus_browser', 'ok': (ensure_focus_top(browser_tokens) or ensure_focus(browser_tokens))}
    steps.append(s3); ok_all = ok_all and s3['ok']
    _t.sleep(0.08)
    s4 = {'action': 'snap_browser_right_top', 'ok': snap_to('right', 'top')}
    steps.append(s4); ok_all = ok_all and s4['ok']
    _t.sleep(0.12)
    # 3) Code right-bottom
    s5 = {'action': 'focus_code', 'ok': (ensure_focus_top(code_tokens) or ensure_focus(code_tokens))}
    steps.append(s5); ok_all = ok_all and s5['ok']
    _t.sleep(0.08)
    s6 = {'action': 'snap_code_right_bottom', 'ok': snap_to('right', 'bottom')}
    steps.append(s6); ok_all = ok_all and s6['ok']
    return {'ok': bool(ok_all), 'steps': steps}


def _click_screen_point(x: int, y: int) -> bool:
    """Best-effort mouse click at a screen coordinate."""
    if os.name != 'nt':
        return False
    try:
        import ctypes as _ct
        user32 = _ct.windll.user32
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        user32.SetCursorPos(int(x), int(y))
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True
    except Exception:
        return False


def _screen_center_of_right_half() -> tuple[int, int] | None:
    if os.name != 'nt':
        return None
    try:
        import ctypes as _ct
        SM_CXSCREEN = 0; SM_CYSCREEN = 1
        sw = int(_ct.windll.user32.GetSystemMetrics(SM_CXSCREEN))
        sh = int(_ct.windll.user32.GetSystemMetrics(SM_CYSCREEN))
        if sw <= 0 or sh <= 0:
            return None
        x = int((sw * 3) / 4)
        y = int(sh / 2)
        return (x, y)
    except Exception:
        return None


def layout_any_right_stack(app_tokens: list[str], browser_tokens: list[str], code_tokens: list[str]) -> Dict[str, Any]:
    """Order-agnostic tri-split via Snap Assist using a simple progression:
    1) Win+Right on the current foreground window (no pre-focusing)
    2) Select ANY acceptable left tile (from app/browser/code pools)
    3) Click the right-half region to ensure focus on the snapped right window
    4) Win+Up to move it to top-right
    5) Select ANY acceptable bottom-right tile (from app/browser/code pools)

    Returns {'ok': bool, 'steps': [...]} with per-step outcomes.
    """
    import time as _t
    steps: list[Dict[str, Any]] = []
    ok_all = True

    # Utilities for verification
    def _get_screen_size():
        try:
            import ctypes as _ct
            SM_CXSCREEN = 0; SM_CYSCREEN = 1
            return (int(_ct.windll.user32.GetSystemMetrics(SM_CXSCREEN)), int(_ct.windll.user32.GetSystemMetrics(SM_CYSCREEN)))
        except Exception:
            return (0, 0)
    def _get_foreground_rect():
        try:
            import ctypes as _ct
            user32 = _ct.windll.user32
            hwnd = user32.GetForegroundWindow()
            rect = _ct.wintypes.RECT()
            if user32.GetWindowRect(hwnd, _ct.byref(rect)):
                return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        except Exception:
            return None
        return None
    def _is_right_top_half() -> tuple[bool, str | None]:
        rect = _get_foreground_rect(); sw, sh = _get_screen_size()
        if not rect or not sw or not sh:
            return (False, 'no_rect_or_screen')
        x1,y1,x2,y2 = rect; w = max(1, x2 - x1); h = max(1, y2 - y1)
        half_w_ok = 0.38 <= (w/float(sw)) <= 0.62
        top_h_ok = (y1 <= int(0.05*sh)) and (h <= int(0.62*sh))
        right_pos_ok = x1 >= (sw//2) - int(0.12*sw)
        ok = half_w_ok and top_h_ok and right_pos_ok
        if ok:
            return (True, None)
        return (False, f'w_ratio={w/float(sw):.2f}, y1={y1}, h_ratio={h/float(sh):.2f}, x1={x1}')
    def _is_right_bottom_half() -> tuple[bool, str | None]:
        rect = _get_foreground_rect(); sw, sh = _get_screen_size()
        if not rect or not sw or not sh:
            return (False, 'no_rect_or_screen')
        x1,y1,x2,y2 = rect; w = max(1, x2 - x1); h = max(1, y2 - y1)
        half_w_ok = 0.38 <= (w/float(sw)) <= 0.62
        bottom_h_ok = (y1 >= int(0.35*sh)) and (y2 >= int(0.85*sh))
        right_pos_ok = x1 >= (sw//2) - int(0.12*sw)
        ok = half_w_ok and bottom_h_ok and right_pos_ok
        if ok:
            return (True, None)
        return (False, f'w_ratio={w/float(sw):.2f}, y1={y1}, y2={y2}, h_ratio={h/float(sh):.2f}, x1={x1}')

    # Optional: focus Code first so Win+Right targets VS Code like the manual flow
    try:
        prefocus = (ensure_focus_top(code_tokens) or ensure_focus(code_tokens))
    except Exception:
        prefocus = False
    # Base sleep tuning (can be overridden via env)
    import os as _os
    try:
        BASE_DELAY = max(0, int(_os.environ.get('CUA_GENERIC_STACK_SLEEP_MS','450')))/1000.0
    except Exception:
        BASE_DELAY = 0.45
    _t.sleep(BASE_DELAY)

    # Step 1: Snap current (ideally Code) window RIGHT
    s1 = {'action': 'snap_current_right', 'ok': snap_to('right'), 'prefocus_code': bool(prefocus)}
    steps.append(s1); ok_all = ok_all and s1['ok']
    _t.sleep(BASE_DELAY)

    # Step 2: Select any left tile from the pool
    pools: list[tuple[str, list[str]]] = []
    pools.append(('app', list(dict.fromkeys(app_tokens or []))))
    pools.append(('browser', list(dict.fromkeys(browser_tokens or []))))
    pools.append(('code', list(dict.fromkeys(code_tokens or []))))
    s2_ok = False; s2_tokens: list[str] | None = None; s2_group: str | None = None
    deadline = _t.time() + 5.0
    if callable(select_snap_assist_tile):  # type: ignore[truthy-bool]
        for group, toks in pools:
            if _t.time() >= deadline:
                break
            try:
                sel = bool(select_snap_assist_tile(toks))  # type: ignore[misc]
                if sel:
                    s2_ok = True; s2_tokens = toks; s2_group = group; break
            except Exception:
                continue
    s2 = {'action': 'select_left_tile_any', 'ok': s2_ok, 'tokens': s2_tokens, 'group': s2_group}
    steps.append(s2); ok_all = ok_all and s2['ok']
    _t.sleep(BASE_DELAY)

    # Step 3: Click the right region to focus snapped right window
    rc = _screen_center_of_right_half()
    clicked = _click_screen_point(rc[0], rc[1]) if rc else False
    s3 = {'action': 'click_right_center', 'ok': clicked}
    steps.append(s3); ok_all = ok_all and s3['ok']
    _t.sleep(BASE_DELAY)

    # Extra: ensure focus prefers Code on the right like the manual flow; fallback to browser
    try:
        _focus_ok = (ensure_focus_top(code_tokens) or ensure_focus(code_tokens))
        if not _focus_ok:
            _focus_ok = (ensure_focus_top(browser_tokens) or ensure_focus(browser_tokens))
    except Exception:
        _focus_ok = False
    steps.append({'action': 'ensure_focus_right_pref_code', 'ok': bool(_focus_ok)})
    _t.sleep(BASE_DELAY)

    # Step 4: Move it to top-right
    # Try a double Win+Up refinement with spacing; improves reliability on some builds
    s4_sent = snap_to('right', 'top')
    _t.sleep(max(0.08, BASE_DELAY/2))
    s4_sent = snap_to('right', 'top') or s4_sent
    placed_zone = 'top'
    # Verify and retry. If top fails, try bottom; accept either.
    _t.sleep(BASE_DELAY)
    verified_ok, reason = _is_right_top_half()
    if not verified_ok:
        # Retry top once
        snap_to('right'); _t.sleep(max(0.08, BASE_DELAY/2)); s4_sent = snap_to('right', 'top') or s4_sent
        _t.sleep(BASE_DELAY)
        verified_ok, reason = _is_right_top_half()
    if not verified_ok:
        # Try bottom placement instead
        snap_to('right')
        _t.sleep(max(0.08, BASE_DELAY/2))
        s4_sent = snap_to('right', 'bottom') or s4_sent
        _t.sleep(BASE_DELAY)
        vbot_ok, reason_b = _is_right_bottom_half()
        if vbot_ok:
            placed_zone = 'bottom'
            verified_ok = True
            reason = None
        else:
            reason = reason_b or reason
    s4 = {'action': 'snap_right_top_or_bottom', 'ok': s4_sent and verified_ok, 'zone': placed_zone}
    if not verified_ok and reason:
        s4['verify_reason'] = reason
    steps.append(s4); ok_all = ok_all and s4['ok']
    _t.sleep(BASE_DELAY)

    # Step 5: Select any remaining tile for the other right zone
    s5_ok = False; s5_tokens: list[str] | None = None
    # Build remaining pools (exclude the group used in step 2)
    remaining: list[tuple[str, list[str]]] = []
    for group, toks in pools:
        if group and group == s2_group:
            continue
        remaining.append((group, toks))
    # Prefer browser for the second pick (Edge/Chrome HTML preview), then code, then app
    group_order = {'browser': 0, 'code': 1, 'app': 2}
    remaining.sort(key=lambda gt: group_order.get(gt[0], 9))
    deadline2 = _t.time() + 6.0
    attempts = 0
    if callable(select_snap_assist_tile):  # type: ignore[truthy-bool]
        while _t.time() < deadline2 and not s5_ok and attempts < 3:
            # If selection fails, nudge Snap UI open by pressing Win+Right again
            if attempts > 0:
                snap_to('right'); _t.sleep(BASE_DELAY)
            for group, toks in remaining:
                if _t.time() >= deadline2:
                    break
                try:
                    sel = bool(select_snap_assist_tile(toks))  # type: ignore[misc]
                    if sel:
                        s5_ok = True; s5_tokens = toks; break
                except Exception:
                    continue
            attempts += 1
    s5 = {'action': 'select_remaining_right_tile_any', 'ok': s5_ok, 'tokens': s5_tokens, 'attempts': attempts, 'expected_zone': ('bottom' if placed_zone=='top' else 'top')}
    steps.append(s5); ok_all = ok_all and s5['ok']
    return {'ok': bool(ok_all), 'steps': steps}
