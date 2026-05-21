"""Tests for the database layer."""

import time
from datetime import datetime, timezone, timedelta

from mcp_session_registry.db import SessionDB, HEARTBEAT_TIMEOUT_SECONDS
from mcp_session_registry.models import Claim, Session


def test_register_and_list(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234, theme="MIR F013")
    tmp_db.register(session)

    active = tmp_db.list_active()
    assert len(active) == 1
    assert active[0]["cli"] == "kiro"
    assert active[0]["theme"] == "MIR F013"
    assert active[0]["pid"] == 1234


def test_multiple_sessions(tmp_db: SessionDB):
    for i in range(3):
        s = Session(cli="kiro", hostname="test-host", pid=1000 + i, theme=f"theme-{i}")
        tmp_db.register(s)

    active = tmp_db.list_active()
    assert len(active) == 3


def test_heartbeat(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    ok = tmp_db.heartbeat(session.id)
    assert ok is True

    # Non-existent session
    ok = tmp_db.heartbeat("nonexistent-id")
    assert ok is False


def test_end_session(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    ok = tmp_db.end(session.id)
    assert ok is True

    active = tmp_db.list_active()
    assert len(active) == 0


def test_end_cleans_claims(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    claim = Claim(session_id=session.id, resource="/home/user/file.py")
    tmp_db.claim(claim)

    tmp_db.end(session.id)

    # Claims should be gone
    conflicts = tmp_db.get_conflicts("other-session", ["/home/user/file.py"])
    assert len(conflicts) == 0


def test_claim_and_conflict(tmp_db: SessionDB):
    s1 = Session(cli="kiro", hostname="test-host", pid=1001, theme="session-1")
    s2 = Session(cli="kiro", hostname="test-host", pid=1002, theme="session-2")
    tmp_db.register(s1)
    tmp_db.register(s2)

    # s1 claims a file
    claim = Claim(session_id=s1.id, resource="~/git/mir/api/")
    tmp_db.claim(claim)

    # s2 checks for conflicts
    conflicts = tmp_db.get_conflicts(s2.id, ["~/git/mir/api/"])
    assert len(conflicts) == 1
    assert conflicts[0].claimed_by_session == s1.id
    assert conflicts[0].claimed_by_theme == "session-1"

    # s1 checks same resource — no conflict (it's their own)
    conflicts = tmp_db.get_conflicts(s1.id, ["~/git/mir/api/"])
    assert len(conflicts) == 0


def test_release(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    claim = Claim(session_id=session.id, resource="/tmp/file.txt")
    tmp_db.claim(claim)

    ok = tmp_db.release(session.id, "/tmp/file.txt")
    assert ok is True

    # No more conflicts
    conflicts = tmp_db.get_conflicts("other", ["/tmp/file.txt"])
    assert len(conflicts) == 0


def test_reap_dead_sessions(tmp_db: SessionDB):
    # Create session with old heartbeat
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    # Manually set heartbeat to past
    with tmp_db._get_conn() as conn:
        old_time = (datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS + 60)).isoformat()
        conn.execute("UPDATE sessions SET heartbeat_at = ? WHERE id = ?", (old_time, session.id))

    # Also add a claim
    claim = Claim(session_id=session.id, resource="/tmp/dead.py")
    tmp_db.claim(claim)

    # Reap
    reaped = tmp_db.reap_dead_sessions()
    assert reaped == 1

    # Session and claims gone
    active = tmp_db.list_active()
    assert len(active) == 0


def test_reap_keeps_alive_sessions(tmp_db: SessionDB):
    session = Session(cli="kiro", hostname="test-host", pid=1234)
    tmp_db.register(session)

    # Fresh heartbeat — should NOT be reaped
    reaped = tmp_db.reap_dead_sessions()
    assert reaped == 0

    active = tmp_db.list_active()
    assert len(active) == 1


def test_no_conflicts_empty_resources(tmp_db: SessionDB):
    conflicts = tmp_db.get_conflicts("any-session", [])
    assert len(conflicts) == 0
