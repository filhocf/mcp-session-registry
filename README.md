# mcp-session-registry

MCP server for multi-session awareness and coordination.

## Problem

Multiple AI CLI sessions on the same machine are blind to each other — causing file conflicts, duplicated work, and wasted context.

## Solution

A shared presence layer where sessions register, declare intent, claim files, and detect conflicts.

## Quick Start

```bash
# Install
uv tool install mcp-session-registry

# Run
MSR_PORT=3203 mcp-session-registry
```

## Tools

| Tool | Description |
|------|-------------|
| `session_register` | Register a new session |
| `session_list` | List active sessions |
| `session_heartbeat` | Keep session alive |
| `session_end` | End a session |
| `session_claim` | Claim a file/resource |
| `session_release` | Release a claim |
| `session_conflicts` | Check for conflicts with other sessions |

## Integration

### Kiro CLI Hooks

```json
{
  "hooks": {
    "AgentSpawn": [{"command": "curl -s -X POST http://localhost:3203/register ..."}],
    "Stop": [{"command": "curl -s -X POST http://localhost:3203/end ..."}]
  }
}
```

## License

Apache-2.0
