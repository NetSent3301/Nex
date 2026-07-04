# Nex — AI Terminal Assistant

Nex is an AI-powered coding assistant that runs directly in your terminal. It understands your entire project, executes commands, edits files, searches code, and integrates with multiple LLM providers.

## Architecture

```
Frontend (Electron/TS) ──HTTP──▶ Backend (Python/FastAPI)
                                      │
                                      ├── api/     — REST + SSE endpoints
                                      ├── llm/     — Gemini, OpenAI, Anthropic, DeepSeek, Ollama
                                      ├── tools/   — 20+ tools (read/write, search, git, terminal, web, LSP)
                                      ├── agent/   — Cognitive loop with planning
                                      └── storage/ — Session memory, settings, history
```

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
