# Changelog

All notable changes documented here. Format: [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-06-23

### Added
- `/health` endpoint via `@mcp.custom_route` (GET, returns status/version/uptime)

### Fixed
- Lint E402: moved `import time` to top of module

## [0.1.1] - 2026-06-19

### Added
- Version bump for /health endpoint (never committed - fixed in 0.2.0)

## [0.1.0] - 2026-05-21

### Added
- Initial release: session_register, session_list, session_heartbeat, session_end, session_claim, session_release, session_conflicts
- SQLite storage with heartbeat-based liveness detection
- Stale session reaping (>5min without heartbeat)
- StreamableHTTP transport on configurable port (MSR_PORT)
