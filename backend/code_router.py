from __future__ import annotations

"""Generic code/text file editing router.
Provides preview, execute (write/overwrite), append, read, and list directory capabilities
under the controlled agent_output base directory OR selected standard user folders
(Desktop, Documents, Downloads) similar to word_router path handling.

Endpoints (prefix /api/code):
  POST /preview  -> summarize intended change, provide diff snippet (first/last lines) if file exists
  POST /execute  -> perform write/overwrite or append
  POST /read     -> return file content (bounded size)
  POST /list     -> list directory entries (relative to agent_output or standard folder)

This keeps functionality intentionally simple; richer refactor/diff application can build on top later.
"""

import os, uuid, re, time, subprocess, shlex
from pathlib import Path
from typing import Optional, Literal, List
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/code", tags=["code"])

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
AGENT_BASE_DIR = os.path.join(REPO_ROOT, "agent_output")
os.makedirs(AGENT_BASE_DIR, exist_ok=True)

# ---------------- Path Resolution (mirrors logic concept from power_router / word_router) ---------

STANDARD_FOLDERS = ["desktop", "documents", "downloads", "document", "docs", "doc", "down", "desk"]


def _get_standard_user_folder(folder_name: str) -> Path:
    name = folder_name.lower().strip()
    home = Path.home()
    if os.name == 'nt':
        userprofile = Path(os.environ.get('USERPROFILE') or str(home))
        onedrive = Path(os.environ.get('OneDrive') or (userprofile / 'OneDrive'))
        mapping = {
            'documents': [userprofile / 'Documents', onedrive / 'Documents'],
            'document': [userprofile / 'Documents', onedrive / 'Documents'],
            'docs': [userprofile / 'Documents', onedrive / 'Documents'],
            'doc': [userprofile / 'Documents', onedrive / 'Documents'],
            'desktop': [userprofile / 'Desktop', onedrive / 'Desktop'],
            'desk': [userprofile / 'Desktop', onedrive / 'Desktop'],
            'downloads': [userprofile / 'Downloads', onedrive / 'Downloads'],
            'download': [userprofile / 'Downloads', onedrive / 'Downloads'],
            'down': [userprofile / 'Downloads', onedrive / 'Downloads'],
        }
        candidates = mapping.get(name, [userprofile / 'Documents'])
    else:
        mapping = {
            'documents': [home / 'Documents'],
            'document': [home / 'Documents'],
            'docs': [home / 'Documents'],
            'doc': [home / 'Documents'],
            'desktop': [home / 'Desktop'],
            'desk': [home / 'Desktop'],
            'downloads': [home / 'Downloads'],
            'download': [home / 'Downloads'],
            'down': [home / 'Downloads'],
        }
        candidates = mapping.get(name, [home / 'Documents'])
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return candidates[0]


def _resolve_under_base(path_like: str) -> str:
    p = path_like
    if not os.path.isabs(p):
        p = os.path.join(AGENT_BASE_DIR, p)
    p = os.path.abspath(p)
    base = os.path.abspath(AGENT_BASE_DIR)
    if os.path.commonpath([p, base]) != base:
        raise ValueError("Target path outside agent base directory")
    return p


def _resolve_save_path(save_target: str, ensure_extension: Optional[str] = None) -> str:
    # Absolute path -> use as-is
    if os.path.isabs(save_target):
        return save_target

    # Standard folder prefix e.g. documents/myfile.py
    folder_match = re.match(r'^(desktop|documents?|downloads?|docs|doc|down|desk)[/\\](.+)$', save_target, re.IGNORECASE)
    if folder_match:
        folder_name, rest = folder_match.group(1), folder_match.group(2)
        base_folder = _get_standard_user_folder(folder_name)
        base_folder.mkdir(parents=True, exist_ok=True)
        if ensure_extension and '.' not in rest:
            rest = rest + ensure_extension
        path = base_folder / rest
        # Avoid overwriting silently
        if path.exists():
            stem, suffix = path.stem, path.suffix
            path = base_folder / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
        return str(path)

    # If it's just a standard folder name
    if save_target.lower() in STANDARD_FOLDERS:
        base_folder = _get_standard_user_folder(save_target)
        base_folder.mkdir(parents=True, exist_ok=True)
        filename = f"file_{uuid.uuid4().hex[:8]}{ensure_extension or ''}"
        return str(base_folder / filename)

    # Relative -> agent_output
    try:
        resolved = _resolve_under_base(save_target)
    except ValueError:
        # fallback to Documents/SarvajnaGPT
        docs = _get_standard_user_folder('documents') / 'SarvajnaGPT'
        docs.mkdir(parents=True, exist_ok=True)
        name = os.path.basename(save_target)
        if not name:
            name = f"file_{uuid.uuid4().hex[:8]}{ensure_extension or ''}"
        resolved = docs / name
    if ensure_extension and '.' not in str(resolved).split(os.sep)[-1]:
        resolved = Path(str(resolved) + ensure_extension)
    return str(resolved)

# ---------------- Models -----------------

