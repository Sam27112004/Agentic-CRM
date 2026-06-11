from unittest.mock import MagicMock, patch
import pytest
from backend.services.agent_tools import (
    escalate_to_human,
    flag_for_legal,
    create_internal_ticket,
    draft_reply
)
from backend.models import Email

@pytest.fixture
def mock_db():
    return MagicMock()

def test_escalate_to_human(mock_db):
    mock_email = Email(id=1, status="Received")
    mock_db.get.return_value = mock_email
    
    result = escalate_to_human(mock_db, 1, "Needs human review", "High")
    
    assert result["status"] == "Escalated"
    assert result["email_id"] == 1
    assert mock_email.status == "Escalated"
    assert mock_db.add.called
    assert mock_db.commit.called

def test_flag_for_legal(mock_db):
    mock_email = Email(id=1, status="Received")
    mock_db.get.return_value = mock_email
    
    result = flag_for_legal(mock_db, 1, "Threatening lawsuit")
    
    assert result["status"] == "Legal-Flagged"
    assert mock_email.status == "Escalated"
    assert mock_db.add.called
    assert mock_db.commit.called

def test_draft_reply(mock_db):
    mock_email = Email(id=1, status="Received")
    mock_db.get.return_value = mock_email
    
    # We need to simulate flush populating the ID
    def mock_flush():
        pass
    mock_db.flush.side_effect = mock_flush
    
    result = draft_reply(mock_db, 1, "Hello, we are looking into this.")
    
    assert result["status"] == "Pending"
    assert "draft_id" in result
    assert mock_db.add.called
    assert mock_db.commit.called
