from __future__ import annotations

from typing import Any, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import Action, Contact, Draft, Email, Thread
from backend.schemas import IngestEmailPayload, IngestResponse, JobStatusResponse
from backend.services.ingestion import IngestionError, get_job_status, ingest_email
from backend.services.job_processor import JobProcessor
from backend.services.rag import get_rag_service


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class RAGChunk(BaseModel):
    chunk_text: str
    source_doc: str
    similarity_score: float


class RAGSearchResponse(BaseModel):
    query: str
    results: List[RAGChunk]


app = FastAPI(
    title="Agentic CRM Intelligence Platform",
    description="""
An autonomous AI-powered CRM email triage and resolution system.

## Features
* **Ingestion API**: Ingest emails asynchronously and queue for processing.
* **Autonomous Agent**: ReAct loop powered by Gemini to triage, escalate, or auto-reply.
* **RAG Knowledge Base**: Vector search for internal policies to ground agent actions.
""",
    version="1.0.0",
    contact={
        "name": "Sam",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # Pre-load the RAG service so sentence-transformers is warm for first query
    get_rag_service()


def process_background_job(job_id: int) -> None:
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        processor = JobProcessor(db)
        processor.process_job(job_id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

@app.post("/api/ingest", response_model=IngestResponse)
def api_ingest(
    payload: IngestEmailPayload,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    try:
        result = ingest_email(db=db, payload=payload)
        background_tasks.add_task(process_background_job, result["job_id"])
        return result
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if exc.error_code == "DUPLICATE_MESSAGE_ID" else status.HTTP_400_BAD_REQUEST,
            detail={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
        ) from exc


@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
def api_status(job_id: int, db: Session = Depends(get_db)):
    try:
        return get_job_status(db=db, job_id=job_id)
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
        ) from exc


# ---------------------------------------------------------------------------
# Email listing (for Inbox view)
# ---------------------------------------------------------------------------

@app.get("/api/emails")
def list_emails(
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    sender: Optional[str] = None,
    sort_by: str = Query("timestamp", description="Sort field: timestamp, category, urgency, sentiment_score"),
    sort_dir: str = Query("desc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """List emails with filtering, sorting, and pagination."""
    query = select(Email)

    if status_filter:
        query = query.where(Email.status == status_filter)
    if category:
        query = query.where(Email.category == category)
    if urgency:
        query = query.where(Email.urgency == urgency)
    if sender:
        query = query.where(Email.sender.ilike(f"%{sender}%"))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Sort
    sort_col = getattr(Email, sort_by, Email.timestamp)
    if sort_dir == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    emails = db.scalars(query).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "sender": e.sender,
                "subject": e.subject or "(no subject)",
                "body_preview": (e.body or "")[:200],
                "timestamp": str(e.timestamp) if e.timestamp else None,
                "category": e.category,
                "urgency": e.urgency,
                "sentiment_score": float(e.sentiment_score) if e.sentiment_score is not None else None,
                "requires_human": e.requires_human,
                "confidence": float(e.confidence) if e.confidence is not None else None,
                "status": e.status,
                "thread_id": e.thread_id,
            }
            for e in emails
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Counts: Pending, Replied, Escalated, Critical, Spam."""
    statuses = db.execute(
        select(Email.status, func.count(Email.id)).group_by(Email.status)
    ).all()
    status_counts = {row[0]: row[1] for row in statuses}

    categories = db.execute(
        select(Email.category, func.count(Email.id)).group_by(Email.category)
    ).all()
    category_counts = {row[0]: row[1] for row in categories if row[0]}

    total = db.scalar(select(func.count(Email.id))) or 0

    return {
        "total_emails": total,
        "by_status": status_counts,
        "by_category": category_counts,
    }


# ---------------------------------------------------------------------------
# Thread view
# ---------------------------------------------------------------------------

@app.get("/threads/{contact_email}")
def get_thread(contact_email: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Full thread with emails, actions, drafts, and agent logs for a contact."""
    threads = db.scalars(
        select(Thread).where(Thread.sender_email == contact_email)
    ).all()

    if not threads:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "THREAD_NOT_FOUND", "message": f"No threads for {contact_email}"},
        )

    # Contact profile
    contact = db.scalars(
        select(Contact).where(Contact.email == contact_email)
    ).first()

    contact_data = None
    if contact:
        contact_data = {
            "email": contact.email,
            "name": contact.name,
            "company": contact.company,
            "status": contact.status,
            "account_value": float(contact.account_value) if contact.account_value else 0,
            "churn_risk_score": float(contact.churn_risk_score) if contact.churn_risk_score else None,
        }

    # All emails across threads
    thread_ids = [t.id for t in threads]
    emails = db.scalars(
        select(Email).where(Email.thread_id.in_(thread_ids)).order_by(Email.timestamp.asc())
    ).all()

    email_ids = [e.id for e in emails]

    # Actions for these emails
    actions = db.scalars(
        select(Action).where(Action.email_id.in_(email_ids))
    ).all() if email_ids else []

    # Drafts for these emails
    drafts = db.scalars(
        select(Draft).where(Draft.email_id.in_(email_ids))
    ).all() if email_ids else []

    return {
        "contact": contact_data,
        "threads": [
            {
                "id": t.id,
                "thread_id": t.thread_id,
                "subject": t.subject,
                "status": t.status,
                "first_seen_at": str(t.first_seen_at) if t.first_seen_at else None,
                "last_updated_at": str(t.last_updated_at) if t.last_updated_at else None,
            }
            for t in threads
        ],
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "sender": e.sender,
                "subject": e.subject or "(no subject)",
                "body": e.body or "",
                "timestamp": str(e.timestamp) if e.timestamp else None,
                "category": e.category,
                "urgency": e.urgency,
                "sentiment_score": float(e.sentiment_score) if e.sentiment_score is not None else None,
                "requires_human": e.requires_human,
                "confidence": float(e.confidence) if e.confidence is not None else None,
                "status": e.status,
                "raw_entities": e.raw_entities,
            }
            for e in emails
        ],
        "actions": [
            {
                "id": a.id,
                "email_id": a.email_id,
                "action_type": a.action_type,
                "proposed_content": a.proposed_content,
                "agent_reasoning_log": a.agent_reasoning_log,
                "is_approved": a.is_approved,
                "executed_at": str(a.executed_at) if a.executed_at else None,
            }
            for a in actions
        ],
        "drafts": [
            {
                "id": d.id,
                "email_id": d.email_id,
                "content": d.content,
                "status": d.status,
                "created_at": str(d.created_at) if d.created_at else None,
                "approved_at": str(d.approved_at) if d.approved_at else None,
            }
            for d in drafts
        ],
    }


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

@app.get("/rag/search", response_model=RAGSearchResponse)
def rag_search(q: str = Query(..., description="Query text to search the knowledge base")):
    """Debug endpoint: embed query, retrieve top-3 KB chunks with similarity scores."""
    rag = get_rag_service()
    chunks = rag.search_knowledge_base(q)
    return RAGSearchResponse(query=q, results=chunks)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@app.post("/agent/dry-run/{email_id}")
def agent_dry_run(email_id: int, db: Session = Depends(get_db)):
    """Run the agent reasoning loop without executing write actions.

    Returns the complete reasoning trace for inspection.
    """
    from backend.services.agent import run_agent

    try:
        result = run_agent(db=db, email_id=email_id, dry_run=True)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "EMAIL_NOT_FOUND", "message": str(exc)},
        ) from exc

