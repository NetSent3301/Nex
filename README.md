# Nex

**Nex** is an AI-powered coding assistant that runs directly in your terminal. It understands your entire codebase, executes commands, edits files, searches across projects, and integrates with multiple leading LLM providers, all while keeping your workflow fast and distraction-free.

---

## ✨ Features

- 🤖 **Multi-Provider AI**
  - Gemini
  - OpenAI GPT
  - Claude
  - DeepSeek
  - Ollama (local models)

- 🛠️ **Powerful Tooling**
  - Read & write files
  - Search codebases
  - Execute shell commands
  - Git integration
  - Web search & fetching
  - Language Server Protocol (LSP)
  - Project-aware context

- 🧠 **Intelligent Agent**
  - Autonomous planning
  - Multi-step reasoning
  - Tool orchestration
  - Context-aware execution

- 👁️ **Vision Support**
  - Drag & drop images
  - Paste screenshots
  - File picker support

- ⚡ **Real-Time Streaming**
  - Live responses
  - Tool execution cards
  - Streaming output

- 💾 **Persistent Memory**
  - Conversation history
  - Sessions
  - Settings
  - Context persistence

- 🔌 **Extensible**
  - Custom skills
  - MCP server support
  - Modular tool system

---

## 🏗️ Architecture

```
Frontend (Electron + TypeScript)
            │
          HTTP/SSE
            │
            ▼
Backend (Python + FastAPI)
│
├── api/       REST & streaming endpoints
├── agent/     Planning and reasoning engine
├── llm/       AI provider integrations
├── tools/     Built-in tool system
├── storage/   Sessions, memory & settings
└── core/      Shared backend logic
```

---

## 🚀 Quick Start

### Start the backend

```bash
./nex
```

Or manually:

```bash
cd backend
../.venv/bin/uvicorn api.routes:app \
    --reload \
    --host 0.0.0.0 \
    --port 8765
```

### Start the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ Configuration

Configure your API keys through the Settings panel or by editing:

```
backend/.env
```

Example:

```env
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
```

---

## 📋 Requirements

- Python **3.12+**
- Node.js **20+**
- Electron

---

## 📄 License

Released under the **MIT License**.
