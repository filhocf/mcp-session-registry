"""SQLite database layer for session registry."""

import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .models import Session, Claim, Conflict, SessionStatus

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "mcp-session-registry" / "sessions.db"
HEARTBEAT_TIMEOUT_SECONDS = 300  # 5 minutes


class SessionDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(
            __import__("os").environ.get("MSR_DB_PATH", str(DEFAULT_DB_PATH))
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    cli TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    theme TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    started_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    resource_type TEXT DEFAULT 'file',
                    claimed_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_claims_resource ON claims(resource);
                CREATE INDEX IF NOT EXISTS idx_claims_session ON claims(session_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
            """)

    def register(self, session: Session) -> Session:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, cli, hostname, pid, theme, status, started_at, heartbeat_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session.id, session.cli, session.hostname, session.pid, session.theme, session.status.value, session.started_at.isoformat(), session.heartbeat_at.isoformat()),
            )
        logger.info(f"Session registered: {session.id} ({session.cli}, pid={session.pid}, theme={session.theme!r})")
        return session

    def list_active(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE status != 'dead' ORDER BY started_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def heartbeat(self, session_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE sessions SET heartbeat_at = ?, status = 'active' WHERE id = ?",
                (now, session_id),
            )
        return cur.rowcount > 0

    def end(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM claims WHERE session_id = ?", (session_id,))
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        logger.info(f"Session ended: {session_id}")
        return cur.rowcount > 0

    def claim(self, claim: Claim) -> Claim:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO claims (id, session_id, resource, resource_type, claimed_at) VALUES (?, ?, ?, ?, ?)",
                (claim.id, claim.session_id, claim.resource, claim.resource_type, claim.claimed_at.isoformat()),
            )
        logger.info(f"Claim: session={claim.session_id} resource={claim.resource}")
        return claim

    def release(self, session_id: str, resource: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM claims WHERE session_id = ? AND resource = ?",
                (session_id, resource),
            )
        return cur.rowcount > 0

    def get_conflicts(self, session_id: str, resources: list[str]) -> list[Conflict]:
        if not resources:
            return []
        placeholders = ",".join("?" * len(resources))
        with self._get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT c.resource, c.resource_type, c.claimed_at, c.session_id,
                       s.cli, s.theme
                FROM claims c
                JOIN sessions s ON c.session_id = s.id
                WHERE c.resource IN ({placeholders})
                  AND c.session_id != ?
                  AND s.status != 'dead'
                """,
                (*resources, session_id),
            ).fetchall()
        return [
            Conflict(
                resource=r["resource"],
                resource_type=r["resource_type"],
                claimed_by_session=r["session_id"],
                claimed_by_cli=r["cli"],
                claimed_by_theme=r["theme"],
                claimed_at=datetime.fromisoformat(r["claimed_at"]),
            )
            for r in rows
        ]

    def reap_dead_sessions(self) -> int:
        """Mark sessions with expired heartbeat as dead and clean their claims."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)).isoformat()
        with self._get_conn() as conn:
            dead = conn.execute(
                "SELECT id FROM sessions WHERE heartbeat_at < ? AND status != 'dead'",
                (cutoff,),
            ).fetchall()
            if not dead:
                return 0
            dead_ids = [r["id"] for r in dead]
            placeholders = ",".join("?" * len(dead_ids))
            conn.execute(f"DELETE FROM claims WHERE session_id IN ({placeholders})", dead_ids)
            conn.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", dead_ids)
        logger.info(f"Reaped {len(dead_ids)} dead sessions")
        return len(dead_ids)
