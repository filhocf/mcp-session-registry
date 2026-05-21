# AGENTS.md — mcp-session-registry

## Project Overview

Lightweight MCP server providing multi-session awareness. Sessions register presence, claim files, and query conflicts. SQLite storage, Streamable HTTP transport, Python.

## Architecture

```
src/mcp_session_registry/
├── __init__.py          # Version
├── server.py            # MCP server setup + main() entrypoint
├── db.py                # SQLite schema, connection, queries
├── models.py            # Pydantic models (Session, Claim)
└── reaper.py            # Background task: expire dead sessions
tests/
├── test_db.py           # Unit tests for database layer
├── test_server.py       # Integration tests for MCP tools
└── conftest.py          # Fixtures (temp DB, test client)
```

## Data Flow

```
CLI Hook (AgentSpawn) → session_register → SQLite → session_list ← Other sessions
                                                  → session_conflicts ← Other sessions
CLI Hook (Stop) → session_end → SQLite (delete)
Background reaper → every 60s → delete sessions with heartbeat > 5min ago
```

## Key Conventions

- **Config**: env vars only (`MSR_PORT=3203`, `MSR_DB_PATH=...`, `MCP_TRANSPORT=streamable-http`)
- **Errors**: raise McpError with human-readable message
- **IDs**: UUID4 for session_id, string paths for claims
- **Timestamps**: UTC ISO 8601, stored as TEXT in SQLite
- **Logging**: stdlib logging, level via `MSR_LOG_LEVEL`
- **No external deps** beyond mcp SDK + uvicorn

## Adding a New Tool

1. Define Pydantic input model in `models.py`
2. Add SQL query in `db.py`
3. Register tool in `server.py` with `@mcp.tool()`
4. Add test in `tests/test_server.py`
5. Update PRD.md tool table

## Tests

```bash
uv run pytest                    # all tests
uv run pytest -x                 # stop on first failure
uv run pytest tests/test_db.py   # just DB layer
```

## Running

```bash
# Development
MSR_PORT=3203 uv run mcp-session-registry

# Production (systemd)
systemctl --user start session-registry.service
```
