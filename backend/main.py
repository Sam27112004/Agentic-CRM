from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.schemas import IngestEmailPayload, IngestResponse, JobStatusResponse
from backend.services.ingestion import IngestionError, get_job_status, ingest_email


app = FastAPI(title="Agentic CRM Intelligence Platform", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/api/ingest", response_model=IngestResponse)
def api_ingest(payload: IngestEmailPayload, db: Session = Depends(get_db)):
    try:
        return ingest_email(db=db, payload=payload)
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
