from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Email, ProcessingJob
from backend.services.heuristic_filter import apply_heuristics


class JobProcessor:
    def __init__(self, db: Session):
        self.db = db

    def process_job(self, job_id: int) -> dict[str, Any]:
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

            triage = apply_heuristics(
                subject=email.subject or "",
                body=email.body or "",
                sender=email.sender or "",
            )

            email.category = "Spam" if triage.is_spam else "Security" if triage.is_security else "Internal" if triage.is_internal else "Pending"
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

    def get_pending_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        jobs = self.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "Queued")
            .limit(limit)
        ).all()

        return [{"job_id": j.id, "email_id": j.email_id} for j in jobs]
