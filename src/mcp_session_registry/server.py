"""MCP server for session registry."""

import asyncio
import logging
import os
import socket
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from .db import SessionDB
from .models import Claim, Session

logger = logging.getLogger(__name__)

mcp = FastMCP("session-registry")

db: SessionDB | None = None


def get_db() -> SessionDB:
    global db
    if db is None:
        db = SessionDB()
    return db


@mcp.tool()
def session_register(cli: str, pid: int, theme: str = "", hostname: str = "") -> dict:
    """Register a new session. Returns session_id for use in heartbeat/end/claim calls."""
    session = Session(
        cli=cli,
        hostname=hostname or socket.gethostname(),
        pid=pid,
        theme=theme,
    )
    get_db().register(session)
    return {"session_id": session.id, "registered_at": session.started_at.isoformat()}


@mcp.tool()
def session_list() -> dict:
    """List all active sessions on this machine."""
    sessions = get_db().list_active()
    return {"sessions": sessions, "count": len(sessions)}


@mcp.tool()
def session_heartbeat(session_id: str) -> dict:
    """Send heartbeat to keep session alive. Call every 2-3 minutes."""
    ok = get_db().heartbeat(session_id)
    if not ok:
        return {"success": False, "error": "Session not found"}
    return {"success": True, "heartbeat_at": datetime.now(timezone.utc).isoformat()}


@mcp.tool()
def session_end(session_id: str) -> dict:
    """Gracefully end a session and release all its claims."""
    ok = get_db().end(session_id)
    return {"success": ok}


@mcp.tool()
def session_claim(session_id: str, resource: str, resource_type: str = "file") -> dict:
    """Claim a resource (file, branch, item). Advisory — visible to other sessions."""
    claim = Claim(session_id=session_id, resource=resource, resource_type=resource_type)
    get_db().claim(claim)
    return {"claim_id": claim.id, "resource": resource}


@mcp.tool()
def session_release(session_id: str, resource: str) -> dict:
    """Release a previously claimed resource."""
    ok = get_db().release(session_id, resource)
    return {"success": ok}


@mcp.tool()
def session_conflicts(session_id: str, resources: list[str]) -> dict:
    """Check if any of the given resources are claimed by another active session."""
    conflicts = get_db().get_conflicts(session_id, resources)
    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": [c.model_dump() for c in conflicts],
    }


async def _reaper_loop():
    """Background task to clean up dead sessions every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        try:
            reaped = get_db().reap_dead_sessions()
            if reaped:
                logger.info(f"Reaper: cleaned {reaped} dead sessions")
        except Exception as e:
            logger.error(f"Reaper error: {e}")


def main():
    """Entrypoint for the MCP server."""
    port = int(os.environ.get("MSR_PORT", "3203"))
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    log_level = os.environ.get("MSR_LOG_LEVEL", "INFO")

    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    # Initialize DB eagerly
    get_db()
    logger.info(f"Session Registry starting on port {port} (transport={transport})")

    if transport == "streamable-http":
        mcp.settings.port = port
        mcp.settings.streamable_http_path = "/mcp"

        # Start reaper as background task
        import threading

        def run_reaper():
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_reaper_loop())

        reaper_thread = threading.Thread(target=run_reaper, daemon=True)
        reaper_thread.start()

        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
