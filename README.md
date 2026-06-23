# mcp-session-registry

[![CI](https://github.com/filhocf/mcp-session-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/filhocf/mcp-session-registry/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Lightweight MCP server for multi-session awareness — lets AI agents know who else is active on the same machine.

## Why

When you run multiple AI CLI sessions (Kiro, Claude Code, Gemini CLI) on the same machine, they are blind to each other. This causes:

- **File conflicts** — two sessions editing the same file
- **Duplicated work** — agents picking up the same task
- **Wasted context** — no way to know what another session is doing

**mcp-session-registry** solves this with a shared presence layer:

- Sessions register on spawn, declare a theme, and heartbeat every 2-3 minutes
- Sessions claim files/resources — other sessions see the claim before touching them
- Stale sessions (no heartbeat >5min) are automatically reaped
- Everything persists in SQLite — survives individual session crashes

## Quick Start

```bash
# Run directly
uvx mcp-session-registry

# Or install as a tool
uv tool install mcp-session-registry

# Configure port (default: 8000)
MSR_PORT=3203 mcp-session-registry
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `session_register` | Register a new session. Returns `session_id` for subsequent calls. |
| `session_list` | List all active sessions on this machine. |
| `session_heartbeat` | Send heartbeat to keep session alive (call every 2-3 min). |
| `session_end` | Gracefully end a session and release all its claims. |
| `session_claim` | Claim a resource (file, branch, work item). Advisory lock. |
| `session_release` | Release a previously claimed resource. |
| `session_conflicts` | Check if resources are claimed by another active session. |

## How It Works

```
Session A registers → gets session_id
Session A claims "src/main.py"
Session B calls session_conflicts(["src/main.py"])
  → returns: claimed by Session A (pid 1234, theme "refactor auth")
Session B picks a different file
```

Sessions that stop sending heartbeats are reaped after 5 minutes — their claims are released automatically.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MSR_PORT` | `8000` | HTTP port for StreamableHTTP transport |
| `MSR_DB_PATH` | `~/.local/share/session-registry/sessions.db` | SQLite database path |

## Integration with Kiro CLI

Add to your `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "session-registry": {
      "url": "http://localhost:3203/mcp",
      "autoApprove": ["session_register", "session_list", "session_heartbeat", "session_end", "session_claim", "session_release", "session_conflicts"]
    }
  }
}
```

Run as a systemd user service:

```bash
# ~/.config/systemd/user/session-registry.service
[Unit]
Description=MCP Session Registry

[Service]
ExecStart=%h/.local/bin/mcp-session-registry
Environment=MSR_PORT=3203
Restart=on-failure

[Install]
WantedBy=default.target
```

## Health Check

```bash
curl http://localhost:3203/health
# {"status": "healthy", "version": "0.2.0", "uptime_seconds": 3600}
```

## Development

```bash
git clone https://github.com/filhocf/mcp-session-registry
cd mcp-session-registry
uv sync
uv run pytest tests/ -v
uv tool run ruff check src/ tests/
```

## License

Apache-2.0
