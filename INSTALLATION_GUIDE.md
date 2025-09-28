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

From the project root, run the helper script:

```powershell
python run.py
```

What it does:
- Creates a virtual environment at `backend/.venv`
- Installs backend requirements
- Clones the CUA repo into `backend/cua` (requires Git in PATH)
- Launches backend (uvicorn) and frontend (Vite) in two terminals

If you prefer manual setup, continue below.

## 3) Backend dependencies (Python)

From the project root:

```powershell
python -m pip install --upgrade pip ; pip install -r requirements.txt ; pip install -r backend/requirements.txt
```

## 4) Start the backend

Run uvicorn from inside the `backend` folder and bind to all interfaces (so other devices on your LAN can access it):

```powershell
cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Notes:
- API base (local machine): http://127.0.0.1:8000
- API base (LAN devices): http://<your-LAN-IP>:8000  (e.g. `http://192.168.29.53:8000`)
- `--reload` auto-restarts on code changes (development only)
- Binding to `0.0.0.0` can trigger a Windows Firewall prompt the first time—allow on Private network if you intend LAN access.
- Keep this terminal running.

## 5) Frontend dependencies (Node)

Open a new PowerShell window:

```powershell
cd frontend ; npm install
```

## 6) Run the frontend (Vite)

```powershell
npm run dev
```

- Dev server: http://192.168.29.53:5173 (port may vary if busy)

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
