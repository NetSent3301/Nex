# API Reference

Endpoints expuestos por `backend/api/routes/` (entry point: `api.routes:app`, puerto 8765).

## UI y sistema

- `GET /` — UI web embebida (`backend/web/index.html`)
- `GET /api/v1/health` — `{"status": "healthy", "agent": "Nex"}`
- `GET /api/v1/metrics` — uso de RAM/CPU
- `GET /api/v1/ollama/models` — modelos Ollama detectados + si el daemon corre
- `POST /api/v1/upload/image` — sube una imagen y devuelve base64 (`multipart/form-data`, campo `file`)
- `POST /api/v1/clear-history` — borra los historiales de `backend/data/*.json`

## Chat

- `POST /api/chat` — chat autónomo multi-paso con tools
  - Request: `{message, session_id, image_data?, image_mime?, provider?, model?, language?}`
  - Response: `{response}`
- `POST /api/chat/stream` — streaming SSE con eventos `text`, `tool_start`, `tool_end`, `done`

## Workspace config

- `GET /api/v1/workspace` — `{path}` del workspace activo
- `GET /api/v1/settings` — ajustes completos (`SettingsResponse`)
- `POST /api/v1/settings` — actualiza ajustes (`SettingsUpdateRequest`; `api_keys` se guarda en `.env`)
- `GET /api/v1/settings/export` — `{provider, model, temperature, ...}`
- `POST /api/v1/settings/import` — importación sanedada de ajustes
- `POST /api/v1/settings/reset` — restablece `backend/.nex_settings.json`

## Nex Watch

- `GET /api/v1/alerts?limit=50` — `{alerts: [{kind, message, details, timestamp}]}`
- `POST /api/v1/alerts/clear` — `{cleared}`
- `GET /api/v1/watch/status` — `{running, workspace, interval, alerts, commands}`