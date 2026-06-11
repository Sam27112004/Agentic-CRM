from unittest.mock import MagicMock
import pytest
from datetime import datetime, timezone
from backend.services.ingestion import ingest_email, IngestionError
from backend.schemas import IngestEmailPayload
from backend.models import Email, Contact, Thread, ProcessingJob

@pytest.fixture
def mock_db():
    return MagicMock()

def test_ingest_email_duplicate_check(mock_db):
    # Setup mock to return an existing email
    mock_db.scalar.return_value = Email(id=1, message_id="dup_001")
    
    payload = IngestEmailPayload(
        message_id="dup_001",
        thread_id="thread_001",
        sender="test@example.com",
        subject="Test",
        body="Test body",
        timestamp=datetime.now(timezone.utc)
    )
    
    with pytest.raises(IngestionError) as exc_info:
        ingest_email(mock_db, payload)
        
    assert exc_info.value.error_code == "DUPLICATE_MESSAGE_ID"

def test_ingest_email_success(mock_db):
    # Setup mock to return NO existing email (so duplicate check passes)
    # And mock the contact/thread fetching to return None so it creates them
    mock_db.scalar.side_effect = [
        None,  # duplicate check
        None,  # contact check
        None,  # thread check
    ]
    
    payload = IngestEmailPayload(
        message_id="new_001",
        thread_id="thread_002",
        sender="new@example.com",
        subject="Hello",
        body="World",
        timestamp=datetime.now(timezone.utc)
    )
    
    result = ingest_email(mock_db, payload)
    
    # Check that items were added to session
    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called
    
    assert "job_id" in result
    assert result["status"] == "queued"
    assert "priority_score" in result
