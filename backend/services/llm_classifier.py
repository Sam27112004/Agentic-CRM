"""LLM Classification Engine — Phase 8.

Classifies emails using Gemini (or OpenAI) with structured JSON output.
Injects thread history, top-3 RAG chunks, and contact profile into the prompt.
Applies conflicting-signal resolution and confidence-threshold routing.
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.contact import Contact
from backend.models.email import Email
from backend.models.thread import Thread
from backend.services.rag import get_rag_service

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")

# ---------------------------------------------------------------------------
# Pydantic schemas for the structured LLM output
# ---------------------------------------------------------------------------

class DetectedEntities(BaseModel):
    order_ids: list[str] = Field(default_factory=list)
    ticket_ids: list[str] = Field(default_factory=list)
    monetary_amounts: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    products_mentioned: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    category: str = "Other"
    sentiment: str = "Neutral"
    sentiment_score: float = 0.0
    urgency: str = "Medium"
    requires_human: bool = False
    escalation_reason: str = ""
    suggested_reply: str = ""
    confidence: float = 0.0
    detected_entities: DetectedEntities = Field(default_factory=DetectedEntities)


# Category priority order for conflicting signal resolution
CATEGORY_PRIORITY = {
    "Legal": 0,
    "Compliance": 1,
    "Complaint": 2,
    "Billing": 3,
    "Bug Report": 4,
    "Feature Request": 5,
    "Inquiry": 6,
    "Internal": 7,
    "Other": 8,
    "Spam": 9,
}

VALID_CATEGORIES = list(CATEGORY_PRIORITY.keys())
VALID_SENTIMENTS = ["Positive", "Neutral", "Negative", "Mixed"]
VALID_URGENCIES = ["Critical", "High", "Medium", "Low"]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI email triage agent for a SaaS CRM company.
Your job is to classify incoming customer emails with structured JSON output.

You must ALWAYS respond with valid JSON matching this exact schema:
{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": <float from -1.0 to 1.0>,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": <true or false>,
  "escalation_reason": "<reason or empty string>",
  "suggested_reply": "<draft reply text>",
  "confidence": <float from 0.0 to 1.0>,
  "detected_entities": {
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }
}

Rules:
- When signals conflict (e.g. positive sentiment but legal threat), apply this priority:
  Legal/Compliance > Complaint > Billing > Bug Report > Feature Request > Inquiry
- If confidence < 0.70, set requires_human to true and explain why in escalation_reason.
- For Critical urgency emails, set requires_human to true.
- For legal threats, ransomware, or cease-and-desist, always set requires_human to true.
- suggested_reply should be professional, empathetic, and cite relevant policy when applicable.
- Do NOT output anything except the JSON object. No markdown, no code fences, no explanation.
"""


