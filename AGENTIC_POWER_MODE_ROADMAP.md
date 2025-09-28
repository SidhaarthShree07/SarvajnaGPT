# Agentic Power Mode Roadmap (Windows)

This document proposes a pragmatic, Windows-first roadmap to add an optional “Power Mode” to the Research Assistant so it can directly create and edit files in Microsoft Word, Excel, PowerPoint, and VS Code. The design respects your current architecture, prioritizes safety, and grows capabilities in phases.

## Goals

- Add an explicit Power Mode toggle to elevate the Research Assistant from chat to action: safely create, modify, and organize files on the user’s machine.
- Support Windows desktop apps first (Word, Excel, PowerPoint, VS Code), then optional cloud expansion via Microsoft Graph.
- Keep the system auditable and permissioned: user sees, approves, and can revoke every action.
- Reuse the existing backend (Python) and frontend (Vue + Vite) without major rewrites.

## Non‑Goals (for initial rollout)

- Full autonomous operation without user approvals.
- Complex, long-running workflows without intermediate checkpoints.
- Cross-OS support (focus on Windows first).

## Constraints and Current Architecture

- Frontend: Vue 3 (Vite) with multiple chat UIs; Research Assistant is primary surface for this feature.
- Backend: Python API (FastAPI/Starlette style) with LLM inference, memory/tag support, and TTS.
- OS: Windows 10/11. Office desktop is present in most target setups. VS Code is used.

## High-Level Architecture

- UI: Add a “Power Mode” toggle in Research Assistant header. When enabled, the model can propose actions; the user sees a preview (title, target app, changes) and approves or denies.
- Agent Layer (Backend):
  - Action registry: strongly typed actions (schemas) for Word/Excel/PowerPoint/VS Code.
  - Executors (adapters):
    - Office Desktop COM via Python (pywin32) for local automation.
    - VS Code bridge: CLI for basic file ops; VS Code Extension for richer actions (run tasks, format code, install deps).
    - Optional later: Microsoft Graph for cloud files; Office.js add-ins for in-app automation.
  - Safety: per-action permissions, path allowlist, dry-run previews, rate limits, full audit log.
- LLM Orchestration: Function-calling/spec-based tools, deterministic schema matching. The LLM suggests structured actions; backend validates and executes only after user approval.

## Action Catalog (MVP)

Each action carries a schema, preconditions, and an executor.

- word.create_document
  - Inputs: path, file_name, optional template_path, content_blocks[] (heading/body/ordered-list/bulleted-list/code-block)
  - Output: absolute_path
  - Executor: COM (Word.Application)
- word.append_content
  - Inputs: absolute_path, content_blocks[]
  - Precondition: file exists and is a .doc/.docx
- excel.create_workbook
  - Inputs: path, file_name, sheets[] { name, table? }
  - Executor: COM (Excel.Application)
- excel.write_table
  - Inputs: absolute_path, sheet_name, start_cell, rows[] (array of arrays)
- ppt.create_presentation
  - Inputs: path, file_name, slides[] { title, bullets[], image_paths[]? }
  - Executor: COM (PowerPoint.Application)
- ppt.append_slide
  - Inputs: absolute_path, layout, title, bullets[]
- vsc.init_project
  - Inputs: path, name, template ("python-app"|"node-app"|"html-css"), open_in_vscode (bool)
  - Executor: 
    - Phase 1: File scaffolding + `code` CLI to open workspace
    - Phase 2: VS Code Extension over WebSocket for richer commands
- fs.write_file (safety-scoped)
  - Inputs: absolute_path (must be under an approved base folder), content, encoding
- fs.create_folder
  - Inputs: parent_path (approved), name

All actions log: user, time, action schema, params (redacted sensitive), result, errors.

## Safety and Permissions

