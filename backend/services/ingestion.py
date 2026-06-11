from __future__ import annotations

import html
from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Contact, Email, ProcessingJob, Thread
from backend.schemas import IngestEmailPayload
from backend.services.heuristic_filter import apply_heuristics


MAX_BODY_LENGTH = 10_000
TRUNCATED_BODY_LENGTH = 8_000


class IngestionError(Exception):
    def __init__(self, error_code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


def clean_subject(subject: str | None) -> str:
    cleaned = (subject or "").strip()
    return cleaned or "(no subject)"


def clean_body(body: str | None) -> str:
    if body is None:
        return ""

    stripped = html.unescape(body).strip()
    if not stripped:
        return ""

    if len(stripped) > MAX_BODY_LENGTH:
        return f"{stripped[:TRUNCATED_BODY_LENGTH]}[TRUNCATED]"

    return stripped


def get_or_create_contact(db: Session, sender_email: str) -> Contact:
    contact = db.scalar(select(Contact).where(Contact.email == sender_email))
    if contact is not None:
        return contact

    contact = Contact(email=sender_email)
    db.add(contact)
    db.flush()
    return contact


def get_or_create_thread(db: Session, thread_reference: str, subject: str, sender_email: str, timestamp: datetime) -> Thread:
    thread = db.scalar(select(Thread).where(Thread.thread_id == thread_reference))
    if thread is not None:
        thread.subject = thread.subject or subject
        thread.last_updated_at = timestamp
        return thread

    thread = Thread(
        thread_id=thread_reference,
        subject=subject,
        sender_email=sender_email,
        first_seen_at=timestamp,
        last_updated_at=timestamp,
        status="Open",
    )
    db.add(thread)
    db.flush()
    return thread


def ensure_unique_message_id(db: Session, message_id: str) -> None:
    existing = db.scalar(select(Email).where(Email.message_id == message_id))
    if existing is not None:
        raise IngestionError(
            error_code="DUPLICATE_MESSAGE_ID",
            message="Email with this message_id already exists",
            details={"message_id": message_id, "existing_id": existing.id},
        )


def ingest_email(db: Session, payload: IngestEmailPayload) -> dict[str, Any]:
    ensure_unique_message_id(db, payload.message_id)

    subject = clean_subject(payload.subject)
    body = clean_body(payload.body)
    sender_email = payload.sender.lower()

    contact = get_or_create_contact(db, sender_email)
    thread = get_or_create_thread(db, payload.thread_id, subject, sender_email, payload.timestamp)

    triage = apply_heuristics(subject=subject, body=body, sender=sender_email)
    email = Email(
        thread_id=thread.id,
        message_id=payload.message_id,
        sender=sender_email,
        subject=subject,
        body=body,
        timestamp=payload.timestamp,
        status="Received",
    )

    db.add(email)
    db.flush()

    job = ProcessingJob(
        email_id=email.id,
        status="Queued",
    )
    db.add(job)

    contact.last_contact_at = payload.timestamp
    thread.last_updated_at = payload.timestamp
    if thread.first_seen_at is None:
        thread.first_seen_at = payload.timestamp

    db.commit()
    db.refresh(email)
    db.refresh(thread)
    db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status.lower(),
        "email_id": email.id,
        "thread_id": thread.id,
        "priority_score": triage.priority_score,
        "triage": asdict(triage),
    }


def get_job_status(db: Session, job_id: int) -> dict[str, Any]:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise IngestionError(
            error_code="JOB_NOT_FOUND",
            message="Processing job not found",
            details={"job_id": job_id},
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "email_id": job.email_id,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
