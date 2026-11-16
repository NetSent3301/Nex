# Nex — AI Terminal Assistant

Nex is an AI-powered coding assistant that runs directly in your terminal. It understands your entire project, executes commands, edits files, searches code, and integrates with multiple LLM providers.

## Architecture

```
Frontend (Electron/TS) ──HTTP──▶ Backend (Python/FastAPI)
                                      │
                                      ├── api/     — REST + SSE endpoints (routes/ por dominio)
                                      ├── config/  — Prompt base + contexto del workspace
                                      ├── llm/     — Gemini, OpenAI, Anthropic, DeepSeek, Ollama, FreeLLM
                                      ├── services/— Nex Watch (alertas de seguridad)
                                      ├── storage/ — Settings + historial de sesiones
                                      ├── tools/   — 20+ tools (read/write, search, git, terminal, web, LSP, recon)
                                      └── web/     — UI web embebida
```

## Orb

The **Orb** is a thin facade over the tool registry (`backend/tools/orb.py`):

- `Orb().get_tool(name)` — Retrieve a specific tool by name
- `Orb().list_tools()` — List all available tools
- `Orb().execute(name, **kwargs)` — Execute a tool operation
- `Orb().get_all_tools_metadata()` — Full tool metadata for LLM prompting

Usage:
```python
from tools.orb import Orb
orb = Orb()
tools = orb.list_tools()
```

## Tool Cleanup

v0.2.0: Removed/refactored redundant tools:
- **RefactorTool**: Basic regex-based operations; use filesystem tools directly
- **MCPTool**: Requires external MCP server configuration; optional integration

Core tools remain: filesystem, git, web, recon, LSP, skills, sessions, images.

## Providers

Gestiona los proveedores LLM desde el CLI (se comparten con la API en `http://127.0.0.1:8765`):

```bash
nex providers                  # Estado de todos (accesible / key / modelos / activo)
nex connect freellm            # Conecta el agregador local (o --start para arrancarlo)
nex connect ollama             # Modelos Ollama locales (autodetecta)
nex connect ollama --model gemma3:1b
nex connect gemini --key GEMINI_API_KEY_de_la_cuenta
nex connect openai --key sk-... --model gpt-4o
nex chat --provider ollama     # Chat usando otro provider
```

FreeLLM: `nex connect freellm --start` arranca el agregador (requiere `node_modules/frontend`).

También se pueden gestionar desde dentro del chat (`nex chat`):

```
/providers                  Estado de todos los proveedores
/connect ollama gemma3:1b   Conecta y activa (flags: --key K --url U --model M --start)
/use openai gpt-4o          Cambia de provider/modelo solo para esta sesión (no persiste)
```

En el prompt interactivo: escribe `/` y se abre una pequeña ventana flotante de
autocompletado justo encima (`↑/↓` navegan, `Tab` completa, `Enter` acepta);
`↑/↓` sin menú navegan el historial.

## Quick Start

```bash
# Start backend
./nex

# Or manually:
cd backend && ../.venv/bin/uvicorn api.routes:app --reload --host 0.0.0.0 --port 8765

# Frontend (dev):
cd frontend && npm run dev
```

## Features

- **Multi-provider LLM**: Gemini, GPT-4o, Claude, DeepSeek, Ollama
- **Tool execution**: Read/write/search files, run commands, git, web fetch/search, LSP
- **Orb orchestrator**: Unified tool access and configuration
- **Vision**: Send images via drag-drop, paste, or file picker
- **Streaming responses**: Real-time output with tool call cards
- **Session memory**: Persistent chat history across sessions
- **Custom agents & skills**: Extensible via Markdown skills and MCP servers

## Configuration

Set your API keys in the settings panel or directly in `backend/.env`:

```
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
```

## Requirements

- Python 3.12+
- Node.js 20+
- Electron (for desktop UI)

## License

MIT