- Toggle: Power Mode is off by default; no actions execute without it.
- Approvals: Each proposed action is displayed to the user with:
  - Summary (e.g., “Create Word doc ‘Summary.docx’ in Documents/Reports”).
  - Details: target app, path, change size (#slides, rows), preview snippet.
  - User can Approve, Deny, or Edit parameters (e.g., rename file, change folder).
- Paths: Restrict to an allowlist (e.g., Documents/Sarvajna, Desktop/Sarvajna, custom project folder). No writes outside.
- Rate limiting: Max N actions per minute; batch similar actions into one step where possible.
- Dry-run: Executors support “plan only” mode to render a preview (e.g., slide count, sheet names) before commit.
- Audit: Persistent log file and UI view under “Activity”.

## Integration Options per App

- Word/Excel/PowerPoint (Windows Desktop)
  - MVP: Python COM via pywin32 to drive Office apps locally (reliable and fast on Windows).
  - Later: Microsoft Graph for cloud storage and Excel online editing; Office.js add-ins for deeper in-app features.
- VS Code
  - MVP: Use `code` CLI to open a folder; create files/folders from backend; optionally run `npm init`, `pip`, etc. with confirmation.
  - Phase 2: VS Code Extension “Sarvajna Agent Bridge” that connects to the backend via WebSocket and exposes safe commands:
    - Create/edit files, run tasks, select workspace folder, show diff preview, format document.

## Backend Changes (Python)

- Data models
  - Action schema definitions (Pydantic): id, type, params, preconditions, preview, result.
  - Audit entry model.
- Endpoints
  - POST /api/agent/plan: Input text/context → returns proposed actions[] (LLM-planned)
  - POST /api/agent/preview: action → preview summary (no side effects)
  - POST /api/agent/execute: action(s) → executes after approval
  - GET /api/agent/logs: recent activity
- Executors
  - COM helpers: word.py, excel.py, powerpoint.py with idempotent creation and robust error handling (retry if instance busy).
  - VS Code bridge: file ops, run `code` (if present), and later socket handshake with the extension.
- LLM tool binding
  - Define function-calling specs for each action.
  - Guardrails: validate/normalize paths; deny unknown actions; refuse actions if Power Mode off.

## Frontend Changes (Vue)

- Power Mode toggle in `ResearchAssistant.vue` header; persistent per session.
- “Proposed Actions” drawer for each AI message when Power Mode is on.
  - Shows a list with previews; buttons: Preview, Approve, Deny, Edit.
- Settings page
  - Allowed paths (pickers), default save location.
  - Office integration mode: Local (COM) vs Cloud (Graph) [future], and sign-in status.
  - VS Code integration: detect `code` CLI, install/enable extension.
- Notifications for execution results; link to open file or open containing folder.

## Windows Setup and Dependencies

- Python 3.11+ environment (already present in repo). Add:
  - pywin32 for COM automation.
  - watchdog (optional) for file change events.
- Office Desktop installed (Word/Excel/PowerPoint). Ensure trusted access to VBA project off is fine (COM does not require macros).
- VS Code installed with `code` in PATH.
- Optional later: Microsoft Graph app registration for OneDrive/SharePoint access (Device Code flow); store token securely.

### Example pip additions (Windows PowerShell)

```powershell
# In backend venv
pip install pywin32 watchdog pydantic
```

## MVP Scenarios (End-to-End)

1) Research summary to Word
- User: “Summarize this topic into a one-page report with 3 headings.”
- AI (Power Mode on): Proposes word.create_document → Summary.docx → Documents/Sarvajna/Reports.
- User approves → Backend COM writes headings and paragraphs → UI offers “Open file”/“Open folder”.

2) Data table to Excel
- User: “Put this table in Excel with columns A,B,C and 10 rows.”
- AI proposes excel.create_workbook + excel.write_table.
- After approval, COM creates workbook, writes rows, auto fits columns.

3) Slides from outline
- User: “Make 5 slides from this outline.”
- AI proposes ppt.create_presentation with 5 slides (title + bullets). User reviews, approves.

4) Scaffold a VS Code project
- User: “Create a Node app called demo-api with an index.js and a README.”
- AI proposes vsc.init_project (path: Documents/Sarvajna/Projects/demo-api).
- On approval: backend creates folder/files and opens in VS Code; later the extension can run npm init on confirmation.

## Phased Delivery Plan

Phase 0 – Foundations (1 week)
- Define action schemas; implement server-side validation and audit logging.
- Frontend: Power Mode toggle, drawer UI skeleton, approve/deny interaction.

Phase 1 – Local Office + Basic VS Code (1–2 weeks)
- Implement COM executors for Word/Excel/PowerPoint with previews and safe output paths.
- Implement file/folder ops and VS Code open via CLI. Ship MVP scenarios.

