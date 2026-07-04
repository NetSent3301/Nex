# Nex — Documentación Completa del Proyecto

**Versión:** 0.1.0-dev  
**Repositorio:** https://github.com/NetSent3301/Nex  
**Stack principal:** Python/FastAPI + Electron/TypeScript

---

## Índice

1. [Visión General](#1-visión-general)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Backend — FastAPI](#3-backend--fastapi)
   - 3.1 [API Endpoints](#31-api-endpoints)
   - 3.2 [Sistema de LLM Providers](#32-sistema-de-llm-providers)
   - 3.3 [Sistema de Tools](#33-sistema-de-tools)
   - 3.4 [Sistema de Persistencia](#34-sistema-de-persistencia)
   - 3.5 [Configuración](#35-configuración)
   - 3.6 [CLI (Typer)](#36-cli-typer)
   - 3.7 [Sistema de Agentes (no integrado)](#37-sistema-de-agentes-no-integrado)
   - 3.8 [Stubs y Código Muerto](#38-stubs-y-código-muerto)
4. [Frontend — Electron/TypeScript](#4-frontend--electrontypescript)
   - 4.1 [Arquitectura](#41-arquitectura)
   - 4.2 [Componentes](#42-componentes)
   - 4.3 [Renderizador](#43-renderizador)
   - 4.4 [Estilos](#44-estilos)
5. [Shared — Protocolo Compartido](#5-shared--protocolo-compartido)
6. [Flujo de Datos](#6-flujo-de-datos)
7. [Seguridad](#7-seguridad)
8. [Despliegue y Desarrollo](#8-despliegue-y-desarrollo)

---

## 1. Visión General

Nex es un **asistente terminal AI** con interfaz web y de escritorio (Electron). El core es un backend Python/FastAPI que conecta con **5 proveedores LLM** (Gemini, OpenAI, Anthropic, DeepSeek, Ollama) y expone **23 herramientas** que el modelo puede invocar autónomamente para operar sobre el sistema de archivos, ejecutar comandos, buscar en web, interactuar con git, analizar código, etc.

### Capacidades principales

- Chat conversacional con historial persistente por sesión
- Streaming de respuestas vía Server-Sent Events (SSE)
- Ejecución autónoma multi-paso (hasta 10 iteraciones de modelo → herramienta → modelo)
- 23 herramientas agrupadas en: sistema de archivos, terminal, git, web, análisis de código, refactorización, imágenes, MCP, LSP, skills y sesiones
- 5 proveedores LLM intercambiables (Gemini, OpenAI, Anthropic, DeepSeek, Ollama)
- Interfaz de escritorio (Electron + TypeScript vanilla) e interfaz web standalone
- Configuración persistente con exportación/importación JSON
- Gestión de API keys con rotación y blacklisting
- Skills personalizables (markdown-based)
- Búsqueda web integrada

---

## 2. Estructura del Proyecto

```
Nex/
├── backend/                          # Python/FastAPI
│   ├── agent/                        # Sistema de agentes (NO integrado en routes.py)
│   ├── api/                          # Endpoints REST + SSE + Pydantic schemas
│   ├── config/                       # Cargador de config.toml
│   ├── context/                      # Sistema RAG/contexto (TODO: stubs)
│   ├── exceptions/                   # Manejo global de excepciones
│   ├── llm/                          # 5 proveedores LLM + key manager + manager
│   ├── prompts/                      # Prompts del sistema (system.txt, planner.txt, tools.txt)
│   ├── services/                     # Capa de servicios (TODO: stubs)
│   ├── storage/                      # Persistencia (settings, history, memory)
│   ├── tests/                        # Vacío
│   ├── tools/                        # 23 herramientas + framework
│   ├── utils/                        # Helpers, logger, paths, tracer
│   ├── web/                          # Interfaz web standalone (WhatsApp-style)
│   ├── main.py                       # Entry point CLI (Typer)
│   ├── config.toml                   # Config principal
│   └── requirements.txt
├── frontend/                         # Electron + TypeScript
│   ├── src/
│   │   ├── components/               # 5 clases componente
│   │   ├── renderer/                 # 7 submódulos del renderer
│   │   ├── styles/                   # 4 hojas de estilo
│   │   ├── index.html                # UI principal
│   │   ├── main.ts                   # Proceso principal Electron
│   │   ├── preload.ts                # Script preload
│   │   ├── renderer.ts               # ~1300 líneas, estado global
│   │   └── types.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tailwind.config.js
├── shared/                           # Protocolo/dataclasses compartidos
│   ├── constants.py
│   ├── version.py
│   └── protocol/
│       ├── events.py
│       ├── messages.py
│       └── tools.py
├── docs/                             # Documentación existente
├── .opencode/skills/                 # Skills custom (markdown)
├── .env                              # API keys
├── .env.example
├── nex                               # Bash launcher
└── limit-nex.sh                      # Launcher con límites de recursos
```

---

## 3. Backend — FastAPI

### 3.1 API Endpoints

El servidor corre en `http://0.0.0.0:8000` por defecto. Todos los endpoints son **no autenticados** y CORS está abierto a `*`.

#### Chat

| Método | Ruta | Propósito | Cuerpo Request | Respuesta |
|--------|------|-----------|----------------|-----------|
| `POST` | `/api/chat` | Enviar mensaje, obtener respuesta (síncrono, multi-paso) | `{message, session_id?, provider?, model?, image_data?, image_mime?}` | `{response: string}` |
| `GET` | `/api/chat/stream/{session_id}` | Streaming SSE de respuesta | — | `text/event-stream` (eventos: `text`, `tool_start`, `tool_end`, `done`) |
| `POST` | `/api/clear-history` | Limpiar historial de una sesión | `{session_id}` | `{status: "cleared"}` |

#### Historial

| Método | Ruta | Propósito | Respuesta |
|--------|------|-----------|-----------|
| `GET` | `/api/history` | Listar todas las sesiones | `{sessions: [{id, name, message_count, updated_at}]}` |
| `GET` | `/api/history/{session_id}` | Obtener mensajes de una sesión | `{messages: [{role, parts}]}` |
| `DELETE` | `/api/history/{session_id}` | Eliminar una sesión | `{status: "deleted"}` |
| `POST` | `/api/history/clear` | Eliminar TODAS las sesiones | `{status: "cleared"}` |

#### Settings

| Método | Ruta | Propósito | Cuerpo | Respuesta |
|--------|------|-----------|--------|-----------|
| `GET` | `/api/settings` | Obtener configuración actual | — | `SettingsResponse` (todos los campos) |
| `POST` | `/api/settings` | Actualizar configuración | `SettingsUpdateRequest` | `{settings: ...}` |
| `GET` | `/api/v1/settings/export` | Exportar settings como JSON | — | `{...}` (archivo JSON descargable) |
| `POST` | `/api/v1/settings/import` | Importar settings desde JSON | `{settings: {...}}` | `{status: "imported", settings: ...}` |
| `POST` | `/api/v1/settings/reset` | Resetear settings a valores por defecto | — | `{status: "reset", settings: ...}` |

Campos de configuración disponibles:

```python
provider: str             # "gemini" | "ollama" | "openai" | "anthropic" | "deepseek"
model: str                # ID del modelo
theme: str                # "dark" | "light" | "system"
language: str             # "es" | "en"
font_size: int            # 12-24
temperature: float        # 0.0 - 2.0
top_p: float              # 0.0 - 1.0
max_tokens: int           # 100-128000
send_mode: str            # "enter" | "ctrl_enter"
auto_scroll: bool
show_timestamps: bool
syntax_highlighting: bool
animations_enabled: bool
custom_api_urls: dict     # {provider: url}
timeout: int              # segundos
system_prompt: str
max_tool_calls: int       # 1-50
auto_save_interval: int   # segundos, 0 = desactivado
```

#### Modelos y Tools

| Método | Ruta | Propósito | Respuesta |
|--------|------|-----------|-----------|
| `GET` | `/api/models` | Listar modelos disponibles | `{models: [{id, name, provider}]}` |
| `GET` | `/api/tools` | Listar todas las herramientas | `{tools: [{name, description, parameters}]}` |
| `POST` | `/api/tools` | Ejecutar herramienta directamente | `{result: ...}` |

#### Workspace

| Método | Ruta | Propósito | Cuerpo |
|--------|------|-----------|--------|
| `POST` | `/api/workspace` | Establecer workspace activo | `{path: string}` |
| `POST` | `/api/upload` | Subir archivo | `multipart/form-data` |

#### Streaming SSE

El endpoint `/api/chat/stream/{session_id}` emite eventos en formato SSE:

```
evento: text       → data: "texto parcial de la respuesta"
evento: tool_start → data: {tool: "nombre", args: {...}}
evento: tool_end   → data: {tool: "nombre", result: {...}}
evento: done       → data: {}
```

No usa WebSockets — es **Server-Sent Events** unidireccional del servidor al cliente.

### 3.2 Sistema de LLM Providers

**Clase base abstracta** (`llm/provider.py`):

```python
class LLMProvider(ABC):
    async def generate(self, messages: list[dict], tools=None) -> Any
    def generate_content(self, contents: list, config=None) -> ResponseWrapper
    def generate_sync(self, message: str) -> str
    def list_models(self) -> list[str]
    def supports_tools(self) -> bool
    def supports_images(self) -> bool
```

**5 implementaciones:**

| Provider | Archivo | API | Modelo Default | Herramientas | Imágenes |
|----------|---------|-----|----------------|--------------|----------|
| **Gemini** | `gemini.py` | `google-genai SDK` | `gemini-2.5-flash` | ✅ | ✅ |
| **OpenAI** | `openai_provider.py` | HTTP directo (`urllib`) | `gpt-4o` | ✅ | ✅ |
| **Anthropic** | `anthropic_provider.py` | HTTP directo | `claude-sonnet-4-20250514` | ✅ | ❌ |
| **DeepSeek** | `deepseek_provider.py` | HTTP directo | `deepseek-chat` | ✅ | ❌ |
| **Ollama** | `ollama_provider.py` | HTTP directo | `gemma3:12b` | ✅ | ✅ |

**LLMManager** (`llm/manager.py`):
- Clase `LLMManager` con `providers: dict[str, LLMProvider]`
- `create_default_manager()` registra todos los providers
- El provider activo se selecciona por nombre desde settings

**APIKeyManager** (`llm/key_manager.py`):
- Lee `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, etc. del entorno
- `get_next_key()` — round-robin entre keys disponibles
- `blacklist_key(key)` — marca key como fallida
- `reset_blacklist()` — recupera keys fallidas

**Models** (`llm/models.py`):
- `AVAILABLE_MODELS = {model_id: {provider, family, supports_streaming, supports_tools}}`
- Catálogo estático de modelos conocidos

#### Gemini (`gemini.py`)

El provider principal. Usa el SDK `google-genai`.

```python
class GeminiProvider(LLMProvider):
    def __init__(api_key=None, model="gemini-2.5-flash")
    def list_models() -> 8 modelos
    def generate_content(contents, config) -> ResponseWrapper
    def generate(messages: list[dict] | str, tools=None) -> ResponseWrapper
    def generate_sync(message) -> str
    def supports_tools() -> True
    def supports_images() -> True
```

- `_call_with_retry()`: Reintenta con backoff ante errores HTTP 429/500/503, cambia de API key si es necesario
- Usa `types.GenerateContentConfig` para system_instruction, tools, temperature
- El bucle de herramientas en routes.py es independiente del provider

#### OpenAI (`openai_provider.py`)

Comunicación HTTP directa con `urllib.request` — **no usa el SDK de OpenAI**.

```python
class OpenAIProvider(LLMProvider):
    def __init__(api_key=None, model="gpt-4o")
    def generate(messages, tools) -> ResponseWrapper
    def generate_content(contents, config) -> ResponseWrapper
    def generate_sync(message) -> str
    def list_models() -> 8 modelos
    def supports_tools() -> True
    def supports_images() -> True  # (solo modelos vision)
```

- `_parse_response()`: Convierte respuesta OpenAI a `ResponseWrapper` con `text`, `function_calls`, `candidates`
- Endpoint: `https://api.openai.com/v1/chat/completions`
- Header: `Authorization: Bearer {api_key}`

#### Anthropic (`anthropic_provider.py`)

Comunicación HTTP directa — **no usa el SDK de Anthropic**.

```python
class AnthropicProvider(LLMProvider):
    def __init__(api_key=None, model="claude-sonnet-4-20250514")
    def generate(messages, tools) -> ResponseWrapper
    def generate_content(contents, config) -> ResponseWrapper
    def generate_sync(message) -> str
    def list_models() -> 6 modelos
    def supports_tools() -> True
```

- `_parse_response()`: Convierte bloques `tool_use` de Anthropic a `function_calls`
- Tool conversion: de formato genérico `function_declarations` a formato Anthropic `{name, description, input_schema}`
- Endpoint: `https://api.anthropic.com/v1/messages`
- Headers: `x-api-key`, `anthropic-version: 2023-06-01`

#### DeepSeek (`deepseek_provider.py`)

Comunicación HTTP directa.

```python
class DeepSeekProvider(LLMProvider):
    def __init__(api_key=None, model="deepseek-chat")
    def generate(messages, tools) -> ResponseWrapper
    def generate_content(contents, config) -> ResponseWrapper
    def generate_sync(message) -> str
    def list_models() -> 3 modelos
    def supports_tools() -> True
```

- API compatible con OpenAI (`/v1/chat/completions`)
- Endpoint: `https://api.deepseek.com/v1/chat/completions`

#### Ollama (`ollama_provider.py`)

Comunicación HTTP directa con servidor Ollama local.

```python
class OllamaProvider(LLMProvider):
    def __init__(model="gemma3:12b", base_url="http://localhost:11434")
    def generate(messages, tools) -> ResponseWrapper
    def generate_content(contents, config) -> ResponseWrapper
    def generate_sync(message) -> str
    def list_models() -> detect_ollama_models() (subprocess)
    def supports_tools() -> True
    def supports_images() -> True
```

Métodos internos de conversión:

| Método | Propósito |
|--------|-----------|
| `_history_to_messages(contents, system_instruction)` | Convierte `list[types.Content]` a mensajes Ollama `[{role, content, tool_calls?, images?}]` |
| `_tools_to_ollama(tools)` | Convierte `function_declarations` (dict o SDK object) a formato Ollama |
| `_schema_to_dict(schema)` | Convierte `Schema` object (Gemini SDK) o `dict` a JSON Schema plano |
| `_parse_response(result)` | Envuelve respuesta Ollama en `ResponseWrapper` con `text`, `function_calls`, `candidates` |
| `_call_ollama(body)` | Ejecuta `POST /api/chat` con `urllib` |

Flujo de `generate_content()`:
1. Convierte `contents` (Google genai `Content` objects) → messages dict
2. Si el modelo rechaza tools (HTTP 400), reintenta sin tools
3. Valida que messages no estén vacíos
4. Usa `settings.temperature` como fallback

### 3.3 Sistema de Tools

**Arquitectura:**

```
Tool (clase abstracta)
  ├── name: str
  ├── description: str
  ├── parameters: dict (JSON Schema)
  └── execute(**kwargs) -> Any

ToolRegistry
  ├── register(tool)
  ├── get(name) -> Tool
  ├── get_all_tools_metadata() -> list[dict] (function_declarations)
  └── create_default_registry() -> ToolRegistry (factory)
```

**23 herramientas registradas:**

#### Sistema de Archivos (`tools/filesystem.py`) — 11 tools

| Tool | Descripción |
|------|-------------|
| `read_file` | Lee contenido de archivo (con límite de tamaño) |
| `write_file` | Escribe/crea archivo |
| `edit_file` | Edición por rango de líneas |
| `delete_file` | Elimina archivo |
| `list_directory` | Lista contenido de directorio |
| `create_directory` | Crea directorio (recursivo) |
| `move_file` | Mueve o renombra archivo/directorio |
| `copy_file` | Copia archivo o directorio |
| `search_files` | Búsqueda por patrón glob |
| `get_file_info` | Metadatos (tamaño, modified, type) |
| `read_multiple_files` | Lectura batch de múltiples archivos |

#### Terminal (`tools/terminal.py`) — 1 tool

- `execute_command`: Ejecuta comando shell con timeout
- Restricciones: `allowed_commands` y `blocked_commands` desde config.toml

#### Git (`tools/git.py`) — 1 tool

- `run_git_command`: Ejecuta comandos git como subprocess
- Detecta automáticamente `--git-dir` y `--work-tree`

#### Web (`tools/web.py`) — 2 tools

- `web_search`: Búsqueda web via HTTP request asíncrono
- `web_fetch`: Fetch de URL, convierte a markdown

#### Análisis de Código (`tools/code_analysis.py`) — 1 tool

- `analyze_code`: Análisis AST/estático multi-lenguaje (Python, JavaScript, TypeScript, Java, etc.)

#### Refactorización (`tools/refactoring.py`) — 1 tool

- `refactor_code`: Transformaciones AST (rename, extract function, inline variable, etc.)

#### Imagen (`tools/image_tool.py`) — 2 tools

- `analyze_image`: Metadatos, formato, dimensiones, histograma de color
- `edit_image`: Redimensionar, recortar, convertir, filtrar, rotar

#### MCP (`tools/mcp.py`) — 1 tool

- `mcp_tool`: Lanza servidor MCP externo via subprocess, comunicación JSON-RPC 2.0 por stdin/stdout

#### LSP (`tools/lsp.py`) — 1 tool

- `lsp_tool`: Análisis de código vía AST (Python) y regex (TypeScript). Acciones:
  - `references` — encontrar referencias
  - `goto_def` — ir a definición
  - `hover` — información de elemento
  - `diagnostics` — errores/sugerencias
  - `complete` — autocompletado
  - `rename` — renombrar símbolo

#### Skills (`tools/skills.py`) — 1 tool

- `execute_skill`: Descubre y ejecuta skills markdown desde `.opencode/skills/`. Parsea frontmatter YAML, ejecuta comandos bash listados.

#### Sesiones (`tools/sessions.py`) — 1 tool

- `manage_session`: Recordar/enfocar/olvidar temas de contexto a través de la conversación. Acciones: `remember`, `focus`, `forget`, `list`.

#### Validación de Seguridad (`tools/errors.py`)

- `validate_path_safety(path, workspace_root)`: Previene path traversal
- `ToolError`: Excepción base para errores de herramientas
- Workspace root se pasa desde routes.py como `tool_args["workspace_root"]`

### 3.4 Sistema de Persistencia

#### Settings (`storage/settings.py`)

- Archivo: `.nex_settings.json` en el directorio del backend
- `SettingsManager`: Singleton que lee/escribe settings
  - `get(key)` / `get_all()` / `set(key, value)`
  - `load_settings()` / `save_settings()`
  - `get_api_key(provider)`: Lee API keys desde `.env` con `python-dotenv`
  - `export_settings()`: Exporta todo a dict (omite API keys y workspace)
  - `import_settings(data)`: Importa desde dict
  - `reset_settings()`: Restaura valores por defecto
- Carga automática al importar: `settings = SettingsManager()`

#### Memoria/Historial (`storage/memory.py`)

- `HistoryManager`: CRUD completo para historial de chat
- Archivos: `.nex_history_{session_id}.json`
  - Almacena `list[Content]` con partes serializadas (text, function_call, function_response, inline_data)
  - `Content` → dict: `{role, parts: [{text?, function_call?, function_response?, inline_data?}]}`
  - Las partes `function_call` guardan `name` + `args` como JSON
  - Las partes `function_response` guardan `name` + `response` como JSON
  - Las partes `inline_data` guardan `mime_type` + `data` (base64)
- `save(content, session_id)`: Agrega un Content al historial
- `load(session_id)`: Carga lista completa de Content
- `list_sessions()`: Lista sesiones con metadatos
- `delete(session_id)`: Elimina archivo de sesión
- `clear_all()`: Elimina todos los archivos de historial
- `ConversationSplitter`: Divide conversación cuando excede `max_messages` (por defecto 50)
- `trim_messages(messages, max_messages)`: Trunca al inicio de la conversación + últimos N mensajes

### 3.5 Configuración

**config.toml** — Archivo de configuración principal del backend:

```toml
[server]
host = "0.0.0.0"
port = 8000

[defaults]
model = "gemini-2.5-flash"
session_id = "default"
system_prompt_path = "prompts/system.txt"

[tools.terminal]
allowed_commands = ["ls", "cat", "pwd", ...]
blocked_commands = ["rm -rf /", ...]

[tools]
workspace_root = "/home/netsent/WorkSpace"

[limits]
max_file_size = 10485760
max_upload_size = 52428800
```

### 3.6 CLI (Typer)

`backend/main.py` — Interfaz de línea de comandos:

- Comando principal: `nex` (bash launcher que activa venv y ejecuta el CLI)
- `python backend/main.py "mensaje"` — Consulta directa (máximo 10 iteraciones)
- Sin modo interactivo o REPL

El flujo CLI replica el mismo bucle que routes.py: carga historial, crea `GenerateContentConfig`, ejecuta hasta 10 iteraciones modelo→herramienta, guarda historial.

### 3.7 Sistema de Agentes (no integrado)

El paquete `backend/agent/` contiene una implementación de agente autónomo **que no está conectada a routes.py ni a ningún endpoint**. El chat loop de routes.py tiene su propio bucle inline.

```python
Agent(orchestrator)
  ├── Planner(llm)           # Crea plan paso a paso
  ├── Executor(llm, tools)   # Ejecuta pasos individuales
  ├── AgentMemory()          # Almacena observaciones con presupuesto de tokens
  └── Observation            # Dataclass: agent_id, step, action, result, summary
```

Estados: `PLANNING → EXECUTING → WAITING → COMPLETED | FAILED`

### 3.8 Stubs y Código Muerto

| Módulo | Estado | Líneas | Notas |
|--------|--------|--------|-------|
| `context/cache.py` | STUB | 6 | `get()` retorna None |
| `context/embeddings.py` | STUB | 3 | `embed()` retorna `[]` |
| `context/indexer.py` | STUB | 3 | `build_index()` retorna `{}` |
| `context/parser.py` | STUB | 3 | `parse()` retorna `{}` |
| `context/search.py` | STUB | 3 | `semantic()` retorna `[]` |
| `context/workspace.py` | PARCIAL | 10 | Solo constructor + resolve |
| `services/chat.py` | STUB | 12 | Dict en memoria, sin persistencia |
| `services/config.py` | STUB | 6 | Wrapper de tomli.load |
| `services/workspace.py` | STUB | 6 | Almacena path actual |
| `storage/history.py` | STUB | 6 | `save()` es pass |
| `storage/cache.py` | STUB | 3 | Solo constructor |
| `agent/*` | MUERTO | ~200 | No importado por routes.py |
| `backend/tests/` | VACÍO | 0 | Solo `__init__.py` |
| `README.md` | VACÍO | 0 | Archivo vacío |

---

## 4. Frontend — Electron/TypeScript

### 4.1 Arquitectura

```
[ Electron Main Process (main.ts) ]
         ↓ preload.ts (contextBridge)
[ Renderer Process (renderer.ts + components) ]
         ↓ HTTP (fetch)
[ FastAPI Backend ]
```

- **Electron**: `main.ts` crea `BrowserWindow` (1200×800) con `contextIsolation: true`, `nodeIntegration: false`
- **Preload**: Expone `electronAPI` vía `contextBridge`: `getAppPath`, `openExternal`, `showSaveDialog`, `platform`
- **Renderer**: TypeScript vanilla, sin framework (no React/Vue/Svelte)
- **Estilos**: Tailwind CSS + glassmorphism

### 4.2 Componentes

Todos en `frontend/src/components/`:

| Componente | Archivo | Propósito |
|-----------|---------|-----------|
| `ChatBox` | `ChatBox.ts` | Contenedor del listado de mensajes + input |
| `Input` | `Input.ts` | Textarea con auto-resize, Enter/Shift+Enter para enviar |
| `Message` | `Message.ts` | Renderiza burbuja de mensaje individual con markdown |
| `Modal` | `Modal.ts` | Modal genérico (overlay + contenido) |
| `Sidebar` | `Sidebar.ts` | Sidebar con lista de sesiones |

### 4.3 Renderizador

`renderer.ts` (~1300 líneas) — Contiene todo el estado global y lógica de UI:

**Estado global:**

```typescript
currentSessionId: string | null
sessions: Session[]
conversationHistory: ConversationMessage[]
state: 'idle' | 'loading' | 'streaming' | 'error'
settings: Settings
currentAssistantMessage: string
abortController: AbortController | null
```

**Módulos en `frontend/src/renderer/`:**

| Módulo | Archivo | Propósito |
|--------|---------|-----------|
| `api` | `api.ts` | Wrappers `fetch()` para todos los endpoints del backend |
| `app` | `app.ts` | Inicialización y ciclo de vida de la app |
| `chat` | `chat.ts` | Estado de chat, envío de mensajes, gestión de streams |
| `history` | `history.ts` | Carga y gestión de historial de sesiones |
| `plasma-core` | `plasma-core.ts` | Animación 3D de partículas en canvas (fondo) |
| `shortcuts` | `shortcuts.ts` | Gestor de atajos de teclado (Ctrl+K spotlight, etc.) |
| `ui` | `ui.ts` | Estado de UI, tema, settings modal |
| `welcomeMessages` | `welcomeMessages.ts` | Mensajes de bienvenida predefinidos |

**Streaming SSE:**

El renderer se conecta a `/api/chat/stream/{session_id}` con `EventSource` y procesa 5 tipos de evento:

| Evento | Acción |
|--------|--------|
| `text` | Acumula chunk en `currentAssistantMessage`, renderiza en vivo |
| `tool_start` | Muestra indicador visual de tool ejecutándose |
| `tool_end` | Muestra resultado de tool |
| `done` | Finaliza streaming, guarda mensaje completo, limpia estado |
| `error` | Muestra error al usuario |

### 4.4 Estilos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `main.css` | ~1150 | Sistema de diseño glassmorphism con propiedades CSS custom |
| `chat.css` | ~100 | Estilos legacy de burbujas de chat |
| `sidebar.css` | ~80 | Estilos legacy del sidebar |
| `spotlight.css` | ~60 | Estilos del modal de búsqueda (Ctrl+K) |

`main.css` implementa:
- Tema oscuro/claro/gruvbox con variables CSS
- Efecto glass (blur, transparencia)
- Animaciones de entrada/salida
- Responsive básico
- Scrollbar personalizada

---

## 5. Shared — Protocolo Compartido

El paquete `shared/` define tipos y protocolos compartidos entre backend y frontend.

**`shared/protocol/events.py`:**
```python
class EventType(Enum):
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"

@dataclass
class StreamEvent:
    type: EventType
    data: dict
```

**`shared/protocol/messages.py`:**
```python
@dataclass
class Message:
    role: str                         # "user" | "assistant" | "tool"
    content: str | None
    tool_calls: list[dict] | None
    tool_call_id: str | None

@dataclass
class Conversation:
    messages: list[Message]
    system_prompt: str | None
    def to_openai() -> list[dict]     # Convierte a formato OpenAI API
```

**`shared/protocol/tools.py`:**
```python
@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict

ToolSpecList = list[ToolSpec]
```

**`shared/constants.py`:**
```python
ERROR_CODES = {"RATE_LIMIT": 429, "AUTH_ERROR": 401, ...}
RATE_LIMIT = 30  # requests/min
RETRY_MAX = 3
RETRY_DELAY = 1.0
TOKEN_LIMITS = {"gemini-2.5-flash": 1048576, ...}
```

**`shared/version.py`:**
```python
VERSION = "0.1.0-dev"
```

---

## 6. Flujo de Datos

### Chat normal (sin tools)

```
Usuario escribe mensaje
  → Frontend: POST /api/chat {message, session_id}
  → Backend: routes.py
      1. Cargar historial previo (storage/memory.py)
      2. Obtener provider desde settings
      3. Construir GenerateContentConfig (system_instruction, tools, temperature)
      4. provider.generate_content(contents, config)
      5. Si respuesta no tiene function_calls → guardar historial → devolver texto
      6. Si tiene function_calls → ejecutar tools → loop hasta 10 iteraciones
  → Frontend: Muestra respuesta renderizada con Markdown
```

### Streaming

```
Usuario escribe mensaje
  → Frontend: POST /api/chat (crea/obtiene session_id)
  → Frontend: EventSource → GET /api/chat/stream/{session_id}
  → Backend: event_stream() generator
      1. Mismo loop que chat normal pero con `yield`
      2. Eventos: text (chunks), tool_start, tool_end, done
  → Frontend: Acumula chunks, renderiza en vivo
```

### Tool execution

```
1. LLM retorna function_call(s) en la respuesta
2. routes.py itera sobre response.function_calls
3. Para cada call:
   a. Obtener tool del registry: registry.get(tool_name)
   b. Ejecutar: tool.execute(**kwargs)
   c. Agregar resultado como Content(role="user", parts=[function_response])
4. provider.generate_content() con historial actualizado
5. Repetir hasta 10 iteraciones o hasta que no haya más function_calls
```

---

## 7. Seguridad

### Riesgos actuales
- **CORS abierto** `allow_origins=["*"]` — cualquier origen puede llamar a la API
- **Sin autenticación** en ningún endpoint
- **API keys en `.env`** — actualmente pobladas con keys visibles (verificar que `.env` esté en `.gitignore`)
- **`validate_path_safety()`** protege contra path traversal limitando operaciones al workspace root
- **Terminal tool** tiene listas blancas/negras de comandos en config.toml

### Recomendaciones
- Agregar autenticación (API key mínimamente)
- Restringir CORS a orígenes conocidos
- Mover `.env` con keys reales fuera del repo o encriptarlas
- Rate limiting en endpoints de chat

---

## 8. Despliegue y Desarrollo

### Requisitos

- Python 3.11+
- Node.js 18+
- Ollama (opcional, para provider local)
- API keys: Gemini, OpenAI, Anthropic, DeepSeek (según proveedores a usar)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configurar API keys
python -m api.routes   # Iniciar servidor (o uvicorn)
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # Desarrollo
npm run build   # Producción
```

### CLI

```bash
./nex "tu mensaje aquí"
```

### Variables de Entorno (`.env`)

```
GEMINI_API_KEY=...
GEMINI_API_KEY_2=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
DEEPSEEK_API_KEY=...
```

---

*Documentación generada el 2026-07-04. Versión del proyecto: 0.1.0-dev.*
