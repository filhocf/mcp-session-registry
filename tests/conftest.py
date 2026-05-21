"""Test fixtures."""

import tempfile
from pathlib import Path

import pytest

from mcp_session_registry.db import SessionDB


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_sessions.db"
    return SessionDB(db_path=db_path)
