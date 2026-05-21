"""Pydantic models for session registry."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class SessionStatus(str, Enum):
    active = "active"
    idle = "idle"
    dead = "dead"


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cli: str = Field(description="CLI type: kiro, gemini, claude-code, codex")
    hostname: str
    pid: int
    theme: str = Field(default="", description="What this session is working on")
    status: SessionStatus = SessionStatus.active
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    resource: str = Field(description="File path, branch name, or item ID")
    resource_type: str = Field(default="file", description="file, branch, item")
    claimed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conflict(BaseModel):
    resource: str
    resource_type: str
    claimed_by_session: str
    claimed_by_cli: str
    claimed_by_theme: str
    claimed_at: datetime


class RegisterInput(BaseModel):
    cli: str = Field(description="CLI type: kiro, gemini, claude-code, codex")
    pid: int
    theme: Optional[str] = ""
    hostname: Optional[str] = None


class ClaimInput(BaseModel):
    session_id: str
    resource: str
    resource_type: str = "file"


class ConflictCheckInput(BaseModel):
    session_id: str
    resources: list[str] = Field(description="List of resources to check")
