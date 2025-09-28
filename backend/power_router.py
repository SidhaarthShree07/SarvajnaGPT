from __future__ import annotations

from typing import List, Optional, Dict, Any
import os
import shutil
import difflib
from pathlib import Path
import uuid
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from llm_inference import generate_response

# Version banner for diagnostics
POWER_ROUTER_VERSION = "2025-09-27-EXEC-AUG-v7"
try:
    print(f"POWER_ROUTER_VERSION: {POWER_ROUTER_VERSION}")
except Exception:
    pass

# Reuse fs and word executors by delegating to existing routers/adapters
from agent_router import ActionType as FsActionType, Action as FsAction, preview as fs_preview, execute as fs_execute
from word_router import preview as word_preview, execute as word_execute
from automation_router import word_preview as auto_word_preview, word_execute as auto_word_execute  # Rename to avoid conflict
import sqlite3, time

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chat_embeddings.db'))
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
AGENT_BASE_DIR = os.path.join(REPO_ROOT, "agent_output")
os.makedirs(AGENT_BASE_DIR, exist_ok=True)


def _resolve_under_base(path_like: str) -> str:
    p = path_like
    if not os.path.isabs(p):
        p = os.path.join(AGENT_BASE_DIR, p)
    p = os.path.abspath(p)
    base = os.path.abspath(AGENT_BASE_DIR)
    if os.path.commonpath([p, base]) != base:
        raise ValueError("Target path outside agent base directory")
    return p

def _augment_assistant_with_exec(assistant_text: str, exec_result: Any) -> str:
    """Append saved path (except internal agent_output paths), VS Code, and mirror summaries.
    Suppresses 'Saved to:' line for sandbox (agent_output) files per user request.
    """
    try:
        if not exec_result or not isinstance(exec_result, dict):
            return assistant_text
        saved_path = None
        res_list = exec_result.get('results') if 'results' in exec_result else None
        if isinstance(res_list, list):
            for r in res_list:
                r_res = r.get('result')
                if isinstance(r_res, dict):
                    saved_path = saved_path or r_res.get('saved_path') or r_res.get('path')
                elif isinstance(r_res, list) and r_res:
                    try:
                        first = r_res[0]
                        if isinstance(first, dict):
                            inner = first.get('result') or {}
                            if isinstance(inner, dict):
                                saved_path = saved_path or inner.get('path')
                    except Exception:
                        pass
                saved_path = saved_path or r.get('desktop_path')
        if saved_path:
            low = saved_path.lower()
            # Only show if not under agent_output sandbox
            if 'agent_output' not in low:
                assistant_text = (assistant_text or '').rstrip() + f"\n\nSaved to: {saved_path}"
        if isinstance(res_list, list):
            vs_lines = []
            mirror_lines = []
            for r in res_list:
                rtype = r.get('type')
                data = r.get('result')
                if isinstance(data, list):
                    try:
                        first = data[0]
                        if isinstance(first, dict):
                            data = first.get('result') or {}
                    except Exception:
                        data = {}
                if not isinstance(data, dict):
                    data = {}
                if rtype == 'automation.open_vscode':
                    opened = data.get('opened')
                    err = data.get('error')
                    path = data.get('path')
                    snapped = data.get('snapped')
                    side = data.get('side')
                    if opened:
                        base_line = f"VS Code opened: {path}"
                        if snapped:
                            base_line += f" (snapped {side or 'right'} half)"
                        vs_lines.append(base_line)
                    else:
                        vs_lines.append(f"VS Code open failed: {err}")
                elif rtype == 'fs.mirror_to_documents':
                    mf = data.get('mirrored_file')
                    md = data.get('mirrored_dir')
                    if mf:
                        mirror_lines.append(f"Mirrored file -> {mf}")
                    if md:
                        mirror_lines.append(f"Mirrored directory -> {md}")
            if vs_lines:
                assistant_text += "\n" + "\n".join(vs_lines)
            if mirror_lines:
                assistant_text += "\n" + "\n".join(mirror_lines)
    except Exception:
        pass
    return assistant_text


# Inline edit configuration
INLINE_EDIT_MAX_SELECTION_CHARS = 6000
INLINE_EDIT_PREVIEW_LIMIT = 400


def _truncate_preview(text: str, limit: int) -> str:
    if not text:
        return ''
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '…'


def _extract_inline_replacement(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw)
    marker_match = re.search(r"<<<REPLACEMENT>>>(.*)<<<END_REPLACEMENT>>>", text, re.DOTALL)
    if marker_match:
        return marker_match.group(1).strip('\r\n')
    stripped = text.strip()
    return stripped or None


def _get_recent_chat_history(chat_id: str, service: Optional[str], limit: int = 6, char_limit: int = 2400) -> Optional[str]:
    if not chat_id:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if service:
            c.execute(
                'SELECT user, llm FROM chat WHERE chat_id=? AND service=? ORDER BY id DESC LIMIT ?',
                (chat_id, service, limit)
            )
        else:
            c.execute(
                'SELECT user, llm FROM chat WHERE chat_id=? ORDER BY id DESC LIMIT ?',
                (chat_id, limit)
            )
        rows = c.fetchall() or []
        conn.close()
    except Exception:
        return None
    if not rows:
        return None
    rows.reverse()
    lines: list[str] = []
    total = 0
    for user_text, ai_text in rows:
        if user_text:
            snippet = f"User: {str(user_text).strip()}"
            if snippet:
                lines.append(snippet)
                total += len(snippet)
        if ai_text:
            snippet = f"Assistant: {str(ai_text).strip()}"
            if snippet:
                lines.append(snippet)
                total += len(snippet)
        if total >= char_limit:
            break
    if not lines:
        return None
    history = "\n".join(lines)
    if len(history) > char_limit:
        history = history[:char_limit].rstrip() + '…'
    return history


def _build_inline_edit_prompt(target: str, instruction: str, selection: str, context_block: Optional[str]) -> str:
    target_label = "Microsoft Word document" if target == 'word' else "Visual Studio Code buffer"
    parts = [
        f"You are assisting with in-place editing inside a {target_label}.",
        "Rewrite the highlighted selection so it satisfies the user's latest request.",
        "Return ONLY the replacement text between <<<REPLACEMENT>>> and <<<END_REPLACEMENT>>> with no commentary.",
    ]
    if context_block:
        parts.append(f"Conversation context to respect (oldest to newest):\n{context_block}")
    parts.append(f"Original selection:\n<<<SELECTION>>>\n{selection}\n<<<END_SELECTION>>>")
    parts.append(f"User request:\n{instruction.strip()}")
    parts.append("If no changes are needed, return the original selection verbatim between the replacement markers.")
    return "\n\n".join(parts)


def _maybe_handle_inline_selection(req: 'PowerChatRequest', context_block: Optional[str]) -> Optional[Dict[str, Any]]:
    if os.name != 'nt':
        return None
    try:
        from automation_router import (  # type: ignore import-error
            get_word_selection_info,
            replace_word_selection,
            get_vscode_selection_info,
            replace_vscode_selection,
        )
    except Exception as exc:
        try:
            print(f"INLINE_EDIT_AUTOMATION_IMPORT_ERR: {exc}")
        except Exception:
            pass
        return None

    word_info: Optional[Dict[str, Any]]
    code_info: Optional[Dict[str, Any]]
    try:
        word_info = get_word_selection_info(require_active=True)
    except Exception as exc:
        word_info = None
        try:
            print(f"INLINE_EDIT_WORD_INFO_ERR: {exc}")
        except Exception:
            pass
    try:
        code_info = get_vscode_selection_info(require_active=True)
    except Exception as exc:
        code_info = None
        try:
            print(f"INLINE_EDIT_VSCODE_INFO_ERR: {exc}")
        except Exception:
            pass

    candidates: list[tuple[str, Dict[str, Any]]] = []
    if word_info:
        candidates.append(('word', word_info))
    if code_info:
        candidates.append(('vscode', code_info))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (not item[1].get('is_active', False), item[0] != 'word'))

    for target, info in candidates:
        if not info.get('ok'):
            continue
        selection_raw = (info.get('selection') or '').replace('\r', '\n')
        if not selection_raw.strip():
            continue
        if len(selection_raw) > INLINE_EDIT_MAX_SELECTION_CHARS:
            try:
                print(f"INLINE_EDIT_SKIP_{target.upper()}: selection too long ({len(selection_raw)} chars)")
            except Exception:
                pass
            continue
        prompt = _build_inline_edit_prompt(target, req.text, selection_raw, context_block)
        raw = generate_response(prompt)
        replacement = _extract_inline_replacement(raw)
        if replacement is None:
            continue
        replacement_norm = replacement.replace('\r\n', '\n')
        success = False
        if target == 'word':
            success = replace_word_selection(replacement)
        else:
            success = replace_vscode_selection(replacement, hwnd=info.get('hwnd'))
        if not success:
            continue
        label = 'Word' if target == 'word' else 'VS Code'
        assistant_text = (
            f"Updated the highlighted {label} content.\n\n"
            f"Preview:\n{_truncate_preview(replacement_norm, INLINE_EDIT_PREVIEW_LIMIT)}"
        )
        return {
            "assistant_text": assistant_text,
            "execute_result": {
                "inline_edit": {
                    "target": target,
                    "window_title": info.get('title'),
                    "selection_before": _truncate_preview(selection_raw, 600),
                    "replacement": _truncate_preview(replacement_norm, 600),
                }
            }
        }
    return None

# ---------------- VS Code Auto-Detection Utilities -----------------
_VSCODE_DETECTION_CACHE: dict[str, str] = {}

def _open_vscode_path(abs_path: str, side: str = 'right', split: bool = True, new_window: bool = True) -> dict:
    """Internal helper to launch VS Code for a given absolute path and optionally snap window.
    Mirrors logic from automation.open_vscode action so we can auto-open after file creation.
    """
    print(f"VSCODE_OPEN: Received path={abs_path}, checking if file exists...")
    result: dict[str, Any] = {"opened": False, "path": abs_path, "snapped": False, "side": side}
    
    # Verify the file exists
    if not os.path.exists(abs_path):
        print(f"VSCODE_OPEN: File not found: {abs_path}")
        result["error"] = f"File not found: {abs_path}"
        return result
    else:
        print(f"VSCODE_OPEN: File exists at {abs_path}, real absolute path: {os.path.abspath(abs_path)}")
        
    try:
        resolved_cmd, tried = _resolve_vscode_executable()
        result["command"] = resolved_cmd
        result["tried"] = tried
        print(f"VSCODE_OPEN: Resolved VS Code command: {resolved_cmd}")
        if not resolved_cmd:
            result["error"] = "VS Code executable not found"
            return result
        
        import subprocess as _sub, time as _t, ctypes
        use_shell = False
        abs_path_real = os.path.abspath(abs_path)
        
        # Check if cmd is just "code" (PATH-based) or ends with cmd/bat
        if resolved_cmd == "code" or (os.name == 'nt' and resolved_cmd.lower().endswith(('.cmd', '.bat'))):
            use_shell = True
            
        try:
            print(f"VSCODE_OPEN: Executing VS Code with path: {abs_path_real}")
            
            # Handle different launch methods based on installation type
            if resolved_cmd == "code" or use_shell:
                # Build command; optionally omit --new-window to reuse existing window
                if new_window:
                    cmd = f'code --new-window "{abs_path_real}"'
                else:
                    cmd = f'code "{abs_path_real}"'
                print(f"VSCODE_OPEN: Running shell command: {cmd}")
                _sub.Popen(cmd, shell=True)
            else:
                # For direct executable paths - add --new-window only when requested
                if new_window:
                    _sub.Popen([resolved_cmd, "--new-window", abs_path_real])
                else:
                    _sub.Popen([resolved_cmd, abs_path_real])
                
            result["opened"] = True
            print("VSCODE_OPEN: Successfully launched VS Code")
        except Exception as _el:
            print(f"VSCODE_OPEN: Launch failed: {_el}")
            result["error"] = f"Launch failed: {_el}"
            return result
        if result["opened"] and split and os.name == 'nt':
            try:
                # Increased delay to give VS Code more time to initialize
                print("VSCODE_OPEN: Waiting for VS Code window to initialize before snapping...")
                _t.sleep(2.5)
                user32 = ctypes.windll.user32
                user32.EnumWindows.restype = ctypes.c_bool
                user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p), ctypes.c_void_p]
                file_basename = os.path.basename(abs_path).lower()
                print(f"VSCODE_OPEN: Looking for VS Code window with filename: {file_basename}")
                target_hwnd = None
                def _enum_proc(hwnd, lParam):  # type: ignore
                    buff = ctypes.create_unicode_buffer(512)
                    if user32.IsWindowVisible(hwnd):
                        user32.GetWindowTextW(hwnd, buff, 512)
                        title = buff.value
                        lowt = (title or '').lower()
                        
                        # Debug window titles
                        print(f"VSCODE_OPEN: Found window: '{title}'")
                        
                        # More robust window detection for VS Code
                        is_vscode_window = any(pattern in lowt for pattern in [
                            'visual studio code',
                            'vs code',
                            'vscode',
                            file_basename
                        ])
                        
                        if title and is_vscode_window:
                            print(f"VSCODE_OPEN: Identified VS Code window: '{title}'")
                            nonlocal target_hwnd
                            target_hwnd = hwnd
                    return True
                CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                attempts = 0
                while attempts < 3 and not target_hwnd:
                    user32.EnumWindows(CMPFUNC(_enum_proc), 0)
                    if target_hwnd:
                        break
                    _t.sleep(0.7)
                    attempts += 1
                if target_hwnd:
                    print(f"VSCODE_OPEN: Found VS Code window with handle: {target_hwnd}")
                    # Make sure the window is restored (not minimized or maximized) before resizing
                    SW_RESTORE = 9
                    user32.ShowWindow(target_hwnd, SW_RESTORE)
                    
                    # Get screen dimensions
                    sw = user32.GetSystemMetrics(0)
                    sh = user32.GetSystemMetrics(1)
                    half_w = int(sw/2)
                    
                    # Calculate window position based on side
                    if side == 'left':
                        x, y, w, h = 0, 0, half_w, sh
                    else:
                        x, y, w, h = half_w, 0, half_w, sh
                    
                    print(f"VSCODE_OPEN: Snapping window to {side} side: x={x}, y={y}, w={w}, h={h}")
                    user32.MoveWindow(target_hwnd, x, y, w, h, True)
                    result["snapped"] = True
                    print(f"VSCODE_OPEN: Window snapped successfully to {side} side")
                if not result["snapped"]:
                    print("VSCODE_OPEN: Primary window snapping failed, trying Win+Arrow key fallback...")
                    # Fallback Win+Arrow simulation
                    try:
                        VK_LEFT = 0x25
                        VK_RIGHT = 0x27
                        KEYEVENTF_EXTENDEDKEY = 0x0001
                        KEYEVENTF_KEYUP = 0x0002
                        VK_LWIN = 0x5B
                        
                        def key_down(vk):
                            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
                        
                        def key_up(vk):
                            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                        
                        # Try to make VS Code the active window first
                        if target_hwnd:
                            user32.SetForegroundWindow(target_hwnd)
                            _t.sleep(0.5)
                        
                        # Press Win+Left/Right Arrow
                        print(f"VSCODE_OPEN: Sending Win+{'Left' if side == 'left' else 'Right'} key combination")
                        key_down(VK_LWIN)
                        key_down(VK_LEFT if side == 'left' else VK_RIGHT)
                        _t.sleep(0.1)
                        key_up(VK_LEFT if side == 'left' else VK_RIGHT)
                        key_up(VK_LWIN)
                        
                        result["snapped"] = True
                        print("VSCODE_OPEN: Win+Arrow keys sent successfully")
                    except Exception as e:
                        print(f"VSCODE_OPEN: Fallback key simulation failed: {e}")
                        pass
                # Try one more time with PowerShell if everything else fails
                if not result["snapped"] and target_hwnd:
                    try:
                        print("VSCODE_OPEN: Attempting PowerShell window snap as last resort...")
                        import subprocess
                        ps_script = f'''
                        Add-Type @"
                        using System;
                        using System.Runtime.InteropServices;
                        public class Win32 {{
                            [DllImport("user32.dll")]
                            public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                            
                            [DllImport("user32.dll")]
                            public static extern bool SetForegroundWindow(IntPtr hWnd);
                            
                            [DllImport("user32.dll")]
                            public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
                        }}
"@
                        # Window handle: {target_hwnd}
                        $hwnd = [IntPtr]::new({target_hwnd})
                        # Restore window if minimized
                        [Win32]::ShowWindow($hwnd, 9)
                        # Bring to foreground
                        [Win32]::SetForegroundWindow($hwnd)
                        # Get screen width
                        $screenWidth = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Width
                        $screenHeight = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Height
                        # Calculate position
                        $x = {0 if side == 'left' else 'int($screenWidth/2)'}
                        $width = [int]($screenWidth/2)
                        # Move window
                        [Win32]::MoveWindow($hwnd, $x, 0, $width, $screenHeight, $true)
                        '''
                        
                        # Save script to temp file and execute
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1') as f:
                            f.write(ps_script.encode('utf-8'))
                            ps_path = f.name
                        
                        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_path], 
                                      capture_output=True)
                        
                        # Clean up
                        try:
                            os.unlink(ps_path)
                        except:
                            pass
                        
                        result["snapped"] = True
                        print("VSCODE_OPEN: PowerShell snap attempt completed")
                    except Exception as e:
                        print(f"VSCODE_OPEN: PowerShell snap failed: {e}")
            except Exception as e:
                print(f"VSCODE_OPEN: Window snap exception: {e}")
                pass
        return result
    except Exception as e:
        result["error"] = str(e)
        print(f"VSCODE_OPEN: Overall exception: {e}")
        return result

