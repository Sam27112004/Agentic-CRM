"""Agent Tools — Phase 9.

Seven tools callable by the ReAct agent. Each tool accepts structured input,
performs a database or external operation, and returns a structured dict that
the agent can use as an observation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.action import Action
from backend.models.audit_log import AuditLog
from backend.models.contact import Contact
from backend.models.draft import Draft
from backend.models.email import Email
from backend.models.thread import Thread
from backend.models.web_intelligence_cache import WebIntelligenceCache
from backend.services.rag import get_rag_service

logger = logging.getLogger(__name__)

WEB_INTEL_CACHE_TTL = int(os.getenv("WEB_INTEL_CACHE_TTL", "21600"))  # 6 hours


# ---------------------------------------------------------------------------
# Tool 1: get_thread_history
# ---------------------------------------------------------------------------

def get_thread_history(db: Session, sender_email: str) -> dict[str, Any]:
    """Return all emails in threads associated with a sender, ordered by timestamp.

    Args:
        db: SQLAlchemy session.
        sender_email: The sender's email address.

    Returns:
        Dict with thread_count, email_count, and list of emails.
    """
    threads = db.scalars(
        select(Thread).where(Thread.sender_email == sender_email)
    ).all()

    if not threads:
        return {"thread_count": 0, "email_count": 0, "emails": []}

    thread_ids = [t.id for t in threads]
    emails = db.scalars(
        select(Email)
        .where(Email.thread_id.in_(thread_ids))
        .order_by(Email.timestamp.asc())
    ).all()

    return {
        "thread_count": len(threads),
        "email_count": len(emails),
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "sender": e.sender,
                "subject": e.subject or "(no subject)",
                "body": (e.body or "")[:500],
                "timestamp": str(e.timestamp),
                "category": e.category,
                "sentiment_score": float(e.sentiment_score) if e.sentiment_score else None,
                "status": e.status,
            }
            for e in emails
        ],
    }


# ---------------------------------------------------------------------------
# Tool 2: search_knowledge_base
# ---------------------------------------------------------------------------

def search_knowledge_base(query: str) -> dict[str, Any]:
    """Query the RAG pipeline and return top-3 chunks with similarity scores.

    Args:
        query: Natural language query to search the knowledge base.

    Returns:
        Dict with query and list of matching chunks.
    """
    rag = get_rag_service()
    chunks = rag.search_knowledge_base(query, top_k=3)
    return {"query": query, "results": chunks}


# ---------------------------------------------------------------------------
# Tool 3: draft_reply
# ---------------------------------------------------------------------------

def draft_reply(db: Session, email_id: int, suggested_content: str) -> dict[str, Any]:
    """Create a Draft record with suggested reply content.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email being replied to.
        suggested_content: The draft reply text.

    Returns:
        Dict with draft_id and status.
    """
    email = db.get(Email, email_id)
    if email is None:
        return {"error": f"Email {email_id} not found"}

    draft = Draft(
        email_id=email_id,
        content=suggested_content,
        status="Pending",
    )
    db.add(draft)

    # Log in audit trail
    audit = AuditLog(
        entity_type="draft",
        entity_id=0,  # will update after flush
        action="draft_created",
        performed_by="agent",
        diff={"email_id": email_id, "content_length": len(suggested_content)},
    )
    db.add(audit)
    db.flush()  # get draft.id
    audit.entity_id = draft.id
    db.commit()

    logger.info("Created draft %d for email %d", draft.id, email_id)

    return {
        "draft_id": draft.id,
        "email_id": email_id,
        "status": "Pending",
        "content_preview": suggested_content[:200],
    }


# ---------------------------------------------------------------------------
# Tool 4: escalate_to_human
# ---------------------------------------------------------------------------

def escalate_to_human(
    db: Session, email_id: int, reason: str, priority: str = "High"
) -> dict[str, Any]:
    """Escalate an email to a human agent.

    Updates the email status to Escalated and creates an Action record
    with the escalation reasoning.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email to escalate.
        reason: Why this email needs human attention.
        priority: Priority level for the escalation.

    Returns:
        Dict with action_id and escalation details.
    """
    email = db.get(Email, email_id)
    if email is None:
        return {"error": f"Email {email_id} not found"}

    email.status = "Escalated"

    action = Action(
        email_id=email_id,
        action_type="Escalate",
        proposed_content=reason,
        agent_reasoning_log={"reason": reason, "priority": priority},
    )
    db.add(action)

    # Audit trail
    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="escalated_to_human",
        performed_by="agent",
        diff={"reason": reason, "priority": priority, "previous_status": "Received"},
    )
    db.add(audit)
    db.commit()

    logger.info("Escalated email %d: %s", email_id, reason)

    return {
        "action_id": action.id,
        "email_id": email_id,
        "status": "Escalated",
        "reason": reason,
        "priority": priority,
    }


# ---------------------------------------------------------------------------
# Tool 5: flag_for_legal
# ---------------------------------------------------------------------------

def flag_for_legal(
    db: Session, email_id: int, threat_summary: str
) -> dict[str, Any]:
    """Flag an email for legal review.

    Creates an Action record with the legal flag and updates the email status.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email to flag.
        threat_summary: Summary of the legal threat or compliance issue.

    Returns:
        Dict with action_id and flag details.
    """
    email = db.get(Email, email_id)
    if email is None:
        return {"error": f"Email {email_id} not found"}

    email.status = "Escalated"

    action = Action(
        email_id=email_id,
        action_type="Legal-Flag",
        proposed_content=threat_summary,
        agent_reasoning_log={"threat_summary": threat_summary, "flagged_for": "legal"},
    )
    db.add(action)

    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="flagged_for_legal",
        performed_by="agent",
        diff={"threat_summary": threat_summary},
    )
    db.add(audit)
    db.commit()

    logger.info("Flagged email %d for legal: %s", email_id, threat_summary)

    return {
        "action_id": action.id,
        "email_id": email_id,
        "status": "Legal-Flagged",
        "threat_summary": threat_summary,
    }


# ---------------------------------------------------------------------------
# Tool 6: create_internal_ticket
# ---------------------------------------------------------------------------

def create_internal_ticket(
    db: Session, email_id: int, contact_email: str, issue_summary: str, urgency: str = "Medium"
) -> dict[str, Any]:
    """Create an internal ticket for follow-up.

    Logs an Action record that can integrate with an external ticket system later.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email triggering the ticket.
        contact_email: The customer's email address.
        issue_summary: Brief description of the issue.
        urgency: Urgency level (Critical/High/Medium/Low).

    Returns:
        Dict with action_id and ticket details.
    """
    email = db.get(Email, email_id)
    if email is None:
        return {"error": f"Email {email_id} not found"}

    action = Action(
        email_id=email_id,
        action_type="Ticket-Created",
        proposed_content=issue_summary,
        agent_reasoning_log={
            "contact_email": contact_email,
            "issue_summary": issue_summary,
            "urgency": urgency,
        },
    )
    db.add(action)

    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="internal_ticket_created",
        performed_by="agent",
        diff={
            "contact_email": contact_email,
            "issue_summary": issue_summary,
            "urgency": urgency,
        },
    )
    db.add(audit)
    db.commit()

    logger.info("Created internal ticket for email %d: %s", email_id, issue_summary)

    return {
        "action_id": action.id,
        "email_id": email_id,
        "contact_email": contact_email,
        "issue_summary": issue_summary,
        "urgency": urgency,
    }


# ---------------------------------------------------------------------------
# Tool 7: scrape_public_sentiment
# ---------------------------------------------------------------------------

# In-memory cache for web intel (production would use Redis)
_web_intel_cache: dict[str, dict[str, Any]] = {}


def scrape_public_sentiment(
    db: Session, company_name: str
) -> dict[str, Any]:
    """Scrape public sentiment data for a company.

    Checks in-memory cache first (6h TTL), then database cache, then
    attempts to scrape review sites. Falls back gracefully on failure.

    Args:
        db: SQLAlchemy session.
        company_name: Name of the company to look up.

    Returns:
        Dict with scraped reputation data or a fallback message.
    """
    cache_key = company_name.lower().strip()
    now = datetime.now(timezone.utc)

    # --- Check in-memory cache ---
    if cache_key in _web_intel_cache:
        cached = _web_intel_cache[cache_key]
        if cached["expires_at"] > now:
            logger.info("Web intel cache hit (in-memory) for %s", company_name)
            return cached["data"]

    # --- Check database cache ---
    db_cache = db.scalars(
        select(WebIntelligenceCache)
        .where(WebIntelligenceCache.target_entity == cache_key)
        .where(WebIntelligenceCache.expires_at > now)
        .order_by(WebIntelligenceCache.scraped_at.desc())
    ).first()

    if db_cache and db_cache.scraped_data:
        # Warm the in-memory cache
        _web_intel_cache[cache_key] = {
            "data": db_cache.scraped_data,
            "expires_at": db_cache.expires_at,
        }
        logger.info("Web intel cache hit (database) for %s", company_name)
        return db_cache.scraped_data

    # --- Attempt to scrape ---
    scraped = _do_scrape(company_name)

    # Store in database
    expires_at = now + timedelta(seconds=WEB_INTEL_CACHE_TTL)
    cache_record = WebIntelligenceCache(
        source_url=f"https://www.trustpilot.com/review/{company_name.lower().replace(' ', '-')}",
        target_entity=cache_key,
        scraped_data=scraped,
        expires_at=expires_at,
    )
    db.add(cache_record)
    db.commit()

    # Store in-memory
    _web_intel_cache[cache_key] = {"data": scraped, "expires_at": expires_at}

    return scraped


def _do_scrape(company_name: str) -> dict[str, Any]:
    """Attempt to scrape public review data. Gracefully degrades on failure."""
    urls = [
        f"https://www.trustpilot.com/review/{company_name.lower().replace(' ', '-')}",
        f"https://www.g2.com/products/{company_name.lower().replace(' ', '-')}/reviews",
    ]

    results: dict[str, Any] = {
        "company": company_name,
        "sources_checked": [],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "data_available": False,
    }

    for url in urls:
        try:
            # Check robots.txt first
            if not _check_robots_txt(url):
                results["sources_checked"].append({"url": url, "status": "blocked_by_robots_txt"})
                continue

            response = httpx.get(url, timeout=10, follow_redirects=True)
            if response.status_code == 200:
                results["sources_checked"].append({
                    "url": url,
                    "status": "success",
                    "status_code": response.status_code,
                    "content_length": len(response.text),
                })
                results["data_available"] = True
            else:
                results["sources_checked"].append({
                    "url": url,
                    "status": "http_error",
                    "status_code": response.status_code,
                })
        except Exception as exc:
            results["sources_checked"].append({
                "url": url,
                "status": "error",
                "error": str(exc),
            })
            logger.warning("Scrape failed for %s: %s", url, exc)

    return results


def _check_robots_txt(url: str) -> bool:
    """Check if scraping is allowed by robots.txt. Returns True if allowed or uncertain."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = httpx.get(robots_url, timeout=5)
        if response.status_code == 200:
            # Simple check: if our target path is explicitly disallowed, skip
            path = parsed.path
            for line in response.text.splitlines():
                line = line.strip().lower()
                if line.startswith("disallow:"):
                    disallowed = line.split(":", 1)[1].strip()
                    if disallowed and path.startswith(disallowed):
                        return False
        return True
    except Exception:
        # If we can't fetch robots.txt, assume allowed
        return True