class CodePreviewRequest(BaseModel):
    target_rel: str = Field(..., description="Target path (relative, standard folder alias, or absolute)")
    content: str = Field("", description="Full replacement content (UTF-8)")
    mode: Literal['write', 'append'] = Field('write')
    ensure_ext: Optional[str] = Field(None, description="If provided and target has no extension, append this (e.g. .py)")

class CodeExecuteRequest(CodePreviewRequest):
    pass

class CodeReadRequest(BaseModel):
    target_rel: str
    max_bytes: int = 100_000

class CodeListRequest(BaseModel):
    path: str = Field(".", description="Directory path relative/standard/absolute")
    depth: int = Field(1, ge=0, le=5)

class DirOpRequest(BaseModel):
    op: Literal['create_dir','create_file','delete','rename','move']
    target: str
    new_name: Optional[str] = None  # for rename
    dest: Optional[str] = None      # for move
    content: Optional[str] = None   # for create_file

class TerminalRequest(BaseModel):
    cmd: str = Field(..., description="Command to run (restricted allowlist)")
    cwd: Optional[str] = Field(None, description="Working directory")

class AIEditRequest(BaseModel):
    target_rel: str
    instruction: str
    selection: Optional[str] = None
    apply: bool = False

class LastModifiedRequest(BaseModel):
    target_rel: str

# ---------------- Helpers -----------------

def _short_diff(old: str, new: str, limit: int = 12) -> List[str]:
    import difflib
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm=""))
    if len(diff) > limit:
        return diff[:limit] + ["... (truncated)"]
    return diff