def _build_user_prompt(
    email: Email,
    thread_history: list[dict[str, Any]],
    rag_chunks: list[dict[str, Any]],
    contact_profile: Optional[dict[str, Any]],
) -> str:
    """Build the user prompt with all contextual information."""
    parts: list[str] = []

    # --- Email being classified ---
    parts.append("=== EMAIL TO CLASSIFY ===")
    parts.append(f"From: {email.sender}")
    parts.append(f"Subject: {email.subject or '(no subject)'}")
    parts.append(f"Timestamp: {email.timestamp}")
    parts.append(f"Body:\n{email.body or '(empty)'}")
    parts.append("")

    # --- Thread history ---
    if thread_history:
        parts.append("=== THREAD HISTORY (oldest first) ===")
        for msg in thread_history:
            parts.append(f"[{msg['timestamp']}] {msg['sender']}: {msg['subject']}")
            body_preview = (msg.get("body") or "")[:500]
            if body_preview:
                parts.append(body_preview)
            parts.append("---")
        parts.append("")

    # --- RAG context ---
    if rag_chunks:
        parts.append("=== INTERNAL POLICY CONTEXT (from knowledge base) ===")
        for chunk in rag_chunks:
            parts.append(f"[Source: {chunk['source_doc']} | Score: {chunk['similarity_score']}]")
            parts.append(chunk["chunk_text"])
            parts.append("---")
        parts.append("")

    # --- Contact profile ---
    if contact_profile:
        parts.append("=== CONTACT PROFILE ===")
        parts.append(f"Name: {contact_profile.get('name', 'Unknown')}")
        parts.append(f"Company: {contact_profile.get('company', 'Unknown')}")
        parts.append(f"Status: {contact_profile.get('status', 'Active')}")
        parts.append(f"Account Value: ${contact_profile.get('account_value', 0)}")
        parts.append(f"Churn Risk Score: {contact_profile.get('churn_risk_score', 'N/A')}")
        parts.append("")

    parts.append("Classify this email now. Respond with JSON only.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Context gathering helpers
# ---------------------------------------------------------------------------

def _get_thread_history(db: Session, email: Email) -> list[dict[str, Any]]:
    """Return all emails in the same thread, ordered by timestamp (oldest first)."""
    thread_emails = db.scalars(
        select(Email)
        .where(Email.thread_id == email.thread_id)
        .where(Email.id != email.id)
        .order_by(Email.timestamp.asc())
    ).all()

    return [
        {
            "sender": e.sender,
            "subject": e.subject or "(no subject)",
            "body": e.body or "",
            "timestamp": str(e.timestamp),
        }
        for e in thread_emails
    ]


def _get_contact_profile(db: Session, sender_email: str) -> Optional[dict[str, Any]]:
    """Retrieve contact profile for the sender."""
    contact = db.scalars(
        select(Contact).where(Contact.email == sender_email)
    ).first()

    if contact is None:
        return None

    return {
        "name": contact.name,
        "company": contact.company,
        "status": contact.status,
        "account_value": float(contact.account_value) if contact.account_value else 0,
        "churn_risk_score": float(contact.churn_risk_score) if contact.churn_risk_score else None,
    }


def _get_rag_chunks(email: Email) -> list[dict[str, Any]]:
    """Retrieve top-3 RAG chunks relevant to this email."""
    query_text = f"{email.subject or ''} {email.body or ''}"
    rag = get_rag_service()
    return rag.search_knowledge_base(query_text, top_k=3)


# ---------------------------------------------------------------------------
# LLM API calls
# ---------------------------------------------------------------------------

def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call the Google Gemini API and return raw text response."""
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=LLM_MODEL,
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    return response.text


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call the OpenAI API and return raw text response."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Route to the configured LLM provider."""
    if GEMINI_API_KEY:
        return _call_gemini(system_prompt, user_prompt)
    elif OPENAI_API_KEY:
        return _call_openai(system_prompt, user_prompt)
    else:
        raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or OPENAI_API_KEY in .env")


# ---------------------------------------------------------------------------
# Response parsing and post-processing
# ---------------------------------------------------------------------------

def _parse_llm_response(raw: str) -> ClassificationResult:
    """Parse LLM JSON response into a validated ClassificationResult."""
    # Strip markdown code fences if the LLM added them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (code fence markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON, falling back to defaults: %s", raw[:200])
        return ClassificationResult(
            category="Other",
            urgency="Medium",
            requires_human=True,
            escalation_reason="LLM returned unparseable output",
            confidence=0.0,
        )

    return ClassificationResult(**data)


def _apply_post_processing(result: ClassificationResult) -> ClassificationResult:
    """Apply business rules on top of LLM output.

    - Validate category/sentiment/urgency values
    - Enforce confidence < 0.70 -> requires_human
    - Clamp sentiment_score to [-1, 1]
    """
    # Validate category
    if result.category not in VALID_CATEGORIES:
        result.category = "Other"

    # Validate sentiment
    if result.sentiment not in VALID_SENTIMENTS:
        result.sentiment = "Neutral"

    # Validate urgency
    if result.urgency not in VALID_URGENCIES:
        result.urgency = "Medium"

    # Clamp sentiment_score
    result.sentiment_score = max(-1.0, min(1.0, result.sentiment_score))

    # Clamp confidence
    result.confidence = max(0.0, min(1.0, result.confidence))

    # Confidence threshold: < 0.70 always routes to human
    if result.confidence < 0.70:
        result.requires_human = True
        if not result.escalation_reason:
            result.escalation_reason = f"Low confidence ({result.confidence:.2f})"

    # Critical urgency always requires human
    if result.urgency == "Critical":
        result.requires_human = True

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_email(db: Session, email_id: int) -> ClassificationResult:
    """Classify an email using the LLM with full context injection.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email to classify.

    Returns:
        ClassificationResult with category, sentiment, urgency, etc.

    Raises:
        ValueError: If the email is not found.
    """
    email = db.get(Email, email_id)
    if email is None:
        raise ValueError(f"Email {email_id} not found")

    # Gather context
    thread_history = _get_thread_history(db, email)
    rag_chunks = _get_rag_chunks(email)
    contact_profile = _get_contact_profile(db, email.sender or "")

    # Build prompt
    user_prompt = _build_user_prompt(email, thread_history, rag_chunks, contact_profile)

    # Call LLM
    raw_response = _call_llm(SYSTEM_PROMPT, user_prompt)

    # Parse and post-process
    result = _parse_llm_response(raw_response)
    result = _apply_post_processing(result)

    # Persist classification on the email record
    email.category = result.category
    email.sentiment_score = Decimal(str(result.sentiment_score))
    email.urgency = result.urgency
    email.requires_human = result.requires_human
    email.confidence = Decimal(str(result.confidence))
    email.raw_entities = result.detected_entities.model_dump()
    db.commit()

    logger.info(
        "Classified email %d: category=%s urgency=%s confidence=%.2f requires_human=%s",
        email_id,
        result.category,
        result.urgency,
        result.confidence,
        result.requires_human,
    )

    return result
