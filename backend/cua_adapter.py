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
    global _cua_diag_last
    logger = logging.getLogger(__name__)
    try:
        print(f"CUA: select_snap_assist_tile called with tokens={name_tokens}")
    except Exception:
        pass

    import os as _os_env
    VERBOSE = bool(_os_env.environ.get('CUA_DEBUG_VERBOSE'))

    raw_tokens = [t for t in (name_tokens or []) if isinstance(t, str) and t.strip()]
    generic_labels = {"word", "visual studio code", "vs code", "chrome", "edge", "browser", "code"}
    specific: list[str] = []
    seen_lower = set()
    for t in raw_tokens:
        tl = t.lower().strip()
        if tl in seen_lower:
            continue
        seen_lower.add(tl)
        if tl not in generic_labels and any(c.isalpha() for c in tl) and len(tl) > 2:
            specific.append(t)
            if '.' in tl:
                stem = tl.split('.')[0]
                if stem and stem not in [s.lower() for s in specific] and stem not in generic_labels:
                    specific.append(stem)
    specific_tokens = [s.lower() for s in specific]
    generic_tokens = [g for g in generic_labels if g not in specific_tokens]
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
    # Dynamic max steps: fewer steps when we expect only a tiny grid (common with 2 tiles)
    BASE_MAX = 14 if specific_tokens else 18
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
            matched = any(tok in name_l for tok in phase_tokens)
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
                # Trigger after at least 6 steps with no new uniques for 4+ steps and no potential token substring present
                if step >= 6 and small_set and no_new_names_for >= 4:
                    joined_lower = " | ".join(n.lower() for n in unique_names)
                    any_token_present = any(tok in joined_lower for tok in phase_tokens)
                    if not any_token_present:
                        repetition_break_triggered = True
                        _cua_diag_last = {
                            'matched': False,
                            'reason': 'early_cycle_repetition_no_match',
                            'phase': phase_name,
                            'focus_changes': focus_changes,
                            'attempts': diag_attempts,
                            'unique_names': unique_names,
                            'specific_tokens': specific_tokens,
                            'all_tokens': all_tokens,
                        }
                        return False

            # Move to next tile
            press(VK_RIGHT)
            _t.sleep(0.06)
            if name == last_name:
                stagnate += 1
                if stagnate % 2 == 1:
                    press(VK_DOWN); _t.sleep(0.06)
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
    relaxed_tokens = [t for t in ("visual studio code", "vs code", "code", "word", "chrome", "edge", "browser") if t in all_tokens]
    if relaxed_tokens:
        for rstep in range(10):
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
            if any(rt in name.lower() for rt in relaxed_tokens):
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
            press(VK_RIGHT); _t.sleep(0.05)

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
            token_set = set(all_tokens)
            while stack and visited < MAX_NODES and matched_elem is None:
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
                    if any(tok in low for tok in token_set):
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
                diag_attempts.append({'phase': 'bfs_fallback', 'step': 0, 'name': '', 'matched': False, 'info': 'no_match_in_bfs'})
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
