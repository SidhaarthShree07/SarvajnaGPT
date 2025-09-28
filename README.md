# SarvajñaGPT

Agentic, offline-first AI on your PC. SarvajñaGPT orchestrates multiple purposeful agents (Research Assistant, Beginner-Friendly Teacher, Homework Helper, Daily Life Companion) with a Memory Manager, tag-aware context, and local multi-model control via Ollama.

Unlike a simple “local model runner,” SarvajñaGPT adds planning, context, and tools around your models so the AI acts with intent and remembers what matters to you—while keeping your data on your machine.

## Key Highlights

- Offline-first by design
   - Runs entirely on your machine. Keep your data local. No cloud required.
- Multi-model, hot-swappable
   - Discover, install, and switch Ollama models from the UI. Your choice persists across restarts.
- Agentic AI out of the box
   - Specialized agents with distinct goals and system prompts: Research Assistant, Teacher, Homework Helper, Daily Life.
   - Each agent inherits the Memory Manager, tag UI, and folder-first context resolution.
- Memory Manager with tags
   - Organize knowledge using #tags. Folder-level tags take precedence over file-level tags when composing context.
   - Inline tag suggestions while typing. Selected tags appear as chips and are sent with your request.
- Clean, presentable chats
   - Safe-markdown rendering preserves headings, bold, and inline code without messy artifacts.
- Thoughtful UX
   - Model picker with glass modals, disk estimate, install preview, and a responsive home carousel for quick entry into agents.

## Mobile Features & Responsive UX

SarvajñaGPT is designed to stay usable and efficient on smaller screens (phones / small tablets):

- Responsive layout
   - Core views adapt with Tailwind-style breakpoints; side panels collapse or become drawers.
   - Memory Manager and chat panes stack vertically on narrow widths.
- Mobile‑only sticky input bar
   - Chat input for agents (Homework Helper, Beginner Teacher, Daily Life, etc.) becomes a sticky bar at the bottom on small screens (`sticky bottom-0`) while remaining non-sticky on desktop.
   - Extra bottom padding (`pb-28`) is applied to the messages list so the final message isn’t hidden behind the bar.
- Scrollable chat region
   - Chats get an internal scroll container with custom scrollbar styling; smooth auto-scroll to latest message on send / receive.
- Attachment & preview flow
   - Image (jpg/png/webp), PDF, DOCX and text file uploads supported from mobile file picker.
   - Image previews render as small “chips” above the input before sending; temporary object URLs are revoked after send/removal to avoid leaks.
   - OCR / text extraction automatically runs for images and non-plain-text docs; extracted text is appended under a `[Document Content]:` section sent to the model.
- Tag input & suggestions
   - Inline `#tag` detection works with touch keyboards; suggestion panel appears above the keyboard area and can be tapped to add chips.
- Hamburger & drawer patterns
   - Mobile-only hamburger toggles side navigation or memory context panels; hidden entirely on larger breakpoints to reduce duplication.
- Touch-friendly controls
   - Larger tap targets (rounded buttons, spacing) and minimal hover dependence; icons rely on accessible labels.
- Performance safeguards
   - Limits on inline selection and extraction size; large file previews avoided.
   - Object URL cleanup + lightweight markdown rendering reduce memory churn on lower-end devices.
- Graceful fallback
   - If localStorage or clipboard APIs are unavailable (private browsing / restrictive mobile WebViews), feature code guards and silently degrades instead of erroring.

Planned mobile enhancements (roadmap): in-chat audio recording button, simplified memory tagging drawer, and offline-first caching of recent chats.

## Architecture

- Frontend: Vue 3 + Vite + Tailwind-style utilities
   - Main shell in `frontend/src/App.vue`
   - Agent components: ResearchAssistant, Translator, BeginnerTeacher, HomeworkHelper, DailyLife, MemoryManager
   - Model management UI: lists installed and recommended models, installs via PowerShell, sets active model
- Backend: FastAPI
   - Inference via local Ollama HTTP, with service-aware prompts and short chat history context
   - Selected model persisted to disk and restored on startup
   - Memory/embeddings: research-first retrieval (SQLite + embeddings) with folder-first tag resolution
   - Automation: `run.py` auto-clones https://github.com/trycua/cua into `backend/cua`

## Installation

You can run SarvajñaGPT in two modes: Quick Dev (auto spawns two terminals) or Manual (production‑style single backend serving built frontend).

### 1. Quick Dev (Windows)

```powershell
python run.py
```

What this does:
1. Creates a virtual environment at `backend/.venv`.
2. Installs Python dependencies from `backend/requirements.txt` (canonical list; root requirements file was removed).
3. Clones the CUA repo into `backend/cua` if missing.
4. Starts FastAPI (uvicorn with `--reload`) and Vite dev server (hot module reload) in separate PowerShell windows.

