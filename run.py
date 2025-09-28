import os
import sys
import subprocess
import shutil
from pathlib import Path

# This script bootstraps a Python venv, installs backend requirements,
# and opens two terminals: backend (uvicorn) and frontend (npm run dev + build option).
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


def launch_terminals(vpy: str) -> None:
    # Backend terminal: activate venv and run uvicorn
    backend_cmd = (
        f"powershell -NoExit -Command \"cd '{BACKEND}'; . .\\.venv\\Scripts\\Activate.ps1; "
        f"$env:PYTHONIOENCODING='utf-8'; $env:UVICORN_RELOAD='1'; {vpy} -m uvicorn main:app --reload\""
    )
    # Frontend terminal: npm install (if needed) and run dev
    frontend_cmd = (
        f"powershell -NoExit -Command \"cd '{FRONTEND}'; if (!(Test-Path node_modules)) {{ npm install }}; npm run dev\""
    )
    print('[+] Launching backend server in new PowerShell...')
    subprocess.Popen(backend_cmd, shell=True)
    print('[+] Launching frontend dev server in new PowerShell...')
    subprocess.Popen(frontend_cmd, shell=True)


def main():
    pyc = find_python()
    check_python_version(pyc)
    ensure_cua_repo()
    vpy = ensure_venv(pyc)
    pip_install(vpy)
    launch_terminals(vpy)
    print('[✓] Setup complete. Two terminals should be open: backend and frontend.')


if __name__ == '__main__':
    main()