def _candidate_vscode_paths() -> list[str]:
    paths: list[str] = []
    local = os.environ.get('LOCALAPPDATA','')
    program_files = os.environ.get('ProgramFiles', r"C:\\Program Files")
    program_files_x86 = os.environ.get('ProgramFiles(x86)', r"C:\\Program Files (x86)")
    userprofile = os.environ.get('USERPROFILE','')
    # Standard installs
    paths.extend([
        os.path.join(local, 'Programs', 'Microsoft VS Code', 'Code.exe'),
        os.path.join(program_files, 'Microsoft VS Code', 'Code.exe'),
        os.path.join(program_files_x86, 'Microsoft VS Code', 'Code.exe'),
    ])
    # User local installs (portable) common patterns
    paths.extend([
        os.path.join(userprofile, 'AppData', 'Local', 'Programs', 'Microsoft VS Code', 'Code.exe'),
        os.path.join(userprofile, 'AppData', 'Local', 'Programs', 'VSCode', 'Code.exe'),
        # Add Microsoft Store installation path
        os.path.join(local, 'Microsoft', 'WindowsApps', 'code.exe'),
        # Add Git Bash path option
        os.path.join(program_files, 'Git', 'cmd', 'code.cmd'),
    ])
    # Insider builds
    paths.extend([
        os.path.join(local, 'Programs', 'Microsoft VS Code Insiders', 'Code - Insiders.exe'),
        os.path.join(program_files, 'Microsoft VS Code Insiders', 'Code - Insiders.exe'),
    ])
    return [p for p in paths if p and isinstance(p,str)]

def _deep_search_vscode(limit: int = 30) -> Optional[str]:
    """Perform a bounded breadth search for Code.exe if not found in standard places.
    Scans selected root dirs up to a limited number of directory entries to avoid slowdown."""
    roots = []
    for env_key in ('LOCALAPPDATA','ProgramFiles','ProgramFiles(x86)','USERPROFILE'):
        val = os.environ.get(env_key)
        if val and os.path.isdir(val):
            roots.append(val)
    seen = 0
    target_lower = 'code.exe'
    for root in roots:
        for r, dnames, fnames in os.walk(root):
            # Cheap pruning
            lowr = r.lower()
            if 'code' not in lowr and 'vscode' not in lowr and 'microsoft' not in lowr:
                continue
            if target_lower in (f.lower() for f in fnames):
                cand = os.path.join(r, 'Code.exe')
                if os.path.isfile(cand):
                    return cand
            seen += 1
            if seen > limit:
                break
        if seen > limit:
            break
    return None

def _resolve_vscode_executable() -> tuple[Optional[str], list[str]]:
    """Return (executable_path, tried_candidates). Caches successful detection in-memory."""
    if '_resolved' in _VSCODE_DETECTION_CACHE:
        return _VSCODE_DETECTION_CACHE['_resolved'], []
    tried: list[str] = []
    
    # 1. Respect POWER_VSCODE_BIN if valid
    env_bin = os.environ.get('POWER_VSCODE_BIN')
    if env_bin and os.path.isfile(env_bin):
        _VSCODE_DETECTION_CACHE['_resolved'] = env_bin
        return env_bin, tried
    
    # 2. Try shell 'code' if available (only if which finds it)
    try:
        import shutil as _sh
        shell_cmd = _sh.which('code')
        if shell_cmd and os.path.isfile(shell_cmd):
            _VSCODE_DETECTION_CACHE['_resolved'] = shell_cmd
            return shell_cmd, tried
        if shell_cmd:
            tried.append(shell_cmd)
    except Exception:
        pass
    
    # 2.5 Try Windows PowerShell to find code in PATH
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", "(Get-Command code -ErrorAction SilentlyContinue).Source"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            ps_path = result.stdout.strip()
            if os.path.isfile(ps_path):
                _VSCODE_DETECTION_CACHE['_resolved'] = ps_path
                return ps_path, tried
            tried.append(ps_path)
    except Exception:
        pass
    
    # 2.6 Check Microsoft Store app registration (Windows)
    if os.name == 'nt':
        try:
            ms_store_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'WindowsApps', 'code.exe')
            if os.path.isfile(ms_store_path):
                _VSCODE_DETECTION_CACHE['_resolved'] = ms_store_path
                return ms_store_path, tried
            tried.append(ms_store_path)
        except Exception:
            pass
        
    # 3. Standard candidate list
    for c in _candidate_vscode_paths():
        if os.path.isfile(c):
            _VSCODE_DETECTION_CACHE['_resolved'] = c
            return c, tried
        tried.append(c)
    
    # 4. Deep search (bounded)
    deep = _deep_search_vscode()
    if deep and os.path.isfile(deep):
        _VSCODE_DETECTION_CACHE['_resolved'] = deep
        return deep, tried
    if deep:
        tried.append(deep)
    
    # 5. Last resort - try direct command which may work if VS Code is in PATH
    # This is especially important for Microsoft Store installations
    _VSCODE_DETECTION_CACHE['_resolved'] = "code"
    print("VSCODE_DETECT: Falling back to 'code' command which should work if VS Code is in your PATH")
    return "code", tried