Access the app (dev): http://localhost:5173 (or the alternative port Vite shows if 5173 is busy).

### 2. Manual / Production‑Style

Build the frontend once, then let the backend serve the static bundle on port 8000.

```powershell
# From project root
cd frontend; npm install; npm run build
cd ..\backend; python -m venv .venv; . .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Access the app at: http://192.168.29.53:8000 (use your machine's LAN IP if different)

Notes:
- The backend auto-detects `../frontend/dist` and serves it at `/` if present.
- `--reload` is for development; remove it for a quieter production process.
- All Python deps live in `backend/requirements.txt` (root file intentionally removed).

### 3. Minimal Manual Backend (no build yet)

If you only want the API first:

```powershell
cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Later you can build the frontend and refresh the page at http://192.168.29.53:8000 to get the UI.

### Requirements

Git, Python 3.11+, Node.js 18+, (optional) Ollama running locally for models.

For deeper troubleshooting steps see `INSTALLATION_GUIDE.md`.

## Model Management (Ollama)

- Open the model selector (top-right chip in the header)
   - “Installed” tab lists models detected from Ollama
   - “Recommended” tab offers curated picks with estimated sizes
- Install a model
   - Click Install to see the exact PowerShell command (e.g., `ollama pull qwen2.5:7b`), then confirm to run from the backend
- Set the active model
   - Click Use on any installed model; the selection persists across app restarts

Notes
- Ensure the Ollama service/app is running locally before using the model selector
- Disk space matters; some models are large (billions of parameters)

## Agentic AI: What you get

- Purpose-built agents
   - Research Assistant: fact-finding and summarization with retrieval from your tagged knowledge
   - Beginner-Friendly Teacher: teaches concepts step-by-step with simple language
   - Homework Helper: guides to solutions with structure and clarity
   - Daily Life Companion: planning and organizing routines
- Memory + Tags
   - Compose context by selecting #tags inline (folder-first resolution)
   - Tag chips appear next to the input and are sent with the message
   - Aggregated batches in the backend still appear as a single file in the Memory Manager UI (cleaner mental model)
- Clean outputs
   - Chat markdown is sanitized and styled for readability, preserving emphasis and code formatting

## Project Structure (simplified)

```
SarvajñaGPT/
├─ backend/                 # FastAPI app, automation, embeddings
│  ├─ main.py               # Core API + static mount of built frontend
│  ├─ llm_inference.py      # Model selection + Ollama bridge
│  └─ requirements.txt      # Canonical Python dependency list
├─ frontend/                # Vue 3 + Vite source
│  ├─ src/                  # Components & views
│  └─ dist/                 # Built assets (created by npm run build)
└─ run.py                   # Dev convenience launcher (spawns both servers)
```

## Troubleshooting

- Frontend doesn’t start (port busy)
   - Vite uses 5173 by default; if busy, it will prompt to use another port. Accept the prompt and reload the page.
- Backend not reachable
   - Confirm `uvicorn` is running on http://192.168.29.53:8000 (or your LAN IP) and not blocked by a firewall
- “No models found” in the modal
   - Ensure the Ollama app/service is running locally
   - Try refreshing the list from the modal
- Install failed
   - Check disk space and internet connectivity (only for model download)
   - You can run the shown `ollama pull <model>` command manually in PowerShell
- Responses look odd
   - Try a different model from the selector, or adjust your tags to refine context

## Why SarvajñaGPT vs. other local AI options?

| Capability | SarvajñaGPT | Ollama CLI | Typical Ollama Web UI | Typical NVIDIA Local Stack |
|---|---|---|---|---|
| Offline-first | Yes | Yes | Yes | Yes |
| Multi-model management (discover, install, set active) | Built-in UI with persistence | Manual CLI (`ollama pull`, env vars) | Varies, often basic | Varies, manual |
| Agentic roles (Research, Teacher, Homework, Daily Life) | Yes, curated prompts + behaviors | No | Rarely | Varies |
| Memory Manager with #tags | Yes, folder-first resolution + inline chips | No | Rarely | Varies |
| Context assembly from tags | Yes | No | Rarely | Varies |
| Clean, safe markdown outputs | Yes | N/A | Varies | Varies |
| Windows-first setup (PowerShell) | Yes | Yes (CLI) | Varies | Varies |
| Persistence of selected model | Yes (disk-backed) | No (per-run) | Rarely | Varies |
| Carousel/home UX to agents | Yes | N/A | Varies | N/A |
| Extensibility (frontend + FastAPI) | High | N/A (CLI) | Medium | Medium/High |

Bottom line: Ollama is excellent for running models; SarvajñaGPT is an agentic layer on top—private, purposeful, and easy to operate.

## License

MIT (see LICENSE if provided). If no license file exists, treat as All Rights Reserved until one is added.
