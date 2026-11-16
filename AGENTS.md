# AGENTS.md

Nex is an AI terminal assistant: Electron/TypeScript frontend + Python 3.12/FastAPI backend. Shared contracts live in `shared/` (single source of truth). UI strings, comments, and docs mix Spanish and English — match the language of the code you touch.

Repo state: `git HEAD` (Jul 2026) lags the working tree by a large in-progress refactor. Treat the working tree as the real codebase; don't "restore" deleted files or treat the ~200 ruff violations as a new regression.

## Run / dev commands

- Backend venv is at the repo root (`.venv/`) — always invoke tools from it: `.venv/bin/python`, `.venv/bin/uvicorn`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/pyright`.
- Backend server: `cd backend && ../.venv/bin/uvicorn api.routes:app --reload --host 0.0.0.0 --port 8765`. `api.routes` is now a package (`backend/api/routes/`): `application.py` builds the FastAPI app (lifespan auto-starts Nex Watch) and re-exports `app`; domain routers live in `chat.py`, `settings.py`, `system.py`, `watch.py`.
- Interactive CLI entry is the `./nex` script at the repo root (streaming Gemini chat, `nex version`, `nex set-workspace`). Provider management: `nex providers` (estado de todos) y `nex connect <provider> [--key] [--url] [--model] [--start]` (conecta FreeLLM/Ollama/cloud y los deja activos). Dentro del chat también hay `/providers`, `/connect <provider> [--key K ...]` (persiste) y `/use <provider> [model]` (solo para la sesión; rehace el provider con `build_provider`). El chat usa `llm/factory.py:build_provider`; los providers sin streaming (todo menos Gemini) funcionan vía un adaptador no-streaming en `nex:provider_iter_content`.
- Frontend (Vite dev, no backend integration in dev mode): `cd frontend && npm run dev`. No lint/typecheck scripts; `npm run build` = `vite build && tsc -p tsconfig.electron.json`. Renderer hits the backend at the hardcoded `http://127.0.0.1:8765` (`frontend/src/renderer/api.ts:1`); `src/main.ts` is a stub Electron main with mocked chat.
- Tests: `.venv/bin/python -m pytest backend/tests` (conftest injects the backend dir into `sys.path`).
- Ruff + pyright (strict) are configured in `backend/pyproject.toml` (line-length 100, select E,F,I,N,W). Note: `ruff check` still reports pre-existing violations (mainly line-length) — don't "fix" them wholesale.

## Config / env gotchas

- Settings come from the gitignored `backend/.nex_settings.json` (provider, model, temperature, workspace_path, watch/scanner options). `get_settings()` in `backend/storage/settings.py` is authoritative.
- API keys are loaded via python-dotenv from `backend/.env` (`backend/llm/gemini.py:11`); root `.env.example` is the template. Gemini uses multi-key failover (`GEMINI_API_KEY`, `_1`, `_2`, `_BACKUP`) with 429/503 cooldowns (`backend/llm/key_manager.py`). Default provider/model: `gemini` / `gemini-2.5-flash`.
- FreeLLM aggregator (15+ providers with failover) runs via `npx freellm --port 3000` — see `start-freellm.sh`; base URL `http://127.0.0.1:3000/v1` (sobreescribible con `FREELM_BASE_URL` en `.env`). `nex providers` lo marca "accesible" si responde aunque pida auth (comportamiento de `llm/connect.py:_reachable`).
- Itchaciones: la temperatura por defecto vive en `backend/.nex_settings.json`; si no existe el key, `get_temperature()` en `backend/llm/utils.py` devuelve `0.7`.

## Architecture notes

- HTTP layer is `backend/api/` (`schemas.py` + `routes/` package); business logic lives in `backend/services/`; persistence in `backend/storage/`; LLM providers in `backend/llm/`; config/prompt building in `backend/config/`; utilities in `backend/utils/`.
- Tools are registered in `backend/tools/registry.py:create_default_registry()`. Every tool call receives a `workspace_root` kwarg injected by callers (`nex`, `backend/api/routes/chat.py`). Workspace is set via `nex set-workspace` or `NEX_WORKSPACE`.
- `backend/tools/orb.py` is a thin facade over the registry (get/list/execute). Provider abstractions live in `backend/llm/*_provider.py`; OpenAI/Anthropic tool-call conversion is in `backend/llm/utils.py`. `backend/llm/factory.py:build_provider` construye cualquier provider desde settings (compartido por API `api/routes/chat.py:_get_provider` y CLI `nex`); `backend/llm/connect.py` es el motor de `nex providers`/`nex connect` (registro `PROVIDERS`, reachability, persistencia en `.env`+settings).
- Recon/OSINT/forensics tools (`backend/tools/recon.py`) are documented in `docs/recon.md`. `port_scan` is scope-limited (loopback / `scan_allowlist` in settings) — respect that.
- Nex Watch (`backend/services/watch.py`) auto-starts with the server, persists alerts to `backend/storage/.nex_alerts.json`, and hooks `run_command` to block dangerous commands.
- API surface is documented in `docs/api.md`.