Phase 2 – VS Code Extension Bridge (1–2 weeks)
- Build “Sarvajna Agent Bridge” extension: WebSocket client to backend; expose commands (create/edit/show-diff/run-task).
- Frontend wires “Run in VS Code” to extension commands when present, else falls back to CLI.

Phase 3 – Microsoft Graph (optional, 2 weeks)
- Support cloud save/open in OneDrive/SharePoint; add sign-in + token storage.
- Excel Graph API for table operations; Word/PPT uploads and template handling.

Phase 4 – Office.js Add-ins (optional, 2–3 weeks)
- Word/Excel Add-ins for richer in-app manipulations and live previews.
- Bridge add-ins to backend action layer.

Phase 5 – Advanced Agentic Behaviors (continuous)
- Multi-step planning with checkpoints, retry/recovery, and user constraints (time budget, change budget).
- “Intent memory” of last used folders and templates per chat.

## Risks and Mitigations

- COM brittleness / version differences → Implement retries, explicit waits, and strong error handling; document supported Office versions.
- Path safety → Strict allowlists + denylist (Windows system dirs) + always show preview.
- LLM overreach → Power Mode toggle + per-action approvals + rate limiting + schema validation.
- Security/privacy → No network uploads by default; Graph integration opt-in; redact sensitive params in logs.

## Testing Strategy

- Unit tests for action schemas/validators.
- Integration tests for COM executors in a CI-like Windows environment (or manual test matrix by Office version).
- End-to-end smoke scripts for MVP scenarios.
- Telemetry on failures with actionable error messages.

## API and Schema Sketch

Action (Pydantic):
- id: string
- type: enum (word.create_document, excel.write_table, …)
- params: dict (validated by specific model)
- preview_only: bool

Endpoints:
- POST /api/agent/plan → { actions: Action[] }
- POST /api/agent/preview → { action, preview }
- POST /api/agent/execute → { results[] }
- GET /api/agent/logs → { entries[] }

Frontend:
- On AI response with proposed actions: show drawer; let user Preview/Approve/Deny.
- After execution: surface links/buttons.

## Optional UI Automation (advanced)

If needed for app surfaces without an API, consider a UI automation layer (e.g., Windows UI Automation wrappers). Use this selectively and behind explicit approvals; prefer first-class SDKs (COM/Graph/Office.js) whenever possible.

---

This roadmap is designed to be immediately actionable on Windows with minimal disruption to your current codebase. We can start with Phase 0/1 and ship a usable MVP, then iterate toward the extension and cloud integrations.

## CUA Integration (Computer Use Agents)

This section details how to integrate a Computer Use Agents (CUA) stack to execute desktop UI automation in a sandboxed environment when native adapters (COM, VS Code extension/CLI) are insufficient.

### What CUA provides

- A managed runtime (“Docker for computer-use agents”) where models can control a full desktop (mouse, keyboard, screen, clipboard, file system) inside a VM/session.
- Two main layers:
  - Agent SDK: Runs computer-use models with a standardized output schema (aligned with OpenAI-style computer-use/tool-call responses), orchestrating the think → act → observe loop.
  - Computer SDK: Provides the primitives to operate the VM (launch apps, click/type, capture screen, transfer files) with logging and replay.
- Model/provider flexibility: Supports multiple providers and model families; you can swap models without changing orchestration code.
- Telemetry and audit: Captures step-by-step actions with screenshots/video for review and debugging.

### When to use CUA vs. native adapters

- Prefer native adapters first (fast, deterministic, offline):
  - Word/Excel/PowerPoint via COM for structured document operations.
  - VS Code via CLI/extension for file/project automation.
- Use CUA when you need:
  - UI flows not covered by any API (first-run wizards, modal dialogs, template galleries).
  - Cross-app workflows (copying between apps, browser-based steps) or web automation.
  - Strong isolation/auditing (run risky actions inside a sandbox VM with video replay).
- Hybrid strategy: Plan with our schema; route each action to the best executor. Fall back to CUA only when a task requires UI-only steps or explicit sandboxing.

### Architecture fit in our plan → preview → execute loop

