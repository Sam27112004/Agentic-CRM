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
                llm_result = self._run_llm_classification(email)
                if llm_result:
                    if triage.is_legal:
                        llm_result.category = "Legal"
                        llm_result.requires_human = True
                        email.status = "Escalated"
                    
                    email.category = llm_result.category
                    email.sentiment_score = llm_result.sentiment_score
                    email.urgency = llm_result.urgency
                    email.requires_human = llm_result.requires_human
                    email.confidence = llm_result.confidence
                    email.raw_entities = llm_result.detected_entities.model_dump() if hasattr(llm_result.detected_entities, "model_dump") else {}
                    # Check sentiment deterioration (3+ consecutive negative emails)
                    from sqlalchemy import select
                    from backend.models.contact import Contact
                    recent_emails = self.db.scalars(
                        select(Email)
                        .where(Email.sender == email.sender)
                        .where(Email.sentiment_score != None)
                        .order_by(Email.timestamp.desc())
                        .limit(3)
                    ).all()
                    
                    if len(recent_emails) == 3 and all(e.sentiment_score and float(e.sentiment_score) < -0.2 for e in recent_emails):
                        logger.warning(f"Sentiment deterioration detected for {email.sender}")
                        email.status = "Escalated"
                        email.requires_human = True
                        email.urgency = "High"
                        email.category = "Complaint"
                        
                        # Trigger web scraping
                        contact_company = self.db.scalars(select(Contact.company).where(Contact.email == email.sender)).first()
                        if contact_company:
                            from backend.services.agent_tools import scrape_public_sentiment
                            scrape_public_sentiment(self.db, contact_company)

                    self.db.commit()

                    # --- Layer 4: Autonomous Agent Triage ---
                    from backend.services.agent import run_agent
                    logger.info(f"Running agent for email {email.id}")
                    run_agent(db=self.db, email_id=email.id, dry_run=False)

                else:
                    email.category = "Pending"

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

    def _run_llm_classification(self, email: Email) -> Any:
        """Attempt LLM classification; returns the full result."""
        try:
            from backend.services.llm_classifier import classify_email

            result = classify_email(db=self.db, email_id=email.id)
            return result
        except Exception as exc:
            logger.warning(
                "LLM classification failed for email %d, keeping Pending: %s",
                email.id,
                exc,
            )
            return None

    def get_pending_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve jobs still in Queued state."""
        jobs = self.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "Queued")
            .limit(limit)
        ).all()

        return [{"job_id": j.id, "email_id": j.email_id} for j in jobs]
