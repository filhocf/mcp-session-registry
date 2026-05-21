# PRD — mcp-session-registry

## Problem

Multiple AI CLI sessions (Kiro CLI, Gemini CLI, Claude Code) running on the same machine are blind to each other. They don't know:
- That other sessions exist
- What each session is working on
- Which files are being modified by another session

This causes: file conflicts, duplicated work, contradictory decisions, and wasted context.

## Solution

A lightweight MCP server that provides a **shared presence layer** for all CLI sessions on a machine. Any session can register itself, declare what it's working on, claim files, and query what others are doing.

## Personas

- **Developer** running 2-4 Kiro CLI sessions in parallel on different themes
- **AI agent** (via hooks) that auto-registers on spawn and cleans up on stop
- **Cross-CLI user** running Kiro + Gemini + Claude Code on the same project

## Core Concepts

### Session
A running CLI instance. Has: id, cli type, hostname, PID, theme/description, status, timestamps.

### Claim
A file or resource that a session declares ownership of. Advisory (not enforced), but visible to all.

### Heartbeat
Periodic signal that a session is still alive. Sessions without heartbeat for >5 minutes are considered dead and auto-cleaned.

## Tools (MCP)

| Tool | Purpose |
|------|---------|
| `session_register` | Register a new session (returns session_id) |
| `session_list` | List all active sessions |
| `session_heartbeat` | Keep session alive |
| `session_end` | Gracefully end a session |
| `session_claim` | Claim a file/resource |
| `session_release` | Release a claim |
| `session_conflicts` | Check if current work conflicts with another session |

## Non-Goals (v0.1)

- Cross-machine coordination (future: shared DB via network)
- Enforced file locking (advisory only)
- Task assignment between sessions (use task-orchestrator for that)
- Memory sharing (use memory-service for that)

## Technical Decisions

- **Storage**: SQLite (single file, zero config, concurrent-safe with WAL)
- **Transport**: Streamable HTTP (same as memory-service, task-orchestrator)
- **Language**: Python (consistent with our stack)
- **Framework**: MCP SDK (mcp>=1.9.0)
- **Port**: 3203 (next after task-orchestrator 3201, memory-service 3202)
- **DB location**: `~/.local/share/mcp-session-registry/sessions.db`

## Success Criteria

1. Session 1 registers → Session 2 can see it via `session_list`
2. Session 1 claims `~/git/mir/api/` → Session 2 gets warning via `session_conflicts`
3. Session 1 dies (kill -9) → after 5min, auto-cleaned from registry
4. Works with Kiro CLI hooks (AgentSpawn → register, Stop → end)
