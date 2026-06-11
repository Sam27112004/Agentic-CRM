from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Email, ProcessingJob
from backend.services.heuristic_filter import apply_heuristics

logger = logging.getLogger(__name__)


class JobProcessor:
    """Processes queued email jobs through heuristics and LLM classification."""

    def __init__(self, db: Session):
        self.db = db

    def process_job(self, job_id: int) -> dict[str, Any]:
        """Run the full processing pipeline for a single job."""
        job = self.db.get(ProcessingJob, job_id)
        if job is None:
            return {"job_id": job_id, "status": "Failed", "error": "Job not found"}

        if job.status != "Queued":
            return {
                "job_id": job_id,
                "status": job.status,
                "error": f"Job is already {job.status.lower()}",
            }

        job.status = "Processing"
        self.db.commit()

        try:
            email = self.db.get(Email, job.email_id)
            if email is None:
                raise ValueError(f"Email {job.email_id} not found")

            # --- Layer 1: Heuristic pre-filter ---
            triage = apply_heuristics(
                subject=email.subject or "",
                body=email.body or "",
                sender=email.sender or "",
            )

            if triage.is_spam:
                email.category = "Spam"
                email.status = "Ignored"
            elif triage.is_security:
                email.category = "Security"
                email.status = "Escalated"
            elif triage.is_internal:
                email.category = "Internal"
            else:
                # --- Layer 2: LLM classification for non-trivial emails ---
                email.category = self._run_llm_classification(email)

            job.status = "Completed"
            job.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "job_id": job_id,
                "status": "Completed",
                "email_id": email.id,
                "category": email.category,
                "triage": triage.labels,
            }
        except Exception as exc:
            job.status = "Failed"
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "job_id": job_id,
                "status": "Failed",
                "error": str(exc),
            }

    def _run_llm_classification(self, email: Email) -> str:
        """Attempt LLM classification; fall back to 'Pending' on failure."""
        try:
            from backend.services.llm_classifier import classify_email

            result = classify_email(db=self.db, email_id=email.id)
            return result.category
        except Exception as exc:
            logger.warning(
                "LLM classification failed for email %d, keeping Pending: %s",
                email.id,
                exc,
            )
            return "Pending"

    def get_pending_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve jobs still in Queued state."""
        jobs = self.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "Queued")
            .limit(limit)
        ).all()

        return [{"job_id": j.id, "email_id": j.email_id} for j in jobs]