def _chat_state_upsert(chat_id: str, service: str | None, tags: list[str] | None, doc_path: str | None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Ensure table exists (defensive)
        c.execute('''CREATE TABLE IF NOT EXISTS chat_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            service TEXT,
            persistent_tags TEXT,
            doc_path TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )''')
        now = int(time.time())
        # Find existing
        if service:
            c.execute('SELECT id, persistent_tags, doc_path FROM chat_state WHERE chat_id=? AND service=? ORDER BY id DESC LIMIT 1', (chat_id, service))
        else:
            c.execute('SELECT id, persistent_tags, doc_path FROM chat_state WHERE chat_id=? ORDER BY id DESC LIMIT 1', (chat_id,))
        row = c.fetchone()
        tags_str = None
        if tags:
            tags_norm = [str(t).strip() for t in tags if t and str(t).strip()]
            if tags_norm:
                tags_str = ','.join(tags_norm)
        if row:
            rid, prev_tags, prev_doc = row
            new_tags = tags_str if tags_str is not None else prev_tags
            new_doc = doc_path if doc_path is not None else prev_doc
            c.execute('UPDATE chat_state SET persistent_tags=?, doc_path=?, updated_at=? WHERE id=?', (new_tags, new_doc, now, rid))
        else:
            c.execute('INSERT INTO chat_state (chat_id, service, persistent_tags, doc_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, service, tags_str, doc_path, now, now))
        conn.commit()
        conn.close()
    except Exception:
        pass

def _chat_state_get(chat_id: str, service: str | None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if service:
            c.execute('SELECT persistent_tags, doc_path FROM chat_state WHERE chat_id=? AND service=? ORDER BY id DESC LIMIT 1', (chat_id, service))
        else:
            c.execute('SELECT persistent_tags, doc_path FROM chat_state WHERE chat_id=? ORDER BY id DESC LIMIT 1', (chat_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        ptags, dpath = row
        tags = []
        if ptags:
            try:
                tags = [t.strip() for t in str(ptags).split(',') if t and str(t).strip()]
            except Exception:
                tags = []
        return {"persistent_tags": tags, "doc_path": dpath}
    except Exception:
        return None


# New functions for user path resolution
def _get_standard_user_folder(folder_name: str) -> Path:
    """Get standard user folders like Documents, Desktop, Downloads with OneDrive fallbacks on Windows.
    Prefers existing directories when possible.
    """
    try:
        name = folder_name.lower().strip()
        home = Path.home()
        candidates: list[Path] = []
        if os.name == 'nt':  # Windows
            userprofile = Path(os.environ.get('USERPROFILE') or str(home))
            onedrive = os.environ.get('OneDrive') or os.path.join(str(userprofile), 'OneDrive')
            onedrive_path = Path(onedrive)
            if name in ['documents', 'document', 'docs', 'doc']:
                candidates = [
                    userprofile / 'Documents',
                    onedrive_path / 'Documents',
                ]
            elif name in ['desktop', 'desk']:
                candidates = [
                    userprofile / 'Desktop',
                    onedrive_path / 'Desktop',
                ]
            elif name in ['downloads', 'download', 'down']:
                candidates = [
                    userprofile / 'Downloads',
                    onedrive_path / 'Downloads',
                ]
            else:
                candidates = [userprofile / 'Documents', onedrive_path / 'Documents']
        else:
            # Unix-like
            if name in ['documents', 'document', 'docs', 'doc']:
                candidates = [home / 'Documents']
            elif name in ['desktop', 'desk']:
                candidates = [home / 'Desktop']
            elif name in ['downloads', 'download', 'down']:
                candidates = [home / 'Downloads']
            else:
                candidates = [home / 'Documents']
        # Pick the first existing, else return the first candidate (will create later)
        for c in candidates:
            try:
                if c.exists():
                    return c
            except Exception:
                continue
        return candidates[0] if candidates else (home / 'Documents')
    except Exception:
        # Fall back to agent base directory if something goes wrong
        return Path(AGENT_BASE_DIR)


def _resolve_save_path(save_target: str, chat_id: Optional[str] = None) -> str:
    """
    Resolves the save path for Word documents based on user input.
    Handles:
    1. Absolute paths
    2. Standard user folders (Desktop, Documents, Downloads)
    3. Relative paths under the agent output directory
    
    Also ensures unique filenames when needed.
    """
    # If it's an absolute path, validate and return it
    if os.path.isabs(save_target):
        return save_target
    
    # Check if it starts with a standard user folder name (e.g., "desktop/filename.docx")
    folder_match = re.match(r'^(desktop|documents?|downloads?)[/\\](.+)$', save_target, re.IGNORECASE)
    if folder_match:
        folder_name = folder_match.group(1)
        file_path = folder_match.group(2)
        base_folder = _get_standard_user_folder(folder_name)
        
        # Save directly in the requested standard folder (no SarvajnaGPT subfolder)
        target_folder = base_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Ensure filename is unique
        if '.' not in file_path:
            file_path = f"{file_path}.docx"
        
        path = target_folder / file_path
        if path.exists():
            # Add unique suffix if file exists
            stem = path.stem
            suffix = path.suffix
            unique_id = uuid.uuid4().hex[:8]
            path = target_folder / f"{stem}_{unique_id}{suffix}"
        
        return str(path)
    
    # Check if it's just a folder name like "desktop" or "documents"
    if save_target.lower() in ['desktop', 'documents', 'downloads', 'document', 'download', 'docs', 'doc', 'desk', 'down']:
        base_folder = _get_standard_user_folder(save_target)
        
        # Save directly in the requested standard folder (no SarvajnaGPT subfolder)
        target_folder = base_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Generate a filename using chat_id or a timestamp
        filename = f"{chat_id if chat_id else 'document'}_{uuid.uuid4().hex[:8]}.docx"
        return str(target_folder / filename)
    
    # Default behavior: save under agent_output directory
    try:
        return _resolve_under_base(save_target)
    except ValueError:
        # If the target path is outside the agent base directory, save to Documents/SarvajnaGPT (default)
        base_folder = _get_standard_user_folder('documents')
        target_folder = base_folder / 'SarvajnaGPT'
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Extract just the filename from the path
        filename = os.path.basename(save_target)
        if not filename or '.' not in filename:
            # Generate a filename if none is provided or it doesn't have an extension
            filename = f"{chat_id if chat_id else 'document'}_{uuid.uuid4().hex[:8]}.docx"
        
        return str(target_folder / filename)


router = APIRouter(prefix="/api/power", tags=["power"])


class PowerChatRequest(BaseModel):
    chat_id: str
    text: str
    # Optional context fields from the UI (ignored by older clients)
    mem_context: Optional[str] = None
    doc_info: Optional[str] = None
    selected_tags: Optional[list[str]] = None
    mem_tags: Optional[list[str]] = None
    auto_execute: bool = True
    service: Optional[str] = None


class ProposedAction(BaseModel):
    type: str
    params: Dict[str, Any]


class PowerChatResponse(BaseModel):
    assistant_text: str
    actions: List[ProposedAction] = []
    execute_result: Optional[Dict[str, Any]] = None


TOOL_SPEC = {
    "fs.create_folder": {
        "params": {"parent_path": "string", "name": "string"},
        "description": "Create a folder under the allowlisted base directory.",
    },
    "fs.write_file": {
        "params": {"relative_path": "string", "content": "string", "encoding": "string"},
        "description": "Write a text file under the allowlisted base directory.",
    },
    "fs.mirror_to_documents": {
        "params": {"relative_path": "string", "target_subdir": "string?"},
        "description": "Copy a file (or directory) from agent_output to the user's Documents/SarvajnaGPT mirror (optionally into a subfolder).",
    },
    "word.create_document": {
        "params": {"target_rel": "string", "paragraph": "string"},
        "description": "Create a .docx at target_rel and insert a paragraph.",
    },
    "word.open_and_type": {
        "params": {"text": "string", "show_window": "boolean", "save_target": "string?", 
                  "split_screen": "boolean", "use_cua_for_selection": "boolean", 
                  "arrangement_delay_ms": "number"},
        "description": "Open Word (COM), insert text into a new doc, optionally save (.docx) under agent_output.",
    },
    "automation.open_vscode": {
        "params": {"path": "string", "focus": "boolean", "split_screen": "boolean?", "vscode_side": "string?"},
        "description": "Open a file or folder in Visual Studio Code. Supports optional split_screen with vscode_side ('left'|'right').",
    },
}


def _planner_prompt(user_text: str, mem_context: Optional[str] = None) -> str:
    ctx = (f"\nContext (summarize or use when helpful):\n{mem_context[:3000]}\n" if mem_context else "\n")
    policy = (
        "Important constraints & decision rules:\n"
        "- All file operations MUST stay under the allowlisted base directory 'agent_output' at the repository root.\n"
        "- Never propose absolute paths (e.g., C:\\, /home). If user mentions Desktop/Documents/Downloads, still produce a RELATIVE path (planner does not directly save there).\n"
        "- For fs.write_file, default encoding to 'utf-8' if not specified.\n"
        "- For word.create_document, 'target_rel' must be a relative path under agent_output (e.g., docs/summary.docx).\n"
        "- For word.open_and_type, you can use additional parameters like split_screen:true to show Word side-by-side with this app.\n"
        "- ALWAYS use word.open_and_type when the user explicitly asks for a Word document, .docx, paper, essay, report, letter, or mentions 'write a document' / 'Word'.\n"
        "- DO NOT use any word.* action when the request is about building a web page, website, landing page, homepage, HTML, CSS, JavaScript, or a UI/component — instead create appropriate code files with fs.write_file.\n"
        "- For website / HTML requests: (1) create an index.html (and optionally style.css or script.js) via fs.write_file, (2) then propose automation.open_vscode to open the created file/folder, (3) then propose fs.mirror_to_documents for the main HTML file so a copy appears in Documents/SarvajnaGPT.\n"
        "- Provide COMPLETE HTML content including <!DOCTYPE html>, <html>, <head> with <meta charset> and a meaningful <title>, and <body>. Inline minimal CSS is fine if no separate CSS file is created.\n"
        "- Only add additional assets (css/js) if the user specifically asks or functionality clearly requires it.\n"
        "- For multi-file site requests, create each file with its own fs.write_file action.\n"
        "- The automation.open_vscode action should follow file creation actions; path parameter should reference the newly created file (e.g., 'files/index.html') or its containing folder.\n"
        "- Use fs.mirror_to_documents ONLY after creating a file that the user will likely want outside the sandbox (e.g., index.html). Do not mirror temporary or trivial files.\n"
        "- When creating Word documents include FULL prose content in the 'text' parameter (no placeholders). Honor requested word counts (generate that many words).\n"
        "- If user asks for an academic paper, include introduction, structured sections, conclusion, and references.\n"
        "- Never emit placeholder tokens like [1000 words] — always expand to real content.\n"
        "- When creating CODE files with fs.write_file: put ONLY the raw code (no explanations) inside a single <code lang=EXT>...</code> block in the 'content' field. EXT must be an appropriate extension (py, js, ts, html, css, json, md).\n"
        "- Do NOT include that code block inside assistant_text. assistant_text should be a concise summary or next-step guidance WITHOUT the full code.\n"
        "- Do NOT wrap the entire JSON in markdown fences. Return strict JSON only.\n"
        "- If multiple code files are needed, create one fs.write_file action per file, each with its own <code> block.\n"
    )
    tool_lines = "\n".join([f"- {k}: {v['description']} params={v['params']}" for k, v in TOOL_SPEC.items()])
    return (
        "You are a planner that decides if any tools should be called to fulfill the user's request.\n"
        "Tools (functions) you can propose as actions:\n" + tool_lines + "\n\n"
        + policy + ctx +
        "\nOutput format:\n"
    "Return ONLY strict JSON: {\"assistant_text\": string, \"actions\": [{\"type\": string, \"params\": object}]}. Do not include markdown code fences.\n"
    "If any fs.write_file action is used its 'content' MUST contain exactly one <code lang=EXT>...</code> block and nothing else (no preceding or trailing prose).\n"
    "assistant_text MUST NOT repeat or inline the full code; keep it high-level.\n\n"
        "For word.open_and_type actions, ensure the params include:\n"
        "- \"text\": The complete text content to write to the document\n"
        "- \"save_target\": The location to save (\"desktop\", \"documents\", or \"downloads\")\n"
        "- \"show_window\": true to show the Word window\n"
        "- \"split_screen\": true to arrange windows side-by-side\n\n"
        "Do NOT use bracketed placeholders like '[800 words on X]'. Always include full prose in the 'text' param. If the assistant_text must be brief, still ensure the action's 'text' param contains the complete content.\n\n"
        f"User: {user_text}\n"
    )


def _try_parse_json(raw: str):
    import json as _json
    # 1) direct parse
    try:
        return _json.loads(raw)
    except Exception:
        pass
    # 2) fenced code block
    if '```' in raw:
        parts = raw.split('```')
        for seg in parts:
            s = seg.strip()
            if s.lower().startswith('json'):
                s = s[4:].strip()
            try:
                return _json.loads(s)
            except Exception:
                continue
    # 3) first brace to last brace
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            return _json.loads(raw[start:end+1])
    except Exception:
        pass
    return None


def _detect_word_doc_intent(text: str) -> bool:
    """Detect if the user's text indicates they want to create a Word document."""
    text_lower = text.lower()
    # If the prompt clearly refers to building a web page/site/app in HTML, treat it as NOT a Word request
    web_exclusion_markers = [
        'html', 'homepage', 'home page', 'single page site', 'single-page site',
        'landing page', 'website', 'web site', 'webpage', 'css', 'javascript', 'single pager website'
    ]
    if any(m in text_lower for m in web_exclusion_markers):
        # Only bypass if the user did NOT explicitly mention wanting Word
        if ' word ' not in f' {text_lower} ' and ' docx' not in text_lower and 'document in word' not in text_lower:
            return False
    word_indicators = [
        "write a word document", "create a word document", "make a word document",
        "write a document", "create a document in word", "save as word document",
        "research paper", "write a paper", "save to desktop", "save to documents",
        "save as docx", "save as .docx", "type in word", "open word", "create a report",
        "write an essay", "create a letter", "write a report", "draft a document",
        "1000 word", "2000 word", "500 word", "page report", "page essay"
    ]
    
    return any(indicator in text_lower for indicator in word_indicators)

def _detect_vscode_intent(text: str) -> bool:
    """Detect if the user's text indicates they want to work with VS Code or code files."""
    text_lower = text.lower()
    
    # Check for VS Code specific keywords
    vscode_markers = [
        'vscode', 'visual studio code', 'vs code', 'code editor',
        'edit code', 'write code', 'coding', 'programming',
        'open in vs code', 'open in vscode', 'open with vs code',
        'html file', 'css file', 'javascript file', 'js file',
        'python file', 'code file', 'source code', 'repo',
        'repository', 'github', 'gitlab', 'coding environment',
        'development environment', 'ide'
    ]
    
    # Check for programming language mentions
    code_lang_markers = [
        'html', 'css', 'javascript', 'python', 'java', 'c#', 'c++', 
        'typescript', 'react', 'vue', 'angular', 'node.js', 'nodejs',
        'code snippet', 'function', 'class', 'method'
    ]
    
    # If request contains VS Code related terms, consider it a VS Code intent
    if any(marker in text_lower for marker in vscode_markers):
        return True
        
    # If request mentions code languages or programming concepts, consider it code-related
    return any(marker in text_lower for marker in code_lang_markers)

def _extract_word_count(text: str) -> int:
    """Extract word count requirement from text."""
    text_lower = text.lower()
    # Look for patterns like "1000 word essay" or "500-word paper"
    word_count_match = re.search(r'(\d+)[\s-]?word', text_lower)
    if word_count_match:
        return int(word_count_match.group(1))
    
    # Look for patterns like "5 page essay" (estimate 250 words per page)
    page_count_match = re.search(r'(\d+)[\s-]?page', text_lower)
    if page_count_match:
        return int(page_count_match.group(1)) * 250
    
    return 0

def _expand_placeholder_content(text: str) -> str:
    """Expand bracketed placeholders into full prose.
    Handles:
      - [Title: ...] -> inline title string (no brackets)
      - [N words on TOPIC], [N words about TOPIC], [N words covering TOPIC], etc.
      - If no explicit topic inside the brackets, uses nearby section heading as context.
    """
    if not text or '[' not in text or ']' not in text:
        return text or ''

    lines = text.split('\n')
    out_lines: list[str] = []
    for i, line in enumerate(lines):
        cur = line
        # Expand all bracketed chunks within the line
        while True:
            m = re.search(r'\[(.*?)\]', cur)
            if not m:
                break
            full = m.group(0)
            inner = (m.group(1) or '').strip()
            replacement = ''
            try:
                # 1) Title directive
                mt = re.match(r'^\s*title\s*:\s*(.+)$', inner, re.IGNORECASE)
                if mt:
                    replacement = mt.group(1).strip()
                else:
                    # 2) N-words directive variants
                    mn = re.match(r'^\s*(\d+)\s*words?\s*(?:on|about|covering|explaining)?\s*(.*)$', inner, re.IGNORECASE)
                    if mn:
                        n = int(mn.group(1))
                        topic = (mn.group(2) or '').strip().strip('.').strip()
                        # If topic absent, try to infer from previous non-empty line (section heading)
                        if not topic:
                            # Find previous non-empty line
                            section = ''
                            for j in range(i - 1, -1, -1):
                                prev = (lines[j] or '').strip()
                                if prev:
                                    section = prev
                                    break
                            topic = section or 'the requested topic'
                        # Build a focused prompt using section context
                        section_name = ''
                        # If current line (minus placeholder) looks like a heading, use it; else previous heading
                        cur_wo = (cur[:m.start()] + cur[m.end():]).strip()
                        if cur_wo and len(cur_wo.split()) <= 6:
                            section_name = cur_wo
                        if not section_name:
                            for j in range(i - 1, -1, -1):
                                prev = (lines[j] or '').strip()
                                if prev and len(prev.split()) <= 8:
                                    section_name = prev
                                    break
                        prompt = (
                            f"Write approximately {n} words for the section '{section_name or 'Body'}' on {topic}. "
                            "Use clear academic prose in full paragraphs, no outlines or placeholders, no bullet points, and no meta commentary."
                        )
                        replacement = generate_response(prompt) or ''
                    else:
                        # Unknown directive: drop brackets and keep inner content
                        replacement = inner
            except Exception as e:
                print(f"Error expanding placeholder: {e}")
                replacement = inner
            # Replace this occurrence only
            cur = cur[:m.start()] + replacement + cur[m.end():]
        out_lines.append(cur)
    return '\n'.join(out_lines)


def _ensure_content_length(content: str, target_count: int, topic: str) -> str:
    """Ensure content meets the required word count."""
    current_count = len(content.split())
    
    # If content is already sufficient, return it
    if current_count >= target_count * 0.8:
        return content
    
    # Otherwise, generate more comprehensive content
    expanded_prompt = (
        f"Generate a detailed, well-structured {target_count}-word document on {topic} with proper "
        f"introduction, thorough body paragraphs with detailed analysis, and a strong conclusion. "
        f"Include appropriate headings, transitions between sections, and citations if relevant. "
        f"The document must be comprehensive and approximately {target_count} words in length."
    )
    
    return generate_response(expanded_prompt)


def _augment_to_word_count(content: str, target_count: int, topic: str) -> str:
    """Append additional paragraphs to content to meet approximately target_count words.
    - If content already >= ~95% of target, return as-is.
    - Otherwise, generate additional paragraphs that continue the same topic and tone.
    """
    try:
        words = content.split()
        current = len(words)
        if current >= max(50, int(target_count * 0.95)):
            return content
        deficit = max(0, target_count - current)
        if deficit == 0:
            return content
        prompt = (
            f"The following is a partial draft for a document on {topic}.\n\n"
            f"Draft so far (do not rewrite, just continue):\n{content}\n\n"
            f"Please append additional cohesive paragraphs to bring the total to roughly {target_count} words. "
            f"Match the tone and structure. No outlines, no meta commentary, and no bracketed placeholders."
        )
        addition = generate_response(prompt) or ""
        # If model produced the whole thing again, prefer concatenation but avoid duplicating exactly
        if addition.strip() and addition.strip() not in content:
            return (content.rstrip() + "\n\n" + addition.strip())
        return content
    except Exception:
        return content


def _should_append_from_text(user_text: str) -> bool:
    """Decide whether to append to the existing document based on explicit phrasing.
    Default is False (replace). Returns True only if user clearly asks to add/append at the end/below.
    """
    try:
        t = (user_text or '').lower()
        # Strong append indicators
        patterns = [
            r"\bappend\b",
            r"add (?:it|this|the content|content|text)?\s+(?:at|to)\s+the\s+end",
            r"add (?:it|this|the content|content|text)?\s+below",
            r"(?:at|to)\s+the\s+bottom",
            r"append (?:it|this|content|text)?\s+(?:to|at)\s+the\s+(?:end|bottom)",
            r"continue (?:writing|the document)\s+(?:at|to)\s+the\s+end",
            r"add a section\s+(?:at|to)\s+the\s+end",
            r"add .* to the existing document",
            r"append .* to the existing document",
            r"add (?:more|another section)\s+(?:at|to)\s+the\s+end",
        ]
        for pat in patterns:
            if re.search(pat, t):
                return True
        # Strong replace indicators (override any weak mentions)
        replace_markers = [
            'replace', 'overwrite', 'rewrite', 'start over', 'replace the whole', 'rewrite completely'
        ]
        if any(k in t for k in replace_markers):
            return False
        return False
    except Exception:
        return False


def _normalize_action_type(t: str) -> str:
    """Normalize minor variations in action type names from the planner, with fuzzy fallback."""
    if not t:
        return t
    low = t.strip().lower()
    # common variants
    if low in ("word.createdocument", "word.create-doc", "word.create.doc", "word.create_doc", "word.createdoc"):
        return "word.create_document"
    if low in ("word.openandtype", "word.open_and_type", "word.typeinword", "word.type", "word.open-and-type", "word.open_andtype"):
        return "word.open_and_type"
    if low in ("fs.createfolder", "fs.mkdir", "fs.create-folder"):
        return "fs.create_folder"
    if low in ("fs.writefile", "fs.write-file", "fs.savefile"):
        return "fs.write_file"
    if low in ("fs.mirror", "fs.mirror_to_docs", "fs.mirrortodocuments", "fs.mirror_to_documents"):
        return "fs.mirror_to_documents"
    if low in ("open.vscode", "automation.open_vscode", "automation.open-vscode", "open_vscode"):
        return "automation.open_vscode"
    # fuzzy fallback across supported tools
    supported = ["fs.create_folder", "fs.write_file", "fs.mirror_to_documents", "word.create_document", "word.open_and_type", "automation.open_vscode"]
    match = difflib.get_close_matches(low, supported, n=1, cutoff=0.72)
    return match[0] if match else low

def _normalize_params(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Map parameter aliases to expected names per action type."""
    p = dict(params or {})
    at = action_type
    if at == "word.create_document":
        # target_rel aliases
        if "target" in p and "target_rel" not in p:
            p["target_rel"] = p.pop("target")
        if "path" in p and "target_rel" not in p:
            p["target_rel"] = p.pop("path")
        if "targetrel" in p and "target_rel" not in p:
            p["target_rel"] = p.pop("targetrel")
        # paragraph/content aliases
        if "content" in p and "paragraph" not in p:
            p["paragraph"] = p.pop("content")
    elif at == "word.open_and_type":
        # Accept content aliases
        if "content" in p and "text" not in p:
            p["text"] = p.pop("content")
        if "paragraph" in p and "text" not in p and isinstance(p["paragraph"], str):
            # Keep paragraph as secondary, but prefer mapping to text
            p["text"] = p.get("text") or p["paragraph"]
        # Save path aliases
        if "savetarget" in p and "save_target" not in p:
            save_target_value = p.pop("savetarget")
            if isinstance(save_target_value, str) and '/' in save_target_value:
                parts = save_target_value.split('/', 1)
                if parts[0].lower() in ['desktop', 'documents', 'downloads']:
                    p["save_target"] = parts[0].lower()
                    p["filename"] = parts[1] if len(parts) > 1 else None
                else:
                    p["save_target"] = save_target_value
            else:
                p["save_target"] = save_target_value
        if "savepath" in p and "save_target" not in p:
            p["save_target"] = p.pop("savepath")
        if "target_rel" in p and "save_target" not in p:
            p["save_target"] = p.pop("target_rel")
        if "path" in p and "save_target" not in p:
            p["save_target"] = p.pop("path")
        if "filepath" in p and "save_target" not in p:
            p["save_target"] = p.pop("filepath")
        # Visibility aliases
        if "showwindow" in p and "show_window" not in p:
            p["show_window"] = p.pop("showwindow")
        if "showWindow" in p and "show_window" not in p:
            p["show_window"] = p.pop("showWindow")
        if "visible" in p and "show_window" not in p:
            p["show_window"] = p.pop("visible")
        # Split-screen aliases
        if "splitscreen" in p and "split_screen" not in p:
            p["split_screen"] = p.pop("splitscreen")
        if "splitScreen" in p and "split_screen" not in p:
            p["split_screen"] = p.pop("splitScreen")
        # Infer save location from content if not explicitly set
        content_for_scan = (p.get("text") or p.get("paragraph") or "").lower()
        if content_for_scan and not p.get("save_target"):
            location_matches = re.findall(r'(?:save|store|place|put|create|write)(?:\s+(?:it|this|file|document|paper))?(?:\s+(?:to|in|on|at))?\s+(desktop|documents?|downloads?|my documents?|my desktop|my downloads?)(?:\s+folder)?', content_for_scan)
            if location_matches:
                location = location_matches[0]
                if location in ['desktop', 'my desktop']:
                    p["save_target"] = "desktop"
                elif location in ['documents', 'document', 'my documents', 'my document']:
                    p["save_target"] = "documents"
                elif location in ['downloads', 'download', 'my downloads', 'my download']:
                    p["save_target"] = "downloads"
        # If saving is mentioned but no specific location, default to desktop for visibility
        if not p.get("save_target") and any(w in content_for_scan for w in ['save', 'store', 'write to', 'create on']):
            p["save_target"] = "desktop"
        # Defaults for window handling and snapping
        p["show_window"] = p.get("show_window", True)
        p["split_screen"] = p.get("split_screen", True)
        p["use_os_snap_keys"] = p.get("use_os_snap_keys", True)
        p["use_cua_for_selection"] = p.get("use_cua_for_selection", True)
        p["arrangement_delay_ms"] = p.get("arrangement_delay_ms", 800)
        p["word_side"] = p.get("word_side", "right")
        # Prefer HTTP transport by default so the automation API call is visible in logs
        if "transport" not in p and not p.get("force_inproc"):
            p["transport"] = "http"
    elif at == "fs.write_file":
        if "path" in p and "relative_path" not in p:
            p["relative_path"] = p.pop("path")
        if "text" in p and "content" not in p:
            p["content"] = p.pop("text")
        if "encoding" not in p:
            p["encoding"] = "utf-8"
    elif at == "fs.create_folder":
        if "parent" in p and "parent_path" not in p:
            p["parent_path"] = p.pop("parent")
    return p


@router.post('/power_chat', response_model=PowerChatResponse)
def power_chat(req: PowerChatRequest) -> PowerChatResponse:
    try:
        print(f"POWER_CHAT_START: auto_execute={bool(getattr(req,'auto_execute',True))} service={getattr(req,'service',None)} chat_id={getattr(req,'chat_id',None)}")
    except Exception:
        pass
    # Force auto-execution on server for reliability (ignore client toggle for Power Mode)
    try:
        if getattr(req, 'auto_execute', True) is not True:
            print("POWER_CHAT_FORCE_AUTOEXEC: overriding client auto_execute to True")
        req.auto_execute = True
    except Exception:
        try:
            print("POWER_CHAT_FORCE_AUTOEXEC: failed to override auto_execute; proceeding anyway")
        except Exception:
            pass
    # If no explicit mem_context provided, augment with persistent tags for this chat (if any)
    mem_ctx = req.mem_context
    st = None
    if not mem_ctx:
        st = _chat_state_get(req.chat_id, req.service)
        if st and st.get('persistent_tags'):
            tags_str = ', '.join(st['persistent_tags'])
            mem_ctx = f"Persistent tags for this chat: {tags_str}"

    # Surface explicit URLs from memory items when tags are present (parity with /api/chat)
    try:
        used_tags: list[str] = []
        # Prefer tags sent by client; else fall back to persistent tags if we used them
        if getattr(req, 'mem_tags', None):
            used_tags = [str(t).strip() for t in (req.mem_tags or []) if t and str(t).strip()]
        elif getattr(req, 'selected_tags', None):
            used_tags = [str(t).strip() for t in (req.selected_tags or []) if t and str(t).strip()]
        elif (not getattr(req, 'mem_context', None)) and st and st.get('persistent_tags'):
            # Only use persistent tags if mem_context wasn't explicitly provided
            used_tags = [str(t).strip() for t in (st.get('persistent_tags') or []) if t and str(t).strip()]

        if used_tags:
            import sqlite3 as _sqlite3
            conn2 = _sqlite3.connect(DB_PATH)
            c2 = conn2.cursor()
            previews = []
            seen_ids = set()
            for t in used_tags:
                like = f"%{t}%"
                try:
                    c2.execute(
                        'SELECT id, substr(text_content,1,1000) as preview, filename FROM mem_item '
                        'WHERE (tags LIKE ? OR filename LIKE ?) AND ('
                        'text_content LIKE "%http%" OR text_content LIKE "%www.%") '
                        'ORDER BY id DESC LIMIT 20', (like, like)
                    )
                    for rid, prev, fn in c2.fetchall() or []:
                        if rid in seen_ids:
                            continue
                        seen_ids.add(rid)
                        previews.append(prev or '')
                except Exception:
                    continue
            try:
                conn2.close()
            except Exception:
                pass
            # Extract URLs
            urls: list[str] = []
            if previews:
                url_re = re.compile(r'https?://[^\s)]+', re.IGNORECASE)
                for pv in previews:
                    for m in url_re.findall(pv or ''):
                        u = m.strip().rstrip('.,);]')
                        if u and u not in urls:
                            urls.append(u)
                        if len(urls) >= 20:
                            break
                    if len(urls) >= 20:
                        break
            if urls:
                block = "Relevant links from memory (by tags: " + ", ".join(used_tags) + "):\n" + "\n".join([f"- {u}" for u in urls])
                mem_ctx = (mem_ctx + "\n" + block) if mem_ctx else block
    except Exception:
        pass
    history_ctx = _get_recent_chat_history(req.chat_id, req.service, limit=6, char_limit=2400)
    if history_ctx:
        history_block = "Recent conversation (oldest to newest):\n" + history_ctx
        mem_ctx = (mem_ctx + "\n\n" + history_block) if mem_ctx else history_block

    inline_attempt = _maybe_handle_inline_selection(req, mem_ctx)
    if inline_attempt:
        assistant_text = inline_attempt.get("assistant_text", "Updated the selected content.")
        try:
            _persist_power_chat_row(req, assistant_text)
        except Exception:
            pass
        try:
            tags = req.mem_tags or req.selected_tags or None
            _chat_state_upsert(req.chat_id, req.service, tags, None)
        except Exception:
            pass
        return PowerChatResponse(
            assistant_text=assistant_text,
            actions=[],
            execute_result=inline_attempt.get("execute_result")
        )
    raw = generate_response(_planner_prompt(req.text, mem_ctx))
    # ---------------- New multi-stage JSON parsing with strict repair pass ----------------
    def _strict_json_repair_call(raw_text: str) -> Optional[dict]:
        """Second-pass: ask LLM to emit ONLY strict JSON object; return dict or None."""
        repair_prompt = (
            "You will be given a noisy assistant output that was SUPPOSED to be a single JSON object.\n"
            "Return ONLY the corrected strict JSON object. Absolutely NOTHING else.\n"
            "Rules:\n- No markdown fences\n- No commentary\n- No trailing commas\n- Single JSON object with double quoted keys/strings\n"
            "If unfixable respond exactly with {} (just curly braces).\n\n"
            f"NOISY_INPUT_START\n{raw_text}\nNOISY_INPUT_END\n"
        )
        try:
            repaired = generate_response(repair_prompt)
            if not repaired:
                return None
            cleaned = repaired.strip()
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
            import json as _json
            return _json.loads(cleaned)
        except Exception:
            return None

    def _parse_or_retry_actions(raw_text: str) -> tuple[Optional[dict], str]:
        import json as _json
        # 1 direct
        try:
            return _json.loads(raw_text), 'direct'
        except Exception:
            pass
        # 2 salvage substring from first { to last }
        brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if brace_match:
            fragment = brace_match.group(0)
            try:
                return _json.loads(fragment), 'salvage'
            except Exception:
                pass
        # 3 repair call
        repaired_obj = _strict_json_repair_call(raw_text)
        if repaired_obj is not None:
            return repaired_obj, 'repair'
        return None, 'fail'

    obj, parse_stage = _parse_or_retry_actions(raw)
    if obj is None or not isinstance(obj, dict):
        try:
            print("POWER_CHAT_PARSE_FALLBACK: stage=fail (direct+salvage+repair); aborting actions")
        except Exception:
            pass
        fail_msg = ("I couldn't produce a valid structured action plan (JSON parse failed). "
                    "Please restate succinctly or specify the exact file / document you want.")
        try:
            _persist_power_chat_row(req, fail_msg)
        except Exception:
            pass
        return PowerChatResponse(assistant_text=fail_msg, actions=[], execute_result=None)
    else:
        try:
            print(f"POWER_CHAT_JSON_PARSE_SUCCESS stage={parse_stage}")
        except Exception:
            pass
    # ------------------------------------------------------------------------------
    # Existing logic after successful obj parsing continues below (web intent injection block removed)
    # (Note: removed heuristic Word/HTML injection on parse failure per user request.)
    low = req.text.lower()
    # (Removed old heuristic HTML/Word fallback block due to strict JSON policy.)
    # tolerate alternate key spellings from model outputs
    assistant_text = str(
        obj.get("assistant_text")
        or obj.get("assistanttext")
        or obj.get("assistant")
        or obj.get("text")
        or ""
    ).strip()
    actions = obj.get("actions") or []
    if not isinstance(actions, list):
        actions = []
    normed: List[ProposedAction] = []
    for a in actions:
        try:
            t_raw = str(a.get("type") or "").strip()
            print(f"Processing action type: {t_raw}")
            t = _normalize_action_type(t_raw)
            print(f"Normalized action type: {t}")
            p = a.get("params") or {}
            print(f"Original params: {p}")
            p = _normalize_params(t, p)
            print(f"Normalized params: {p}")
            if t in TOOL_SPEC and isinstance(p, dict):
                normed.append(ProposedAction(type=t, params=p))
            else:
                print(f"Warning: Action type '{t}' not in TOOL_SPEC or params is not a dict")
        except Exception as e:
            print(f"Error normalizing action: {e}")
            continue

    # Post-normalization rewrite for default website generation: unify to a single relocation flow
    try:
        docs_base = _get_standard_user_folder('documents')
        docs_folder = os.path.join(str(docs_base), 'SarvajnaGPT', 'web')
        os.makedirs(docs_folder, exist_ok=True)
        final_default = os.path.join(docs_folder, 'index.html').replace('\\', '/')
        
        # First, find HTML file paths and collect their file names for better handling
        html_files = {}
        found_default_write = False
        
        for pa in normed:
            if pa.type == 'fs.write_file':
                rel = (pa.params.get('relative_path') or '').lower()
                if rel.endswith('.html') or rel in ('files/output.html','files/generated.txt','index.html','files/site.html') or not rel:
                    # Remember the original path and associate with its content
                    filename = os.path.basename(rel) if os.path.basename(rel) else 'index.html'
                    if not filename.lower().endswith('.html'):
                        filename = 'index.html'
                    html_files[rel] = filename
                    
                    # Mark the default parameters
                    pa.params['relative_path'] = f'files/{filename}'
                    pa.params['__default_site__'] = True
                    found_default_write = True
        if found_default_write:
            # Remove pre-existing open_vscode/mirror for sandbox and append a unified one targeting final path.
            filtered: list[ProposedAction] = []
            main_html_file = None
            
            # Find which HTML file should be the main one to open (prefer index.html)
            if html_files:
                if 'files/index.html' in html_files or 'index.html' in html_files:
                    main_html_file = 'index.html'
                else:
                    # Use the first HTML file we found
                    main_html_file = list(html_files.values())[0]
            
            # If we didn't find any HTML files, default to index.html
            if not main_html_file:
                main_html_file = 'index.html'
                
            # Build the correct path to the main file
            final_path = os.path.join(docs_folder, main_html_file).replace('\\', '/')
            
            # Filter out VS Code and mirror actions, we'll add our own
            for pa in normed:
                if pa.type == 'automation.open_vscode':
                    # Skip; we'll append our own canonical opening
                    continue
                if pa.type == 'fs.mirror_to_documents':
                    # Skip redundant mirror; relocation will handle placement
                    continue
                filtered.append(pa)
                
                # Append canonical VS Code open with ABSOLUTE path to Documents location
                filtered.append(ProposedAction(type='automation.open_vscode', params={
                    'path': final_path,
                    'split_screen': True,  # Always force split_screen to true
                    'vscode_side': 'right', 
                    '__default_site__': True
                }))            # Update the chat state with the final path
            if getattr(req, 'chat_id', None):
                try:
                    _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, final_path)
                except Exception as _e_db:
                    print(f"POWER_CHAT_POSTREWRITE_DB_ERR: {_e_db}")
                    
            normed = filtered
            print(f'POWER_CHAT_POSTREWRITE: enforced default site path={final_path} and canonical VS Code open')
    except Exception as _e_postrewrite:
        try:
            print(f"POWER_CHAT_POSTREWRITE_ERR: {_e_postrewrite}")
        except Exception:
            pass

    # Auto-inject VS Code reopen for existing chat code file if no open action planned
    try:
        has_open = any(a.type == 'automation.open_vscode' for a in normed)
        has_write = any(a.type == 'fs.write_file' for a in normed)
        st2 = _chat_state_get(req.chat_id, req.service)
        doc_path_existing = (st2 or {}).get('doc_path') if st2 else None
        if doc_path_existing and not has_open and not has_write:
            # Only inject if looks like a code file and user didn't ask NOT to open
            low_ut = req.text.lower()
            if 'do not open' not in low_ut and 'dont open' not in low_ut and 'no open' not in low_ut:
                ext = os.path.splitext(doc_path_existing)[1].lower()
                if ext in ('.html', '.htm', '.js', '.css', '.py', '.md', '.txt') and os.path.isfile(doc_path_existing):
                    # Map absolute path back to relative under agent_output if possible
                    rel_for_action = None
                    try:
                        rel_for_action = os.path.relpath(doc_path_existing, AGENT_BASE_DIR)
                    except Exception:
                        rel_for_action = doc_path_existing
                    normed.insert(0, ProposedAction(type='automation.open_vscode', params={
                        'path': rel_for_action.replace('\\','/'),
                        'focus': True,
                        'split_screen': True,
                        'vscode_side': 'right'
                    }))
                    try:
                        print(f"POWER_CHAT_INJECT_VSCODE_REOPEN: path={rel_for_action}")
                    except Exception:
                        pass
    except Exception as _einject_vs:
        try:
            print(f"POWER_CHAT_INJECT_VSCODE_ERR: {_einject_vs}")
        except Exception:
            pass
            
    # Check if this is a Word document request without Word actions
    if not any(a.type.startswith("word.") for a in normed):
        # Use our helper function to detect Word document requests
        is_word_request = _detect_word_doc_intent(req.text)
        
        # If it looks like a Word document request, add a word.open_and_type action
        if is_word_request:
            # Extract topic from the user request for better content generation
            topic_match = re.search(r'(?:about|on|regarding|for|about)\s+([^,.!?]+)', req.text.lower())
            topic = topic_match.group(1).strip() if topic_match else "the requested topic"
            
            # Determine save location
            save_target = None
            user_text_lower = req.text.lower()
            
            # Check for save location in the text
            if "desktop" in user_text_lower:
                save_target = "desktop"
            elif "documents" in user_text_lower:
                save_target = "documents"
            elif "downloads" in user_text_lower:
                save_target = "downloads"
            
            # If no explicit location found, default to desktop for visibility
            if not save_target:
                save_target = "desktop"

            # If chat already has a document path, prefer updating the same file
            try:
                st = _chat_state_get(req.chat_id, req.service)
                if st and st.get('doc_path'):
                    save_target = st['doc_path']
                    print(f"POWER_CHAT_INJECT: using existing doc_path for save_target: {save_target}")
            except Exception:
                pass
            
            # Extract word count requirement and ensure content meets it
            target_word_count = _extract_word_count(req.text)
            if target_word_count > 0:
                # Ensure content meets the required length
                assistant_text = _ensure_content_length(assistant_text, target_word_count, topic)
            
            # Add the word.open_and_type action
            normed.append(ProposedAction(
                type="word.open_and_type",
                params={
                    "text": assistant_text,
                    "show_window": True,
                    "split_screen": True,
                    "save_target": save_target,
                    "use_cua_for_selection": True,
                    "append": _should_append_from_text(req.text)
                }
            ))
            
            # Modify the assistant text to include information about the document creation
            assistant_text += "\n\n[I've created a Word document with this content and saved it to your " + save_target + ".]"
    # Check existing Word actions for content length
    else:
        # Extract word count requirements from user request
        user_text_lower = req.text.lower()
        word_count_match = re.search(r'(\d+)[\s-]?word', user_text_lower)
        if word_count_match:
            target_word_count = int(word_count_match.group(1))
            
            # Check each word action
            for action in normed:
                if action.type.startswith("word."):
                    text_content = action.params.get("text", "") or action.params.get("paragraph", "")
                    current_word_count = len(text_content.split())
                    
                    # If content is less than 80% of requested word count, add a note in assistant_text
                    if current_word_count < target_word_count * 0.8:
                        assistant_text += f"\n\n[Note: The document content is only about {current_word_count} words, which is less than the requested {target_word_count} words. I'll expand the content to meet your requirements.]"
            
    # Optionally auto-execute proposed actions to guarantee end-to-end flow
    exec_result = None
    if req.auto_execute and normed:
        # Reorder so automation.open_vscode (if any) runs immediately after file creation and before mirror
        try:
            types = [a.type for a in normed]
            if 'automation.open_vscode' in types and 'fs.mirror_to_documents' in types:
                ov_idx = types.index('automation.open_vscode')
                # Mirror might occur before open_vscode due to model drift; enforce order
                # Move all mirror actions to after the last open_vscode
                last_ov_idx = max(i for i,t in enumerate(types) if t=='automation.open_vscode')
                new_list = []
                mirrors = []
                for i,a in enumerate(normed):
                    if a.type == 'fs.mirror_to_documents':
                        mirrors.append(a)
                    else:
                        new_list.append(a)
                # Insert mirrors after last open_vscode position
                # Find updated index of last open_vscode in new_list
                ov_positions = [i for i,a in enumerate(new_list) if a.type=='automation.open_vscode']
                if ov_positions:
                    insert_at = ov_positions[-1] + 1
                    normed = new_list[:insert_at] + mirrors + new_list[insert_at:]
        except Exception:
            pass
        try:
            # For all word actions: expand placeholders and ensure approx target word count
            target_wc = _extract_word_count(req.text)
            # Try to extract topic from user request for better augmentation
            tmatch = re.search(r'(?:about|on|regarding|for)\s+([^,.!?\n]+)', req.text, re.IGNORECASE)
            topic = (tmatch.group(1).strip() if tmatch else '').strip() or 'the requested topic'
            append_flag = _should_append_from_text(req.text)
            for action in normed:
                if action.type.startswith("word."):
                    text_content = action.params.get("text") or action.params.get("paragraph") or ""
                    # Decide append vs replace
                    action.params["append"] = bool(append_flag)
                    # Placeholder expansion
                    if isinstance(text_content, str) and ('[' in text_content and ']' in text_content):
                        try:
                            expanded = _expand_placeholder_content(text_content)
                            action.params["text"] = expanded
                            text_content = expanded
                            print(f"POWER_CHAT_EXPANDED_PLACEHOLDERS: length={len(expanded)}")
                        except Exception as _eph:
                            print(f"POWER_CHAT_EXPAND_ERR: {_eph}")
                    # Augment to target word count when user specified one
                    if isinstance(text_content, str) and target_wc and len(text_content.split()) < int(target_wc * 0.92):
                        try:
                            augmented = _augment_to_word_count(text_content, target_wc, topic)
                            action.params["text"] = augmented
                            print(f"POWER_CHAT_AUGMENTED_TO_TARGET: target={target_wc} final_words={len(augmented.split())}")
                        except Exception as _eaug:
                            print(f"POWER_CHAT_AUGMENT_ERR: {_eaug}")
            try:
                print(f"POWER_CHAT_AUTOEXEC: actions_count={len(normed)} types={[a.type for a in normed]}")
            except Exception:
                pass
            exec_result = power_execute(ExecuteActionsRequest(actions=normed, chat_id=req.chat_id, service=req.service))
            try:
                if isinstance(exec_result, dict):
                    print(f"POWER_CHAT_AUTOEXEC_DONE: keys={list(exec_result.keys())}")
            except Exception:
                pass
        except Exception as e:
            exec_result = {"error": str(e)}
    # Persist this exchange into chat table (service=power_mode)
    try:
        _persist_power_chat_row(req, assistant_text)
    except Exception:
        pass
    # Upsert persistent tags for this chat
    try:
        tags = req.mem_tags or req.selected_tags or None
        _chat_state_upsert(req.chat_id, req.service, tags, None)
    except Exception:
        pass
    # If we have a saved_path from execution, append a confirmation line to assistant_text for UX clarity
    try:
        assistant_text = _augment_assistant_with_exec(assistant_text, exec_result)
    except Exception:
        pass
    # Hide actions/execute_result from response to avoid frontend showing "power execute" UI
    return PowerChatResponse(assistant_text=assistant_text or "", actions=[], execute_result=None)

class ExecuteActionsRequest(BaseModel):
    actions: List[ProposedAction]
    chat_id: Optional[str] = None
    service: Optional[str] = None


def _to_safe_rel_path(p: Optional[str], default_dir: str, default_filename: Optional[str] = None) -> str:
    """Map any absolute or Desktop-like path to a safe relative path under agent_output.
    - Converts backslashes to forward slashes.
    - Drops drive letters and leading slashes.
    - If mentions 'desktop', prefix under 'desktop/'.
    - If empty, use default_dir/(default_filename or 'output.txt').
    """
    try:
        s = (p or '').strip()
        s = s.replace('\\', '/')
        low = s.lower()
        # remove drive like C:/ or leading/
        if ':' in s:
            s = s.split(':', 1)[1]
        s = s.lstrip('/')

        # If path contains "desktop", keep it under desktop/
        if 'desktop' in low:
            parts = s.split('/')
            # remove desktop component and any empty parts
            parts = [p for p in parts if p and p.lower() != 'desktop']
            if parts:
                s = f"desktop/{'/'.join(parts)}"
            else:
                s = f"desktop/{default_filename or 'output.txt'}"
        # if directory or path not provided, use defaults
        if not s:
            # Default: place in Documents/SarvajnaGPT if this is for files (default_dir == 'files')
            if default_dir == 'files':
                docs = _get_standard_user_folder('documents')
                target_root = os.path.join(str(docs), 'SarvajnaGPT')
                os.makedirs(target_root, exist_ok=True)
                fname = default_filename or 'output.html'
                # Return absolute path so downstream logic can persist absolute path
                return os.path.join(target_root, fname).replace('\\','/')
            if default_filename:
                s = f"{default_dir}/{default_filename}"
            else:
                s = f"{default_dir}/output.txt"
        elif s.endswith('/'):
            # it's a directory request
            s = f"{s}{default_filename or 'output.txt'}"
        return s
    except Exception:
        if default_filename:
            return f"{default_dir}/{default_filename}"
        return f"{default_dir}/output.txt"
        # pick base folder
        base = 'desktop' if 'desktop' in low else default_dir.strip('/ ')
        if not s:
            tail = default_filename or 'output.txt'
        else:
            tail = s
        # ensure no directory traversal
        tail = '/'.join([seg for seg in tail.split('/') if seg not in ('', '.', '..')])
        rel = f"{base}/{tail}" if base else tail
        return rel
    except Exception:
        return f"{default_dir.strip('/ ')}/{default_filename or 'output.txt'}"


@router.post('/power_execute')
def power_execute(req: ExecuteActionsRequest) -> dict:
    results = []
    try:
        print(f"POWER_EXEC_START: actions={len(getattr(req,'actions',[]) or [])} chat_id={getattr(req,'chat_id',None)}")
    except Exception:
        pass
    # Pre-scan to know if planner already intends to open VS Code (to avoid duplicate auto open)
    try:
        planned_open_vscode = any(_normalize_action_type(x.type)=='automation.open_vscode' for x in (getattr(req,'actions',[]) or []))
    except Exception:
        planned_open_vscode = False
    for a in req.actions:
        atype = _normalize_action_type(a.type)
        try:
            print(f"POWER_EXEC_ACTION: raw_type={a.type} norm_type={atype}")
        except Exception:
            pass
        params = _normalize_params(atype, a.params)
        try:
            print(f"POWER_EXEC_PARAMS: keys={list((params or {}).keys())}")
        except Exception:
            pass
        if atype == 'fs.create_folder':
            safe_parent = _to_safe_rel_path(params.get("parent_path", ""), default_dir='folders')
            action = FsAction(type=FsActionType.FS_CREATE_FOLDER, params={"parent_path": safe_parent, "name": params.get("name", "")})
            prev = fs_preview(action)
            res = fs_execute([action])
            results.append({"type": atype, "preview": prev, "result": res})
        elif atype == 'fs.write_file':
            # Direct-to-Documents strategy (removes sandbox write):
            rel_candidate = params.get('relative_path') or params.get('absolute_path') or ''
            raw_content = params.get('content', '') or ''
            # Extract raw code from a single <code lang="py">...</code> (quotes around lang optional)
            code_match = re.search(r"<code\s+lang=[\"']?([a-zA-Z0-9_.-]+)[\"']?>([\s\S]*?)</code>", raw_content)
            extracted_lang = None
            if code_match:
                extracted_lang = code_match.group(1).strip('.').lower()
                raw_content = code_match.group(2).replace('\r\n','\n')
            # Determine extension & target folder
            ext_map = {'py':'.py','python':'.py','js':'.js','ts':'.ts','html':'.html','htm':'.html','css':'.css','json':'.json','md':'.md','txt':'.txt'}
            inferred_ext = ext_map.get(extracted_lang or '', None)
            # Build filename if missing
            base_name = os.path.splitext(os.path.basename(rel_candidate))[0] if rel_candidate else 'generated'
            if not base_name:
                base_name = 'generated'
            existing_ext = os.path.splitext(rel_candidate)[1] if rel_candidate else ''
            if not existing_ext:
                if inferred_ext:
                    filename = base_name + inferred_ext
                else:
                    filename = base_name + '.py'
            else:
                filename = base_name + existing_ext
            # Decide subfolder (web for html, code for others)
            try:
                docs = _get_standard_user_folder('documents')
            except Exception:
                docs = Path.home() / 'Documents'
            sub_root = 'web' if filename.lower().endswith(('.html','.htm')) else 'code'
            # Rebuild any provided relative subdirectories (except path traversal tokens)
            rel_dirs = []
            if rel_candidate:
                parts = [p for p in rel_candidate.replace('\\','/').split('/')[:-1] if p and p not in ('.','..')]
                rel_dirs = parts
            target_dir = os.path.abspath(os.path.join(str(docs), 'SarvajnaGPT', sub_root, *rel_dirs))
            os.makedirs(target_dir, exist_ok=True)
            dest_path = os.path.abspath(os.path.join(target_dir, filename))
            try:
                with open(dest_path, 'w', encoding=params.get('encoding','utf-8')) as f:
                    f.write(raw_content)
                print(f"POWER_EXEC_WRITE_DOCS: {dest_path}")
            except Exception as _e_write:
                results.append({"type": atype, "error": True, "detail": f"WRITE_FAIL: {_e_write}"})
                continue
            # Persist chat state
            try:
                if getattr(req,'chat_id',None):
                    _chat_state_upsert(req.chat_id, getattr(req,'service',None), None, dest_path)
                    try:
                        conn_u = sqlite3.connect(DB_PATH)
                        cu = conn_u.cursor()
                        cu.execute('SELECT id FROM chat WHERE chat_id=? ORDER BY id DESC LIMIT 1', (req.chat_id,))
                        row = cu.fetchone()
                        if row:
                            cu.execute('UPDATE chat SET doc_info=? WHERE id=?', (dest_path, row[0]))
                            conn_u.commit()
                        conn_u.close()
                    except Exception as _e_db:
                        print(f"POWER_EXEC_WRITE_DOCS_DB_ERR: {_e_db}")
            except Exception as _e_state:
                print(f"POWER_EXEC_WRITE_DOCS_STATE_ERR: {_e_state}")
            results.append({"type": atype, "path": dest_path, "error": False})
            # Auto open VS Code if planner didn\'t request it
            if not planned_open_vscode:
                try:
                    vs_res = _open_vscode_path(dest_path, side='right', split=True)
                    results.append({"type": 'automation.open_vscode', "auto": True, "result": vs_res})
                    print(f"POWER_EXEC_AUTO_VSCODE_DOCS: {dest_path}")
                except Exception as _e_vsc:
                    print(f"POWER_EXEC_AUTO_VSCODE_DOCS_ERR: {_e_vsc}")
            continue
        elif atype == 'automation.open_vscode':
            # Reworked to delegate to automation_router for CUA-enabled snapping & tab focusing
            try:
                path_param = params.get('path') or 'files'
                print(f"VSCODE_CUA: Initial path_param={path_param}")

                # If tagged default site ensure absolute Documents web path (retain prior behavior)
                if params.get('__default_site__'):
                    try:
                        docs_base = _get_standard_user_folder('documents')
                        filename = os.path.basename(path_param) if os.path.basename(path_param) else 'index.html'
                        docs_path = os.path.abspath(os.path.join(str(docs_base), 'SarvajnaGPT', 'web', filename))
                        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
                        path_param = docs_path
                        print(f"VSCODE_CUA: Forced web docs path -> {docs_path}")
                        if getattr(req, 'chat_id', None):
                            try:
                                _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, docs_path)
                                conn_u = sqlite3.connect(DB_PATH)
                                cu = conn_u.cursor()
                                cu.execute('SELECT id FROM chat WHERE chat_id=? ORDER BY id DESC LIMIT 1', (req.chat_id,))
                                row = cu.fetchone()
                                if row:
                                    cu.execute('UPDATE chat SET doc_info=? WHERE id=?', (docs_path, row[0]))
                                    conn_u.commit()
                                conn_u.close()
                            except Exception as _db_err:
                                print(f"VSCODE_CUA: doc_info update failed: {_db_err}")
                    except Exception as _e_docs:
                        print(f"VSCODE_CUA: docs path set error: {_e_docs}")

                # Prefer previously persisted absolute doc_path when relative placeholder provided
                try:
                    if getattr(req,'chat_id',None) and not os.path.isabs(path_param) and not params.get('__default_site__'):
                        st = _chat_state_get(getattr(req,'chat_id'), getattr(req,'service',None))
                        existing_doc = (st or {}).get('doc_path')
                        if existing_doc and os.path.isfile(existing_doc):
                            path_param = existing_doc
                            print(f"VSCODE_CUA: Using persisted doc_path {existing_doc}")
                except Exception as _e_st:
                    print(f"VSCODE_CUA: chat_state lookup error: {_e_st}")

                # Resolve to absolute path (allow creation for not yet existing file)
                if not os.path.isabs(path_param):
                    safe_rel = _to_safe_rel_path(path_param, default_dir='files', default_filename=None)
                    abs_path = os.path.join(AGENT_BASE_DIR, safe_rel)
                    print(f"VSCODE_CUA: Relative -> {abs_path}")
                else:
                    abs_path = path_param
                    print(f"VSCODE_CUA: Absolute path detected {abs_path}")
                # Ensure directory exists so VS Code can create new file
                try:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                except Exception:
                    pass

                # Build request payload for automation_router
                code_side = params.get('vscode_side') or 'right'
                split_screen = params.get('split_screen', True)
                # Override an explicit False from planner to maintain consistent UX (always split for first opens)
                if split_screen is False:
                    try:
                        print("VSCODE_CUA: Overriding split_screen=False -> True for consistency")
                    except Exception:
                        pass
                    split_screen = True
                http_payload = {
                    'abs_path': abs_path,
                    'split_screen': bool(split_screen),
                    'code_side': code_side,
                    'use_os_snap_keys': True,
                    'use_cua_for_selection': True,
                    'arrangement_delay_ms': 1000,
                }
                http_mode = True  # always attempt HTTP first (mirrors word logic simplification)
                result_obj = None
                transport_used = None
                if http_mode:
                    try:
                        import requests  # type: ignore
                        base_url = os.environ.get('API_BASE_URL') or 'http://localhost:8000'
                        endpoint = base_url.rstrip('/') + '/api/automation/vscode/open_existing'
                        print(f"VSCODE_CUA_HTTP: POST {endpoint} path={abs_path}")
                        resp = requests.post(endpoint, json=http_payload, timeout=40)
                        if resp.ok:
                            result_obj = resp.json()
                            transport_used = 'http'
                        else:
                            print(f"VSCODE_CUA_HTTP_ERR: {resp.status_code} {resp.text[:180]}")
                    except Exception as _http_e:
                        print(f"VSCODE_CUA_HTTP_EXC: {_http_e}")

                # In-process fallback if HTTP failed or returned error
                if not isinstance(result_obj, dict) or not result_obj.get('opened', True):
                    try:
                        from automation_router import VSCodeOpenRequest, vscode_open_existing  # type: ignore
                        req_obj = VSCodeOpenRequest(**http_payload)
                        print("VSCODE_CUA_INPROC: calling vscode_open_existing fallback")
                        result_obj = vscode_open_existing(req_obj)
                        transport_used = (transport_used or '') + ('+inproc' if transport_used else 'inproc')
                    except Exception as _inproc_e:
                        print(f"VSCODE_CUA_INPROC_ERR: {_inproc_e}")
                        result_obj = {'error': f'inproc_failed: {_inproc_e}'}

                if isinstance(result_obj, dict):
                    result_obj['transport'] = transport_used
                else:
                    result_obj = {'error': 'unexpected_result_type'}

                # Persist doc_path if successfully opened
                if result_obj.get('opened') and getattr(req,'chat_id',None):
                    try:
                        _chat_state_upsert(req.chat_id, getattr(req,'service',None), None, abs_path)
                    except Exception:
                        pass

                results.append({'type': atype, 'result': result_obj})
            except Exception as _e_vs:
                results.append({'type': atype, 'error': f'VSCode CUA delegation exception: {_e_vs}'})
        elif atype == 'fs.mirror_to_documents':
            # Mirror a file or directory from agent_output into Documents/SarvajnaGPT
            try:
                rel = params.get("relative_path") or ''
                safe_rel = _to_safe_rel_path(rel, default_dir='files', default_filename=None)
                src_abs = os.path.join(AGENT_BASE_DIR, safe_rel.replace('..','')) if not os.path.isabs(safe_rel) else safe_rel
                # If source already inside Documents/SarvajnaGPT, skip mirror (already saved at final location)
                try:
                    docs_base = _get_standard_user_folder('documents')
                    doc_root = os.path.join(str(docs_base), 'SarvajnaGPT')
                    if os.path.abspath(src_abs).lower().startswith(os.path.abspath(doc_root).lower()):
                        results.append({"type": atype, "result": {"skipped": True, "reason": "already_in_documents", "path": src_abs}})
                        continue
                except Exception:
                    pass
                if not os.path.exists(src_abs):
                    results.append({"type": atype, "error": f"Source not found: {src_abs}"})
                    continue
                docs_base = _get_standard_user_folder('documents')
                mirror_root = os.path.join(str(docs_base), 'SarvajnaGPT')
                os.makedirs(mirror_root, exist_ok=True)
                subdir = params.get('target_subdir')
                dest_root = mirror_root if not subdir else os.path.join(mirror_root, subdir)
                os.makedirs(dest_root, exist_ok=True)
                if os.path.isdir(src_abs):
                    # Copy directory tree (shallow copy: create folder, copy files, not recursive subfolders deeper than 10 for safety)
                    import shutil as _sh
                    dest_dir = os.path.join(dest_root, os.path.basename(src_abs))
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir, exist_ok=True)
                    copied = []
                    for root, dirs, files in os.walk(src_abs):
                        depth = root[len(src_abs):].count(os.sep)
                        if depth > 10:
                            continue
                        rel_root = os.path.relpath(root, src_abs)
                        target_dir = os.path.join(dest_dir, rel_root) if rel_root != '.' else dest_dir
                        os.makedirs(target_dir, exist_ok=True)
                        for f in files:
                            sp = os.path.join(root, f)
                            dp = os.path.join(target_dir, f)
                            try:
                                _sh.copy2(sp, dp)
                                copied.append(dp)
                            except Exception:
                                continue
                    results.append({"type": atype, "result": {"mirrored_dir": dest_dir, "files": copied}})
                else:
                    import shutil as _sh
                    dest_path = os.path.join(dest_root, os.path.basename(src_abs))
                    try:
                        _sh.copy2(src_abs, dest_path)
                        results.append({"type": atype, "result": {"mirrored_file": dest_path}})
                    except Exception as _e_m:
                        results.append({"type": atype, "error": f"Mirror failed: {_e_m}"})
            except Exception as _e_m2:
                results.append({"type": atype, "error": f"Mirror exception: {_e_m2}"})
        elif atype == 'word.create_document':
            # Handle target_rel parameter
            if params.get("target_rel"):
                # Use our new path resolution function for more flexible path handling
                resolved_target = _resolve_save_path(params.get("target_rel"), getattr(req, 'chat_id', None))
                # Convert to a path relative to agent_output for word_router
                try:
                    rel_path = os.path.relpath(resolved_target, AGENT_BASE_DIR)
                    safe_target = rel_path
                except ValueError:
                    # If it's on a different drive, use the filename only
                    filename = os.path.basename(resolved_target)
                    safe_target = os.path.join('docs', filename if filename else f"output_{uuid.uuid4().hex[:8]}.docx")
            else:
                # Default to Documents/SarvajnaGPT folder
                docs_folder = _get_standard_user_folder('documents')
                target_folder = docs_folder / 'SarvajnaGPT'
                target_folder.mkdir(parents=True, exist_ok=True)
                chat_id = getattr(req, 'chat_id', None)
                filename = f"{chat_id if chat_id else 'document'}_{uuid.uuid4().hex[:8]}.docx"
                resolved_target = str(target_folder / filename)
                safe_target = os.path.join('docs', filename)
                
            if not safe_target.lower().endswith('.docx'):
                safe_target += '.docx'
                
            prev = word_preview(type("Obj", (), {"target_rel": safe_target, "paragraph": params.get("paragraph", "")}))
            res = word_execute(type("Obj", (), {"target_rel": safe_target, "paragraph": params.get("paragraph", "")}))
            
            # Update chat_state with saved_path if present
            try:
                saved = (res or {}).get('path')
                if saved and getattr(req, 'chat_id', None):
                    _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, saved)
            except Exception:
                pass
                
            # Attempt to copy to Desktop and open the document locally
            desktop_info = {"desktop_copied": False, "desktop_path": None, "opened": False}
            try:
                created_path = (res or {}).get('path')
                if created_path and os.path.isfile(created_path):
                    # Resolve Desktop path (Windows preferred)
                    home = os.path.expanduser('~')
                    desktop_dir = None
                    if os.name == 'nt':
                        userprofile = os.environ.get('USERPROFILE') or home
                        candidate = os.path.join(userprofile, 'Desktop')
                        if os.path.isdir(candidate):
                            desktop_dir = candidate
                    # Fallback for non-Windows or if not found
                    if desktop_dir is None:
                        candidate2 = os.path.join(home, 'Desktop')
                        if os.path.isdir(candidate2):
                            desktop_dir = candidate2
                    if desktop_dir:
                        dest_path = os.path.join(desktop_dir, os.path.basename(created_path))
                        try:
                            shutil.copy2(created_path, dest_path)
                            desktop_info["desktop_copied"] = True
                            desktop_info["desktop_path"] = dest_path
                            # Try to open the file with default app (Word if associated)
                            # But only if this isn't a VS Code focused chat
                            try:
                                # Check if there's a VS Code action or VS Code intent
                                vs_code_focus = False
                                if getattr(req, 'text', None) and _detect_vscode_intent(req.text):
                                    vs_code_focus = True
                                    print("POWER_EXEC_WORD: VS Code intent detected, skipping auto-open of Word document")
                                
                                # Since we don't have direct access to other actions from here,
                                # check if a VS Code file is stored in chat_state
                                if getattr(req, 'chat_id', None):
                                    try:
                                        st = _chat_state_get(req.chat_id, getattr(req, 'service', None))
                                        doc_path = (st or {}).get('doc_path', '')
                                        # If doc_path is an HTML file or has 'vscode' in the path
                                        if doc_path and (doc_path.lower().endswith('.html') or 
                                                        doc_path.lower().endswith('.js') or 
                                                        doc_path.lower().endswith('.css') or
                                                        'vscode' in doc_path.lower()):
                                            vs_code_focus = True
                                            print(f"POWER_EXEC_WORD: VS Code doc_path found: {doc_path}, skipping Word doc open")
                                    except Exception as e:
                                        print(f"POWER_EXEC_CHAT_STATE_ERR: {e}")
                                
                                if not vs_code_focus:
                                    if os.name == 'nt':
                                        os.startfile(dest_path)  # type: ignore[attr-defined]
                                        desktop_info["opened"] = True
                                    else:
                                        # macOS/Linux best effort
                                        import subprocess as _sub
                                        opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                                        _sub.Popen([opener, dest_path])
                                        desktop_info["opened"] = True
                            except Exception as e:
                                print(f"POWER_EXEC_WORD_OPEN_ERROR: {e}")
                        except Exception:
                            pass
            except Exception:
                pass
            results.append({"type": atype, "preview": prev, "result": res, **desktop_info})
        elif atype == 'word.open_and_type':
            # preview and execute via automation router; guard exceptions so this route never 500s
            try:
                # If no save_target provided and we have chat_id, create a stable path per chat
                p2 = dict(params)

                # If this chat already has an associated document, override target to that path
                try:
                    if getattr(req, 'chat_id', None):
                        st = _chat_state_get(req.chat_id, getattr(req, 'service', None))
                        existing = (st or {}).get('doc_path')
                        if existing:
                            p2['save_target'] = existing
                            p2['open_existing'] = True
                            print(f"POWER_EXEC_USE_EXISTING: save_target set to existing doc: {existing}")
                except Exception as _e_exist:
                    try:
                        print(f"POWER_EXEC_EXISTING_LOOKUP_ERR: {_e_exist}")
                    except Exception:
                        pass

                # Process save_target path based on user input
                if p2.get('save_target'):
                    # Check if we have a specific filename from savetarget parsing
                    if p2.get('filename'):
                        # We've parsed "desktop/filename.docx" format
                        location = p2['save_target']  # This will be 'desktop', 'documents', etc.
                        filename = p2['filename']

                        # Handle different locations
                        if location == 'desktop':
                            desktop_dir = _get_standard_user_folder('desktop')
                            p2['save_target'] = str(desktop_dir / filename)
                        elif location == 'documents':
                            docs_dir = _get_standard_user_folder('documents')
                            p2['save_target'] = str(docs_dir / filename)
                        elif location == 'downloads':
                            downloads_dir = _get_standard_user_folder('downloads')
                            p2['save_target'] = str(downloads_dir / filename)
                    else:
                        # Standard path handling
                        p2['save_target'] = _resolve_save_path(p2['save_target'], getattr(req, 'chat_id', None))
                elif getattr(req, 'chat_id', None):
                    # Default to Documents/SarvajnaGPT folder with a chat-specific filename
                    docs_folder = _get_standard_user_folder('documents')
                    target_folder = docs_folder / 'SarvajnaGPT'
                    target_folder.mkdir(exist_ok=True)
                    filename = f"{req.chat_id}_{uuid.uuid4().hex[:8]}.docx"
                    p2['save_target'] = str(target_folder / filename)

                # Set standard parameters
                p2['split_screen'] = p2.get('split_screen', True)
                p2['use_os_snap_keys'] = p2.get('use_os_snap_keys', True)
                p2['use_cua_for_selection'] = p2.get('use_cua_for_selection', True)
                p2['arrangement_delay_ms'] = p2.get('arrangement_delay_ms', 800)
                p2['word_side'] = p2.get('word_side', 'right')

                # Ensure the text content is properly passed
                if 'text' not in p2:
                    p2['text'] = params.get('text', '')

                # Do not expand placeholders here; expansion is handled earlier in power_chat to avoid preview failures

                # Build a safe, local preview without strict path checks
                prev = {
                    "summary": f"Open Word and type {len(p2.get('text',''))} chars" + (" and save" if p2.get('save_target') else ""),
                    "save_target": p2.get('save_target'),
                    "show_window": p2.get('show_window', True),
                    "split_screen": p2.get('split_screen', True),
                }
            except Exception as e:
                try:
                    print(f"POWER_EXEC_PREVIEW_ERR: {e}")
                except Exception:
                    pass
                results.append({"type": atype, "error": f"preview failed: {e}"})
                continue
            try:
                # Create a proper object with all required attributes
                # We need to ensure 'text' is explicitly set and not just accessed via getattr
                word_params = {
                    'text': p2.get('text', ''),
                    'save_target': p2.get('save_target', None),
                    'show_window': p2.get('show_window', True),
                    'split_screen': p2.get('split_screen', True),
                    'use_os_snap_keys': p2.get('use_os_snap_keys', True),
                    'use_cua_for_selection': p2.get('use_cua_for_selection', True),
                    'arrangement_delay_ms': p2.get('arrangement_delay_ms', 800),
                    'word_side': p2.get('word_side', 'right'),
                    'append': bool(p2.get('append', False)),
                }
                
                # Use a proper class instance rather than a dynamic object
                class WordParams:
                    def __init__(self, **kwargs):
                        for key, value in kwargs.items():
                            setattr(self, key, value)
                
                param_obj = WordParams(**word_params)

                # Optional HTTP mode for users who want to see the API endpoint being hit
                res = None
                # Allow per-action override via params.transport='http' or force_http=true
                transport_val = str(p2.get('transport', '')).strip().lower()
                # Default to HTTP unless explicitly forced inproc or env disables
                env_http = str(os.environ.get('POWER_AUTOMATION_HTTP', '')).strip().lower()
                env_disables_http = env_http in ('0', 'false', 'no')
                force_http = bool(p2.get('force_http'))
                force_inproc = bool(p2.get('force_inproc')) or transport_val == 'inproc'
                http_mode = (not env_disables_http) and (force_http or (transport_val == 'http') or (not force_inproc))
                try:
                    print(f"WORD_HTTP_PREF: http_mode={http_mode} transport={transport_val} env={env_http} force_http={force_http} force_inproc={force_inproc}")
                except Exception:
                    pass
                if http_mode:
                    try:
                        import requests  # type: ignore
                        # Derive endpoint dynamically: prefer explicit env, else request host, else localhost
                        base_env = os.environ.get('API_BASE_URL') or ''
                        dynamic_host = None
                        try:
                            # If running inside a FastAPI request context with headers
                            hdr_host = getattr(req, 'headers', {}).get('host') if hasattr(req, 'headers') else None
                            if hdr_host:
                                scheme = 'http'
                                # naive HTTPS detection if forwarded proto set
                                fproto = getattr(req, 'headers', {}).get('x-forwarded-proto') if hasattr(req, 'headers') else None
                                if fproto in ('https', 'http'): scheme = fproto
                                dynamic_host = f"{scheme}://{hdr_host}"
                        except Exception:
                            dynamic_host = None
                        base_url = base_env or dynamic_host or 'http://localhost:8000'
                        endpoint = base_url.rstrip('/') + '/api/automation/word/execute'
                        try:
                            print(f"WORD_HTTP_POST: endpoint={endpoint} text_len={len(word_params.get('text','') or '')} save_target={word_params.get('save_target')}")
                        except Exception:
                            pass
                        payload = {
                            'text': word_params.get('text', ''),
                            'show_window': bool(word_params.get('show_window', True)),
                            'save_target': word_params.get('save_target'),
                            'split_screen': bool(word_params.get('split_screen', True)),
                            'word_side': word_params.get('word_side', 'right'),
                            'arrangement_delay_ms': int(word_params.get('arrangement_delay_ms', 800)),
                            'use_os_snap_keys': bool(word_params.get('use_os_snap_keys', True)),
                            'use_cua_for_selection': bool(word_params.get('use_cua_for_selection', True)),
                            'append': bool(word_params.get('append', False)),
                        }
                        try:
                            resp = requests.post(endpoint, json=payload, timeout=30)
                            if resp.ok:
                                res = resp.json()
                                res['transport'] = 'http'
                            else:
                                res = {'error': f'HTTP {resp.status_code}: {resp.text}', 'transport': 'http'}
                        except Exception as _e:
                            try:
                                print(f"WORD_HTTP_ERR: {_e}")
                            except Exception:
                                pass
                            res = {'error': f'HTTP request failed: {_e}', 'transport': 'http'}
                    except Exception:
                        # Fallback to in-process if requests not available
                        res = auto_word_execute(param_obj)
                        if isinstance(res, dict):
                            res['transport'] = 'inproc'
                else:
                    # Default: in-process fast path
                    try:
                        print("WORD_INPROC_CALL")
                    except Exception:
                        pass
                    res = auto_word_execute(param_obj)
                    if isinstance(res, dict):
                        res['transport'] = 'inproc'
                try:
                    print(f"WORD_EXEC_TRANSPORT: {'http' if http_mode else 'inproc'}")
                except Exception:
                    pass
                # Update chat_state with saved_path if present
                try:
                    saved = (res or {}).get('saved_path')
                    if saved and getattr(req, 'chat_id', None):
                        _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, saved)
                except Exception:
                    pass
                
                # Add debugging information to the result
                if isinstance(res, dict):
                    res['debug_info'] = {
                        'text_length': len(word_params.get('text', '')),
                        'save_path': word_params.get('save_target'),
                        'params_keys': list(word_params.keys())
                    }
                    
                # Update chat_state with saved_path if present
                try:
                    saved = (res or {}).get('saved_path')
                    print(f"Word automation saved_path: {saved}")
                    if saved and getattr(req, 'chat_id', None):
                        _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, saved)
                except Exception as e:
                    print(f"Error updating chat state: {e}")
                    
                results.append({"type": atype, "preview": prev, "result": res})
            except Exception as e:
                # Fallback: create a .docx via python-docx and open it, so user still sees Word
                try:
                    text = p2.get('text') or ''
                    
                    # Handle fallback save path with the new path resolver
                    if p2.get('save_target'):
                        raw_target = p2.get('save_target')
                    else:
                        # Use Documents folder with SarvajnaGPT subfolder by default
                        docs_folder = _get_standard_user_folder('documents')
                        target_folder = docs_folder / 'SarvajnaGPT'
                        target_folder.mkdir(exist_ok=True)
                        chat_id = getattr(req, 'chat_id', None)
                        filename = f"{chat_id if chat_id else 'document'}_{uuid.uuid4().hex[:8]}.docx"
                        raw_target = str(target_folder / filename)
                    
                    # Convert to a relative path for word_router
                    # First try to make it relative to agent_output
                    try:
                        rel_path = os.path.relpath(raw_target, AGENT_BASE_DIR)
                        safe_target = rel_path
                    except ValueError:
                        # If it's on a different drive, use the filename only
                        filename = os.path.basename(raw_target)
                        safe_target = os.path.join('docs', filename if filename else f"output_{uuid.uuid4().hex[:8]}.docx")
                    
                    if not safe_target.lower().endswith('.docx'):
                        safe_target += '.docx'
                    f_prev = auto_word_preview(type("Obj", (), {"target_rel": safe_target, "paragraph": text}))
                    f_res = auto_word_execute(type("Obj", (), {"target_rel": safe_target, "paragraph": text}))
                    try:
                        if getattr(req, 'chat_id', None):
                            # Construct absolute path like word_execute returns
                            created_path = (f_res or {}).get('path')
                            if created_path:
                                _chat_state_upsert(req.chat_id, getattr(req, 'service', None), None, created_path)
                    except Exception:
                        pass
                    # Try to copy to Desktop and open default app
                    desktop_info = {"desktop_copied": False, "desktop_path": None, "opened": False}
                    try:
                        created_path = (f_res or {}).get('path')
                        if created_path and os.path.isfile(created_path):
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
                                dest_path = os.path.join(desktop_dir, os.path.basename(created_path))
                                try:
                                    shutil.copy2(created_path, dest_path)
                                    desktop_info["desktop_copied"] = True
                                    desktop_info["desktop_path"] = dest_path
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
                    results.append({"type": atype, "preview": prev, "error": str(e), "fallback": {"preview": f_prev, "result": f_res, **desktop_info}})
                except Exception as e2:
                    results.append({"type": atype, "preview": prev, "error": f"automation failed: {e}; fallback failed: {e2}"})
        else:
            try:
                print(f"POWER_EXEC_UNKNOWN_ACTION: {atype}")
            except Exception:
                pass
            # Support automation.open_vscode here (added after initial else ladder)
            results.append({"type": atype, "error": "Unknown action"})
    try:
        # Summarize results quickly for debugging
        summary = []
        for r in results:
            t = r.get('type')
            err = r.get('error')
            transport = None
            try:
                transport = (r.get('result') or {}).get('transport')
            except Exception:
                transport = None
            summary.append({"type": t, "error": bool(err), "transport": transport})
        print(f"POWER_EXEC_END: results={summary}")
    except Exception:
        pass
    return {"results": results}


@router.get('/power_version')
def power_version() -> dict:
    """Diagnostic endpoint to verify the running version of power router."""
    return {
        "version": POWER_ROUTER_VERSION,
        "http_default": True,
        "auto_execute_in_power_chat": True
    }


# ---------------------- Developer Diagnostic Endpoints ----------------------
@router.get('/dev/check_path')
def dev_check_path(rel: str) -> dict:
    """Return existence, absolute path, and size for a path under agent_output (or absolute if inside)."""
    try:
        abs_path = _resolve_under_base(rel)
    except Exception as e:
        return {"ok": False, "error": str(e), "rel": rel}
    exists = os.path.exists(abs_path)
    size = None
    if exists and os.path.isfile(abs_path):
        try:
            size = os.path.getsize(abs_path)
        except Exception:
            size = None
    return {"ok": True, "exists": exists, "abs_path": abs_path, "size": size}


@router.get('/dev/list_agent')
def dev_list_agent(sub: str = '.') -> dict:
    """List files/folders recursively (depth 3) under agent_output/sub."""
    try:
        base = _resolve_under_base(sub)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    out = []
    for root, dirs, files in os.walk(base):
        depth = os.path.relpath(root, base).count(os.sep)
        if depth > 3:
            continue
        out.append({
            "dir": os.path.relpath(root, base),
            "files": files,
            "subdirs": dirs
        })
    return {"ok": True, "base": base, "entries": out}


@router.get('/dev/documents_mirror')
def dev_documents_mirror() -> dict:
    """Inspect Documents/SarvajnaGPT mirror root."""
    docs = _get_standard_user_folder('documents')
    mirror = os.path.join(str(docs), 'SarvajnaGPT')
    exists = os.path.isdir(mirror)
    listing = []
    if exists:
        for root, dirs, files in os.walk(mirror):
            depth = os.path.relpath(root, mirror).count(os.sep)
            if depth > 2:
                continue
            listing.append({
                "dir": os.path.relpath(root, mirror),
                "files": files,
                "subdirs": dirs
            })
    return {"ok": True, "mirror_root": mirror, "exists": exists, "entries": listing}

@router.get('/dev/vscode_status')
def dev_vscode_status() -> dict:
    """Report current VS Code detection result and candidates tried."""
    resolved, _ = _resolve_vscode_executable()
    # Expose cache and environment hints
    return {
        "resolved": resolved,
        "env_POWER_VSCODE_BIN": os.environ.get('POWER_VSCODE_BIN'),
        "cache_keys": list(_VSCODE_DETECTION_CACHE.keys()),
        "version": POWER_ROUTER_VERSION,
        "note": "Set POWER_VSCODE_BIN to explicit Code.exe path if resolved is null.",
    }


def _persist_power_chat_row(req: PowerChatRequest, assistant_text: str):
    """Insert a row into chat table for Power Mode, so chats appear in lists/history.
    Stores user text, assistant_text, tags, doc_info, service, and a friendly chat_name.
    """
    service = (req.service or 'power_mode')
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        # Determine chat_name for this chat_id: reuse existing or create 'New Chat N'
        c.execute('SELECT DISTINCT chat_name FROM chat WHERE chat_id=? AND chat_name IS NOT NULL', (req.chat_id,))
        row = c.fetchone()
        if row and row[0]:
            chat_name_to_use = row[0]
        else:
            c.execute("SELECT DISTINCT chat_name FROM chat WHERE chat_name LIKE 'New Chat %'")
            existing = [r[0] for r in c.fetchall() if r and r[0]]
            max_n = 0
            for en in existing:
                try:
                    n = int(str(en).replace('New Chat ', '').strip())
                    if n > max_n:
                        max_n = n
                except Exception:
                    continue
            chat_name_to_use = f'New Chat {max_n + 1}'
        # Normalize tags
        tags = req.mem_tags or req.selected_tags or []
        tags_str = ','.join([str(t).strip() for t in tags if t and str(t).strip()]) if tags else None
        # Insert one combined row (user + ai)
        c.execute('INSERT INTO chat (chat_id, user, llm, embedding, timestamp, tags, doc_info, service, chat_name) VALUES (?, ?, ?, ?, strftime("%s","now"), ?, ?, ?, ?)',
                  (req.chat_id, req.text, assistant_text, None, tags_str, req.doc_info, service, chat_name_to_use))
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass
            
class OpenDocIntelligentlyRequest(BaseModel):
    abs_path: str
    split_screen: bool = True
    preferred_side: str = "right"  # 'left' or 'right'
    chat_context: Optional[str] = None  # Optional chat context to help determine if code-related
    request_id: Optional[str] = None  # Optional idempotency key

def compute_open_doc_signature(req: "OpenDocIntelligentlyRequest") -> str:
    """Deterministic signature for idempotency when client does not supply request_id.
    Includes normalized absolute path + preferred side + split flag.
    Keep concise: hash content to avoid leaking full path length in key map.
    """
    import hashlib, os as _os
    try:
        norm_path = _os.path.abspath(req.abs_path) if req.abs_path else ""  # normalize
    except Exception:
        norm_path = req.abs_path or ""
    base = f"{norm_path}|{req.preferred_side}|{req.split_screen}"
    h = hashlib.sha1(base.encode('utf-8', errors='ignore')).hexdigest()[:16]
    return f"auto:{h}"
    
@router.post('/open_doc_intelligently')
def open_doc_intelligently(req: OpenDocIntelligentlyRequest) -> dict:
    """Intelligently open a document with either Word or VS Code based on file extension and content."""
    print(f"[DEBUG] Received open_doc_intelligently request: {req.abs_path}")
    # Idempotency: compute effective key (explicit request_id or auto signature)
    effective_request_id = req.request_id or compute_open_doc_signature(req)
    auto_generated = req.request_id is None
    # Fast-return if recently processed
    try:
        from main import _RECENT_REQUESTS, _RECENT_REQUESTS_LOCK, _RECENT_REQUESTS_TTL
        import time as _t_idem
        now = _t_idem.time()
        with _RECENT_REQUESTS_LOCK:
            rec = _RECENT_REQUESTS.get(effective_request_id)
            if rec and (now - rec[0] <= _RECENT_REQUESTS_TTL):
                cached = rec[1]
                cached_copy = dict(cached)
                cached_copy['idempotent'] = True
                cached_copy['idempotent_key'] = effective_request_id
                if auto_generated:
                    cached_copy['idempotent_auto'] = True
                return cached_copy
    except Exception:
        pass
    if not req.abs_path or not os.path.isfile(req.abs_path):
        return {"error": f"File not found: {req.abs_path}", "opened": False}
        
    # Determine if this is a code file based on extension
    code_extensions = ['.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', 
                      '.py', '.java', '.c', '.cpp', '.cs', '.php', '.go', 
                      '.rb', '.rs', '.swift', '.json', '.xml', '.yaml', '.yml', '.md',
                      '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.vue', '.jsx', '.tsx',
                      '.config', '.gitignore', '.env']
    
    is_code_file = any(req.abs_path.lower().endswith(ext) for ext in code_extensions)
    
    # Check chat context for code-related keywords if available
    if not is_code_file and req.chat_context:
        code_keywords = ['code', 'programming', 'developer', 'function', 'class', 'html', 
                         'javascript', 'python', 'java', 'c++', 'typescript', 'algorithm', 
                         'syntax', 'compiler', 'debugging', 'github', 'git']
        lower_context = req.chat_context.lower()
        context_suggests_code = any(keyword in lower_context for keyword in code_keywords)
        
        # For text files, which could be either code or text documents, use context as a tiebreaker
        if req.abs_path.lower().endswith(('.txt', '.csv', '.log')) and context_suggests_code:
            is_code_file = True
    
    if is_code_file:
        # Open with VS Code using the robust implementation from automation_router
        print(f"Opening {req.abs_path} with VS Code (using automation_router)")
        try:
            from automation_router import VSCodeOpenRequest, vscode_open_existing
            vscode_req = VSCodeOpenRequest(
                abs_path=req.abs_path,
                split_screen=req.split_screen,
                code_side=req.preferred_side,
                fallback_snap=True,
                arrangement_delay_ms=600,
                use_os_snap_keys=True,
                use_cua_for_selection=True
            )
            result = vscode_open_existing(vscode_req)
            # Cache idempotent result if request_id provided
            try:
                import time as _t_store
                from main import _RECENT_REQUESTS, _RECENT_REQUESTS_LOCK
                with _RECENT_REQUESTS_LOCK:
                    _RECENT_REQUESTS[effective_request_id] = (_t_store.time(), result)
                result['idempotent_key'] = effective_request_id
                if auto_generated:
                    result['idempotent_auto'] = True
            except Exception:
                pass
            return result
        except Exception as e:
            print(f"Error with automation_router.vscode_open_existing: {e}")
            # Fall back to our basic implementation
            result = _open_vscode_path(
                abs_path=req.abs_path,
                side=req.preferred_side,
                split=req.split_screen
            )
            try:
                import time as _t_store2
                from main import _RECENT_REQUESTS, _RECENT_REQUESTS_LOCK
                with _RECENT_REQUESTS_LOCK:
                    _RECENT_REQUESTS[effective_request_id] = (_t_store2.time(), result)
                result['idempotent_key'] = effective_request_id
                if auto_generated:
                    result['idempotent_auto'] = True
            except Exception:
                pass
            return result
    else:
        # Open with Word
        try:
            from automation_router import WordOpenExistingRequest, word_open_existing
            word_req = WordOpenExistingRequest(
                abs_path=req.abs_path,
                split_screen=req.split_screen,
                word_side=req.preferred_side,
                fallback_snap=True,
                arrangement_delay_ms=600
            )
            result = word_open_existing(word_req)
            try:
                import time as _t_store3
                from main import _RECENT_REQUESTS, _RECENT_REQUESTS_LOCK
                with _RECENT_REQUESTS_LOCK:
                    _RECENT_REQUESTS[effective_request_id] = (_t_store3.time(), result)
                result['idempotent_key'] = effective_request_id
                if auto_generated:
                    result['idempotent_auto'] = True
            except Exception:
                pass
            return result
        except Exception as e:
            print(f"Error opening Word: {e}")
            # If Word fails, try VS Code as fallback
            result = _open_vscode_path(
                abs_path=req.abs_path,
                side=req.preferred_side,
                split=req.split_screen
            )
            try:
                import time as _t_store4
                from main import _RECENT_REQUESTS, _RECENT_REQUESTS_LOCK
                with _RECENT_REQUESTS_LOCK:
                    _RECENT_REQUESTS[effective_request_id] = (_t_store4.time(), result)
                result['idempotent_key'] = effective_request_id
                if auto_generated:
                    result['idempotent_auto'] = True
            except Exception:
                pass
            return result
