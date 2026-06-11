from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngestEmailPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    sender: str = Field(min_length=3)
    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: datetime

    @field_validator("sender")
    @classmethod
    def validate_sender(cls, value: str) -> str:
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
            raise ValueError("sender must be a valid email address")
        return value


class IngestResponse(BaseModel):
    job_id: int
    status: str
    email_id: int
    thread_id: int
    priority_score: int
    triage: dict[str, Any]


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    email_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
