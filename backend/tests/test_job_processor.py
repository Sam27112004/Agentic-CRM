from unittest.mock import MagicMock, patch
import pytest
from backend.services.job_processor import JobProcessor
from backend.models import ProcessingJob, Email
from backend.services.heuristic_filter import HeuristicResult

@pytest.fixture
def mock_db():
    return MagicMock()

def test_process_job_not_found(mock_db):
    mock_db.get.return_value = None
    processor = JobProcessor(mock_db)
    
    result = processor.process_job(1)
    
    assert result["status"] == "Failed"
    assert result["error"] == "Job not found"

def test_process_job_already_processing(mock_db):
    mock_job = ProcessingJob(id=1, status="Processing")
    mock_db.get.return_value = mock_job
    processor = JobProcessor(mock_db)
    
    result = processor.process_job(1)
    
    assert result["status"] == "Processing"
    assert "Job is already processing" in result["error"]

@patch("backend.services.job_processor.apply_heuristics")
def test_process_job_spam(mock_apply_heuristics, mock_db):
    mock_job = ProcessingJob(id=1, status="Queued", email_id=1)
    mock_email = Email(id=1, subject="Test", body="Test", sender="spam@example.com")
    
    # mock_db.get will be called for Job then Email
    mock_db.get.side_effect = [mock_job, mock_email]
    
    mock_apply_heuristics.return_value = HeuristicResult(
        is_spam=True, is_security=False, is_internal=False, priority_score=1, labels=["spam"]
    )
    
    processor = JobProcessor(mock_db)
    result = processor.process_job(1)
    
    assert result["status"] == "Completed"
    assert result["category"] == "Spam"
    assert mock_email.status == "Ignored"
    assert mock_job.status == "Completed"
    assert mock_db.commit.called

@patch("backend.services.job_processor.JobProcessor._run_llm_classification")
@patch("backend.services.job_processor.apply_heuristics")
def test_process_job_normal_email(mock_apply_heuristics, mock_run_llm, mock_db):
    mock_job = ProcessingJob(id=1, status="Queued", email_id=1)
    mock_email = Email(id=1, subject="Test", body="Test", sender="user@example.com")
    
    mock_db.get.side_effect = [mock_job, mock_email]
    
    mock_apply_heuristics.return_value = HeuristicResult(
        is_spam=False, is_security=False, is_internal=False, priority_score=3, labels=["priority_3"]
    )
    
    mock_run_llm.return_value = "Inquiry"
    
    processor = JobProcessor(mock_db)
    result = processor.process_job(1)
    
    assert result["status"] == "Completed"
    assert result["category"] == "Inquiry"
    assert mock_job.status == "Completed"
    assert mock_db.commit.called
