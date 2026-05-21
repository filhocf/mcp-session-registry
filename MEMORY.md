# MEMORY.md — mcp-session-registry

## Estado Atual

- **Versão**: 0.1.0 (em desenvolvimento)
- **Criado**: 21/mai/2026
- **Motivação**: 4 sessões Kiro CLI cegas entre si na DNBSCDC289

## Decisões

- Porta 3203 (após task-orch 3201, memory 3202)
- SQLite WAL mode, DB em ~/.local/share/mcp-session-registry/sessions.db
- Heartbeat timeout: 5 minutos
- Claims são advisory (não enforced)
- Streamable HTTP transport (consistente com outros MCPs)

## Próximo

- Implementar schema + models
- Implementar server com 7 tools
- Testes
- Integrar via hooks Kiro CLI
