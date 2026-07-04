# Architecture

Nex follows a layered architecture:

```
Frontend (Electron/TS)  ──HTTP──▶  Backend (Python/FastAPI)
                                        │
                                        ├── api/        — REST endpoints
                                        ├── agent/      — Cognitive loop
                                        ├── llm/        — LLM abstraction
                                        ├── tools/      — System primitives
                                        ├── context/    — Code analysis
                                        └── storage/    — Persistence
```

## Principles
- Shared contracts in `shared/` are the single source of truth
- No circular dependencies between backend packages
- Frontend communicates exclusively over HTTP
