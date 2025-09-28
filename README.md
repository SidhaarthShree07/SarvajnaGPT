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

Quick start (Windows):

```powershell
python run.py
```

This will:
- Create a venv in `backend/.venv`
- Install backend requirements
- Auto-clone the CUA repo to `backend/cua` (no manual folder creation)
- Launch backend (uvicorn) and frontend (Vite) in two terminals

Requirements: Git, Python 3.11+, Node.js 18+.

For manual setup or extra details, see INSTALLATION_GUIDE.md.

### Manual backend start

If you prefer to launch the backend manually instead of using `run.py`:

```powershell
cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Why this form?
- `cd backend` lets uvicorn import `main:app` without the `backend.` prefix.
- `--host 0.0.0.0` exposes the API to your LAN (so you can hit it from another device). Use `127.0.0.1` if you want to restrict to local machine.
- `--reload` is convenient during development (hot-reloads). Omit it for production.

After starting, open another terminal for the frontend:

```powershell
cd frontend; npm install; npm run dev
```

Then visit the shown Vite dev URL (usually http://localhost:5173 or http://<LAN-IP>:5173).

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

## Project Structure

```
SarvajñaGPT/
├─ backend/
│  ├─ main.py               # FastAPI app and endpoints (chat, memory, models)
│  ├─ llm_inference.py      # Ollama inference + model persistence
│  └─ ...
├─ frontend/
│  ├─ src/
│  │  ├─ App.vue            # App shell: agents, model modals, carousel
│  │  └─ components/        # ResearchAssistant, MemoryManager, etc.
│  └─ ...
├─ requirements.txt         # Root Python deps
└─ backend/requirements.txt # Backend-specific deps
```

## Troubleshooting

- Frontend doesn’t start (port busy)
   - Vite uses 5173 by default; if busy, it will prompt to use another port. Accept the prompt and reload the page.
- Backend not reachable
   - Confirm `uvicorn` is running on 127.0.0.1:8000 and not blocked by a firewall
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