def _read_file_text(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''

# ---------------- AI Assisted Edit ----------------
try:
    from .llm_inference import generate_response
except Exception:
    def generate_response(prompt: str) -> str:  # fallback dummy
        return "[AI unavailable]" + prompt[:200]

AI_EDIT_SYSTEM_PROMPT = (
    "You are a precise code editing assistant. Given an instruction and the ORIGINAL file content, "
    "produce ONLY the full UPDATED file content between the markers <<<BEGIN_FILE>>> and <<<END_FILE>>>. "
    "Do NOT add explanations outside markers. Maintain original formatting unless changes are required."
)

def _apply_ai_instruction(original: str, instruction: str, selection: Optional[str]) -> str:
    selection_block = f"\nUser selected region:\n<<<SELECTION>>>\n{selection}\n<<<END_SELECTION>>>\n" if selection else ""
    prompt = (
        f"{AI_EDIT_SYSTEM_PROMPT}\n\nInstruction:\n{instruction}\n{selection_block}\n"
        f"Original file content below between markers:\n<<<BEGIN_ORIGINAL>>>\n{original}\n<<<END_ORIGINAL>>>\n"
        "Return updated full file between <<<BEGIN_FILE>>> and <<<END_FILE>>> markers."
    )
    raw = generate_response(prompt)
    # Extract between markers
    m = re.search(r"<<<BEGIN_FILE>>>(.*)<<<END_FILE>>>", raw, re.DOTALL)
    if m:
        return m.group(1).strip('\n')
    # Fallback: if model returned plain content
    return raw.strip('\n')

# ---------------- Endpoints ----------------

@router.post('/preview')
def preview(req: CodePreviewRequest) -> dict:
    target_abs = _resolve_save_path(req.target_rel, req.ensure_ext)
    exists = os.path.isfile(target_abs)
    old_content = ''
    if exists:
        try:
            with open(target_abs, 'r', encoding='utf-8', errors='replace') as f:
                old_content = f.read()
        except Exception:
            old_content = ''
    new_effective = old_content + req.content if (exists and req.mode == 'append') else req.content
    diff_snippet = _short_diff(old_content, new_effective)
    return {
        'summary': f"{'Append to' if req.mode=='append' and exists else 'Write'} file {target_abs} ({len(new_effective)} chars)",
        'target_abs': target_abs,
        'exists': exists,
        'mode': req.mode,
        'lines_new': new_effective.count('\n') + 1 if new_effective else 0,
        'diff_preview': diff_snippet,
    }

@router.post('/execute')
def execute(req: CodeExecuteRequest) -> dict:
    prev = preview(req)
    target_abs = prev['target_abs']
    os.makedirs(os.path.dirname(target_abs), exist_ok=True)
    try:
        if prev['exists'] and req.mode == 'append':
            with open(target_abs, 'a', encoding='utf-8') as f:
                f.write(req.content)
        else:
            with open(target_abs, 'w', encoding='utf-8') as f:
                f.write(req.content)
        return {'written': True, 'path': target_abs, 'mode': req.mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/read')
def read(req: CodeReadRequest) -> dict:
    target_abs = _resolve_save_path(req.target_rel)
    if not os.path.isfile(target_abs):
        raise HTTPException(status_code=404, detail='File not found')
    try:
        with open(target_abs, 'rb') as f:
            data = f.read(req.max_bytes + 1)
        truncated = len(data) > req.max_bytes
        if truncated:
            data = data[:req.max_bytes]
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = data.decode('latin-1', errors='replace')
        return {'path': target_abs, 'truncated': truncated, 'content': text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/list')
def list_dir(req: CodeListRequest) -> dict:
    base = _resolve_save_path(req.path)
    if os.path.isfile(base):
        return {'path': base, 'type': 'file'}
    out = []
    try:
        for root, dirs, files in os.walk(base):
            depth = Path(root).relative_to(Path(base)).parts
            if len(depth) > req.depth and req.depth >= 0:
                continue
            rel_root = os.path.relpath(root, base)
            out.append({'dir': rel_root, 'files': files, 'subdirs': dirs})
        return {'path': base, 'entries': out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/dir_op')
def dir_op(req: DirOpRequest) -> dict:
    target_abs = _resolve_save_path(req.target)
    try:
        if req.op == 'create_dir':
            os.makedirs(target_abs, exist_ok=True)
            return {'ok': True, 'path': target_abs}
        elif req.op == 'create_file':
            os.makedirs(os.path.dirname(target_abs), exist_ok=True)
            with open(target_abs, 'w', encoding='utf-8') as f:
                f.write(req.content or '')
            return {'ok': True, 'path': target_abs}
        elif req.op == 'delete':
            if os.path.isdir(target_abs):
                # shallow safety: only delete empty dir
                if os.listdir(target_abs):
                    raise HTTPException(status_code=400, detail='Directory not empty')
                os.rmdir(target_abs)
            else:
                os.remove(target_abs)
            return {'ok': True}
        elif req.op == 'rename':
            if not req.new_name:
                raise HTTPException(status_code=400, detail='new_name required')
            new_abs = os.path.join(os.path.dirname(target_abs), req.new_name)
            os.rename(target_abs, new_abs)
            return {'ok': True, 'path': new_abs}
        elif req.op == 'move':
            if not req.dest:
                raise HTTPException(status_code=400, detail='dest required')
            dest_abs = _resolve_save_path(req.dest)
            if os.path.isdir(dest_abs):
                dest_final = os.path.join(dest_abs, os.path.basename(target_abs))
            else:
                dest_final = dest_abs
            os.makedirs(os.path.dirname(dest_final), exist_ok=True)
            os.rename(target_abs, dest_final)
            return {'ok': True, 'path': dest_final}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=400, detail='Unsupported op')

ALLOWED_CMDS = {'dir','echo','type','pip','python','node','npm','ls','cat'}

@router.post('/terminal')
def run_terminal(req: TerminalRequest) -> dict:
    # Basic allowlist: first token must be allowed
    parts = shlex.split(req.cmd, posix=False)
    if not parts:
        raise HTTPException(status_code=400, detail='Empty command')
    first = parts[0].lower()
    if first not in ALLOWED_CMDS:
        raise HTTPException(status_code=403, detail='Command not allowed')
    cwd = _resolve_save_path(req.cwd or '.')
    if not os.path.isdir(cwd):
        raise HTTPException(status_code=400, detail='cwd not found')
    try:
        proc = subprocess.run(parts, cwd=cwd, capture_output=True, text=True, timeout=20)
        return {
            'returncode': proc.returncode,
            'stdout': proc.stdout[-10000:],
            'stderr': proc.stderr[-10000:]
        }
    except subprocess.TimeoutExpired:
        return {'returncode': -1, 'stdout': '', 'stderr': 'Timeout'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/ai_edit')
def ai_edit(req: AIEditRequest) -> dict:
    path_abs = _resolve_save_path(req.target_rel)
    if not os.path.isfile(path_abs):
        raise HTTPException(status_code=404, detail='File not found')
    original = _read_file_text(path_abs)
    updated = _apply_ai_instruction(original, req.instruction, req.selection)
    diff_snippet = _short_diff(original, updated, limit=100)
    applied = False
    if req.apply:
        try:
            with open(path_abs, 'w', encoding='utf-8') as f:
                f.write(updated)
            applied = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Write failed: {e}')
    return {
        'path': path_abs,
        'applied': applied,
        'diff': diff_snippet,
        'preview_len': len(updated),
        'updated_content': None if req.apply else updated
    }

@router.post('/last_modified')
def last_modified(req: LastModifiedRequest) -> dict:
    path_abs = _resolve_save_path(req.target_rel)
    if not os.path.isfile(path_abs):
        raise HTTPException(status_code=404, detail='File not found')
    try:
        stat = os.stat(path_abs)
        return {'path': path_abs, 'mtime': stat.st_mtime}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/raw')
def raw_file(path: str):  # query param
    # Serve raw file content (used for HTML live preview). Limited to text & html.
    path_abs = _resolve_save_path(path)
    if not os.path.isfile(path_abs):
        raise HTTPException(status_code=404, detail='File not found')
    try:
        with open(path_abs, 'rb') as f:
            data = f.read()
        # naive content-type selection
        ext = os.path.splitext(path_abs)[1].lower()
        ctype = 'text/plain; charset=utf-8'
        if ext in {'.html','.htm'}:
            ctype = 'text/html; charset=utf-8'
        elif ext in {'.js'}:
            ctype = 'application/javascript; charset=utf-8'
        elif ext in {'.css'}:
            ctype = 'text/css; charset=utf-8'
        return Response(content=data, media_type=ctype)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