# ---------------------------------------------------------------------------
# Tool registry — maps tool names to callables for the agent dispatcher
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_thread_history": {
        "fn": get_thread_history,
        "description": "Retrieve all emails in threads from a sender, ordered by timestamp.",
        "requires_db": True,
        "params": ["sender_email"],
    },
    "search_knowledge_base": {
        "fn": search_knowledge_base,
        "description": "Search internal policy documents (RAG). Returns top-3 relevant chunks.",
        "requires_db": False,
        "params": ["query"],
    },
    "draft_reply": {
        "fn": draft_reply,
        "description": "Create a draft reply for an email. Content is held for human approval.",
        "requires_db": True,
        "params": ["email_id", "suggested_content"],
    },
    "escalate_to_human": {
        "fn": escalate_to_human,
        "description": "Escalate an email to a human agent with a reason and priority.",
        "requires_db": True,
        "params": ["email_id", "reason"],
    },
    "flag_for_legal": {
        "fn": flag_for_legal,
        "description": "Flag an email for legal review with a threat summary.",
        "requires_db": True,
        "params": ["email_id", "threat_summary"],
    },
    "create_internal_ticket": {
        "fn": create_internal_ticket,
        "description": "Create an internal support ticket for follow-up.",
        "requires_db": True,
        "params": ["email_id", "contact_email", "issue_summary", "urgency"],
    },
    "scrape_public_sentiment": {
        "fn": scrape_public_sentiment,
        "description": "Scrape public review sites for company reputation data.",
        "requires_db": True,
        "params": ["company_name"],
    },
}
