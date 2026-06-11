import pytest
from backend.services.heuristic_filter import apply_heuristics

def test_spam_detection():
    # Clear spam pattern
    result = apply_heuristics(
        subject="You won a prize!",
        body="Click here to claim your 100% free prize.",
        sender="scammer@example.com"
    )
    assert result.is_spam is True
    assert "spam" in result.labels
    
    # Internal email, NOT spam
    result2 = apply_heuristics(
        subject="Project update",
        body="Here is the update.",
        sender="sam@mycompany.com"
    )
    assert result2.is_spam is False
    assert "internal" in result2.labels

def test_security_detection():
    result = apply_heuristics(
        subject="URGENT: Legal issue",
        body="Cease and desist immediately or face legal action.",
        sender="lawyer@firm.com"
    )
    assert result.is_security is True
    assert "security" in result.labels

def test_priority_scoring():
    # VIP domain should boost priority
    result = apply_heuristics(
        subject="Need help urgent",
        body="System is down",
        sender="ceo@enterprise.net"
    )
    # VIP (+1) and 'urgent' (+1)
    assert result.priority_score >= 3
    
    # Normal inquiry
    result2 = apply_heuristics(
        subject="Question about billing",
        body="How much does this cost?",
        sender="customer@gmail.com"
    )
    # 'billing' (+1)
    assert result2.priority_score == 2
