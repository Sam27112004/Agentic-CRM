from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


SPAM_PATTERNS = (
    "buy now",
    "nigerian prince",
    "100% free",
    "free money",
    "work from home",
)

SECURITY_PATTERNS = (
    "urgent",
    "p0",
    "ransomware",
    "btc",
    "bitcoin",
    "data breach",
    "suspicious login",
)

LEGAL_PATTERNS = (
    "legal",
    "cease and desist",
    "gdpr",
    "data portability",
    "article 20",
    "right to be forgotten",
    "data processing agreement",
)

DOMAIN_REPUTATION_BLOCKLIST = {
    "mailinator.com",
    "tempmail.com",
    "example.com",
}


@dataclass(slots=True)
class HeuristicResult:
    is_spam: bool
    is_security: bool
    is_legal: bool
    is_internal: bool
    priority_score: int
    labels: list[str]


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _extract_domain(email_address: str) -> str:
    match = re.search(r"@([^>\s]+)$", email_address.strip())
    return match.group(1).lower() if match else ""


def score_priority(subject: str, body: str, sender: str) -> int:
    text = f"{subject}\n{body}".lower()
    score = 1

    priority_keywords = (
        "urgent",
        "p0",
        "legal",
        "refund",
        "billing",
        "vip",
        "breach",
        "ransomware",
    )
    score += sum(1 for keyword in priority_keywords if keyword in text)

    sender_domain = _extract_domain(sender)
    if sender_domain in {"enterprise.net", "retail-co.com"}:
        score += 1

    return max(1, min(5, score))


def apply_heuristics(subject: str, body: str, sender: str) -> HeuristicResult:
    combined = f"{subject}\n{body}".strip()
    domain = _extract_domain(sender)
    lower_text = combined.lower()

    is_spam = _contains_any(lower_text, SPAM_PATTERNS) or domain in DOMAIN_REPUTATION_BLOCKLIST
    is_security = _contains_any(lower_text, SECURITY_PATTERNS)
    is_legal = _contains_any(lower_text, LEGAL_PATTERNS)
    is_internal = domain.endswith("internal.com") or domain.endswith("mycompany.com")
    priority_score = score_priority(subject, body, sender)

    labels: list[str] = []
    if is_spam:
        labels.append("spam")
    if is_security:
        labels.append("security")
    if is_legal:
        labels.append("legal")
    if is_internal:
        labels.append("internal")
    labels.append(f"priority_{priority_score}")

    return HeuristicResult(
        is_spam=is_spam,
        is_security=is_security,
        is_legal=is_legal,
        is_internal=is_internal,
        priority_score=priority_score,
        labels=labels,
    )
