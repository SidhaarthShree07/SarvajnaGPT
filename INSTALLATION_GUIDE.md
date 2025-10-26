# Installation Guide (Windows)

This guide covers installing and running SarvajñaGPT on Windows using PowerShell.

## Prerequisites

- Windows 10/11
- PowerShell
- Python 3.11+
- Node.js 18+
- Ollama (local model runtime): https://ollama.com

## 1) Clone and open the project

```powershell
# Using Git
# git clone https://github.com/<your-username>/Sarvajna-GPT.git
# cd Sarvajna-GPT
```

## 2) Quick start (recommended)

From the project root, run:

```powershell
python run.py
```

It will:
1. Create `backend/.venv`
2. Install Python deps from `backend/requirements.txt` (canonical list)
3. Clone CUA into `backend/cua` if missing
4. Launch uvicorn (FastAPI) + Vite dev server in separate PowerShell windows

Access (dev UI): typically http://localhost:5173  (shows on terminal)  
API base (dev): http://192.168.29.53:8000

## 3) Backend dependencies (Python)

Canonical dependency file is `backend/requirements.txt`. (Root requirements.txt was removed.)

```powershell
python -m pip install --upgrade pip ; pip install -r backend/requirements.txt
```

## 4) Start the backend

Launch uvicorn from inside `backend` and bind to all interfaces if you want LAN access:

```powershell
cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Access:
- LAN Access: http://192.168.29.53:8000 (replace with your machine's LAN IP if different)

Notes:
- `--reload` is for development (auto restart). Remove for production.
- First bind to 0.0.0.0 may prompt Windows Firewall—allow Private if you need LAN.

## 5) Frontend dependencies (Node)

Open a new PowerShell window:

```powershell
cd frontend ; npm install
```

## 6) Run or build the frontend

Dev (hot reload):

```powershell
npm run dev
```

Production build (served by backend when you hit :8000):

```powershell
npm run build
```

After build, restart (or start) the backend and open http://192.168.29.53:8000 — the static bundle is mounted automatically if `frontend/dist` exists.

## 7) Model management (Ollama)

- Ensure the Ollama app/service is running locally
- In the app header, click the model chip to open the modal
  - Installed: Lists models detected from Ollama
  - Recommended: Shows curated choices with estimated disk usage
- Install a model: Click Install, review the PowerShell command (e.g., `ollama pull qwen2.5:7b`), then confirm
- Set active model: Click Use; your selection persists across restarts

## Troubleshooting

- Frontend port busy: Vite will prompt to switch ports; accept the prompt
- Backend not reachable: Ensure uvicorn is running and not blocked by firewall
- “No models found”: Confirm Ollama is running; try Refresh in the modal
- Install failed: Check internet and disk space; you can run `ollama pull <model>` manually in PowerShell
- Poor output quality: Try a different model from the selector or refine context using #tags in the Memory Manager
 - Word integration (selection/paste):
   - If selection isn’t detected, enable selection monitoring in the Power Mode UI and approve clipboard access in the browser if prompted
   - Reselect text in Word and press Ctrl+C once to refresh the selection state, then send your prompt again
   - By default, enhanced text is copied to your clipboard; switch to Word and press Ctrl+V to replace your current selection manually (preserves split and formatting)
