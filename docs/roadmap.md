# Roadmap

## v0.1.0 — Foundation
- [x] Project structure
- [ ] Basic chat API
- [ ] LLM integration (Gemini)
- [ ] File read/write tools
- [ ] Terminal execution

## v0.2.0 — Agent Loop
- [ ] Planning and decomposition
- [ ] Tool registry and auto-schema
- [ ] Conversation memory
- [ ] Streaming responses

## v0.3.0 — Frontend
- [ ] Electron shell
- [ ] Chat UI
- [ ] Sidebar with history
- [ ] Keyboard shortcuts

## v0.4.0 — Security Toolkit
- [x] `dns_lookup` — DNS records (A/AAAA/MX/NS/TXT/CNAME)
- [x] `whois_lookup` — RDAP/WHOIS registration data
- [x] `subdomain_enum` — passive enum via crt.sh (certificate transparency)
- [x] `http_fingerprint` — headers, server, technology stack
- [x] `tls_probe` — TLS certificate inspection
- [x] `hash_identify` — hash type identification (forensics)
- [x] `file_metadata` — magic bytes, hashes, timestamps, strings (forensics)
- [x] `port_scan` — TCP connect scan (scoped to loopback/NEX_SCAN_ALLOWLIST)
- [x] Tests + docs (see `docs/recon.md`)

## v0.5.0 — Nex Watch + Explicador
- [x] Secret scanner (API keys, tokens, private keys; patrones + entropía)
- [x] WatchService: borrados masivos, secretos nuevos, archivos sensibles
- [x] Alerta de comandos peligrosos bloqueados (hooks en `run_command`)
- [x] Alertas persistidas + endpoints API (`/api/v1/alerts`, `/watch/status`)
- [x] CLI `nex watch`
- [x] Modo explicador (el agente explica por qué usa cada tool)
- [x] Todo configurable desde ajustes (vigilante, umbrales, explain, scan scope)
- [x] UI: campana de alertas + panel Security en configuración
- [x] Tests + docs (see `docs/watch.md`)

## v0.6.0 — Orb + Cleanup (Current)
- [x] **Orb module**: Unified tool orchestrator (`backend/orb.py`)
- [x] **Tool registry cleanup**: Removed RefactorTool, MCPTool from default registry
- [x] **Enhanced documentation**: README, roadmap, api.md updates
- [ ] API endpoints for orb integration
- [ ] Frontend orb component
- [ ] Skill system integration