1) Planning: The LLM produces structured actions (e.g., word.create_document). We add a hint flag like requires_ui or executor="cua" when APIs are insufficient.
2) Preview: If routed to CUA, render a human-readable plan and risk summary (apps involved, estimated steps, VM target image). No VM is started yet.
3) Approval: User approves per-action (or a short batch).
4) Execution: Backend spins up (or attaches to) a CUA session, streams events, and saves artifacts back to an allowlisted shared folder.
5) Audit: Store the CUA transcript and optional video link; surface a summary to the Activity log.

### Windows setup considerations

- MVP does not require CUA. CUA is optional and can be enabled later for UI-only gaps or sandboxing.
- If adopting CUA:
  - Provision a Windows image with Office (Word/Excel/PowerPoint) and VS Code preinstalled.
  - Define a shared folder for artifact exchange (e.g., \\host\sarvajna-share or a cloud bucket mounted inside the VM).
  - Configure model provider credentials for computer-use capable models.
  - Expect higher latency/cost than local COM; reserve for cases where it adds clear value.

### Backend wiring (adapter)

- Add a CuaClient adapter with responsibilities:
  - Start/attach to a session with the requested base image.
  - Push initial artifacts (e.g., a markdown draft for a report, CSV for tables).
  - Instruct the agent with an objective and constraints (allowed folders, time budget).
  - Stream back events for live UI (optional) and collect final artifacts.
  - Enforce timeouts, retries, and ensure teardown.
- Persist: transcript, timestamps, model identity, and artifact paths.

### Orchestration flow (pseudocode)

```text
actions = plan_actions(user_prompt, context)
for a in actions:
  if a.executor == "native":
    preview = native_preview(a)
  else:
    preview = cua_preview(a)  # Describe intended UI flow + artifacts

show(preview)
if approved:
  if a.executor == "native":
    result = native_execute(a)
  else:
    session = cua.start_session(image="win11-office-vscode", share=allowed_share)
    objective = render_objective_from_action(a, artifacts=preseed_files)
    stream = session.run(objective, constraints={
      "allowed_paths": [allowed_share],
      "time_budget_s": 600,
      "no_network": true
    })
    # Optionally display streamed events (thumbnails/step text)
    result = session.collect_artifacts()
  audit_log.append(a, preview, result)
return summarize_results(actions)
```

### Mapping our action catalog to CUA

- word.create_document / word.append_content
  - Provide a content.md file in the shared folder; ask CUA to open Word, paste/format content, and save to "share/…/Summary.docx".
- excel.create_workbook / excel.write_table
  - Provide a data.csv; instruct CUA to create a workbook, import CSV, auto-fit, and save.
- ppt.create_presentation / ppt.append_slide
  - Provide an outline.md; instruct CUA to build slides from headings/bullets and save.
- vsc.init_project
  - Provide a folder skeleton or instructions; ask CUA to open VS Code, create files, and run safe commands as allowed.
- fs.write_file / fs.create_folder
  - Prefer native; only route to CUA if it must be created via UI in a target app.

### Safety model with CUA

- Isolation: All CUA actions run in a VM, never directly on the host.
- Path control: Only share a dedicated allowlisted folder between host and VM.
- Approvals: Maintain the same per-action approval gates; show an execution plan and estimated step count.
- Observability: Keep transcripts/screenshots/video for each run; surface a link in Activity.
- Data handling: Redact secrets in prompts/artifacts; default to no network inside the VM unless explicitly allowed.

### Phasing with CUA

- Phase 0/1: Ship native COM/VS Code MVP.
- Phase 2: Build VS Code extension bridge.
- Phase 2.5 (optional): Introduce CUA adapter for UI-only workflows and sandboxing. Start with a single scenario (e.g., importing a complex Word template) and add routing logic.
- Phase 3+: Expand scenarios, add browser flows (research + document creation), and richer streaming UI.

### Known trade-offs

- Performance: CUA adds session spin-up and model loop latency; use selectively.
- Reliability: UI automation can be brittle across app versions; prefer native when available.
- Cost: VM + model cost vs. local COM.
- Maintenance: Keep a golden Windows image updated with Office/VS Code; version it and test before promotion.

### Minimal acceptance criteria for a first CUA-backed scenario

- Backend flag enables CUA routing for a specific action.
- Action preview clearly indicates CUA usage and target image.
- Successful end-to-end: artifacts seeded → VM session runs → file saved to shared folder → host copies into allowlisted path → audit log recorded.
