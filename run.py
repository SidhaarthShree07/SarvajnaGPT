import os
import sys
import subprocess
import shutil
import socket
from pathlib import Path

"""Dev/Prod bootstrap utility.

Default (no args):
    - Creates virtual env (backend/.venv)
    - Installs backend requirements
    - Clones CUA repo if missing
    - Launches two terminals (backend + frontend dev server)

Flags / Env:
    --prod              Serve built frontend from backend only (single process)
    APP_HOST            Override host (default 0.0.0.0)
    APP_PORT            Override port (default 8000)
    SKIP_CUA=1          Skip cloning CUA
    NO_FRONTEND=1       Skip spawning frontend dev terminal in default mode
"""
# Requirements:
# - Windows PowerShell (default on this repo)
# - Python 3.11+ installed (or path provided via PYTHON env)
# - Node.js + npm installed (for frontend)

REPO_ROOT = Path(__file__).parent
BACKEND = REPO_ROOT / 'backend'
FRONTEND = REPO_ROOT / 'frontend'
VENV_DIR = BACKEND / '.venv'
PY_REQ = BACKEND / 'requirements.txt'

REQUIRED_PYTHON = (3, 11)


def find_python() -> str:
    # Respect explicit override
    env_py = os.environ.get('PYTHON')
    if env_py:
        return env_py
    # Try py launcher then python3 then python
    candidates = ['py', 'python3', 'python']
    for c in candidates:
        try:
            r = subprocess.run([c, '-c', 'import sys;print(sys.executable)'], capture_output=True, text=True, check=True)
            exe = r.stdout.strip()
            if exe:
                return c
        except Exception:
            continue
    return 'python'


def check_python_version(pyc: str) -> None:
    try:
        code = 'import sys; print("%d.%d"%sys.version_info[:2])'
        r = subprocess.run([pyc, '-c', code], capture_output=True, text=True, check=True)
        ver = r.stdout.strip()
        major, minor = map(int, ver.split('.'))
        if (major, minor) < REQUIRED_PYTHON:
            print(f"[!] Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ is recommended. Detected {ver}.")
    except Exception as e:
        print(f"[!] Could not verify Python version: {e}")


def ensure_venv(pyc: str) -> str:
    if not VENV_DIR.exists():
        print('[+] Creating virtual environment...')
        subprocess.run([pyc, '-m', 'venv', str(VENV_DIR)], check=True)
    # Determine venv python
    vpy = VENV_DIR / 'Scripts' / 'python.exe' if os.name == 'nt' else VENV_DIR / 'bin' / 'python'
    return str(vpy)


def ensure_cua_repo() -> None:
    cua_dir = BACKEND / 'cua'
    if os.environ.get('SKIP_CUA'):
        print('[i] SKIP_CUA=1 set; skipping cua clone check.')
        return
    if not cua_dir.exists():
        print('[+] Cloning cua repo into backend/cua...')
        subprocess.run([
            'git', 'clone', 'https://github.com/trycua/cua.git', str(cua_dir)
        ], check=True)
    else:
        print('[i] cua repo already present in backend/cua.')

def pip_install(vpy: str) -> None:
    if PY_REQ.exists():
        print('[+] Installing backend requirements...')
        subprocess.run([vpy, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([vpy, '-m', 'pip', 'install', '-r', str(PY_REQ)], check=True)
    else:
        print('[i] No backend/requirements.txt found. Skipping pip install.')


def _detect_lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def launch_terminals(vpy: str, host: str, port: int) -> None:
    # Backend terminal: activate venv and run uvicorn (dev reload)
    backend_cmd = (
        f"powershell -NoExit -Command \"cd '{BACKEND}'; . .\\.venv\\Scripts\\Activate.ps1; "
        f"$env:PYTHONIOENCODING='utf-8'; $env:UVICORN_RELOAD='1'; {vpy} -m uvicorn main:app --host {host} --port {port} --reload\""
    )
    print('[+] Launching backend server in new PowerShell...')
    subprocess.Popen(backend_cmd, shell=True)

    if os.environ.get('NO_FRONTEND'):
        print('[i] NO_FRONTEND=1 set; skipping frontend dev server.')
        return
    # Frontend terminal: npm install (if needed) and run dev
    frontend_cmd = (
        f"powershell -NoExit -Command \"cd '{FRONTEND}'; if (!(Test-Path node_modules)) {{ npm install }}; npm run dev\""
    )
    print('[+] Launching frontend dev server in new PowerShell...')
    subprocess.Popen(frontend_cmd, shell=True)


def run_prod(vpy: str, host: str, port: int) -> None:
    print('[*] Production mode: ensuring frontend build...')
    dist = FRONTEND / 'dist'
    if not dist.exists():
        subprocess.run(['npm', 'install'], cwd=FRONTEND, check=True)
        subprocess.run(['npm', 'run', 'build'], cwd=FRONTEND, check=True)
    cmd = [vpy, '-m', 'uvicorn', 'main:app', '--host', host, '--port', str(port)]
    print(f"[+] Starting backend (serving built frontend) on http://{host}:{port}")
    lan_ip = _detect_lan_ip()
    if host in ('0.0.0.0', '::') and lan_ip:
        print(f"[i] LAN: http://{lan_ip}:{port}")
    subprocess.run(cmd, cwd=BACKEND, check=True)


def main():
    pyc = find_python()
    check_python_version(pyc)
    ensure_cua_repo()
    vpy = ensure_venv(pyc)
    pip_install(vpy)

    host = os.environ.get('APP_HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('APP_PORT', '8000'))
    except ValueError:
        port = 8000

    if '--prod' in sys.argv:
        run_prod(vpy, host, port)
        return

    launch_terminals(vpy, host, port)
    lan_ip = _detect_lan_ip()
    if host in ('0.0.0.0', '::') and lan_ip:
        print(f"[i] Backend API:   http://{lan_ip}:{port}")
    print('[✓] Setup complete. Dev terminals should be open (backend + frontend).')


if __name__ == '__main__':
    main()
