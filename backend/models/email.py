from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    message_id = Column(String(255), unique=True, nullable=False)
    sender = Column(String(255), nullable=True)
    subject = Column(Text)
    body = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    sentiment_score = Column(Numeric(4, 2))
    category = Column(String(100))
    urgency = Column(String(50))
    requires_human = Column(Boolean)
    confidence = Column(Numeric(4, 2))
    raw_entities = Column(JSONB)
    status = Column(String(50), nullable=False, server_default="Received")

    thread = relationship("Thread", back_populates="emails")
    actions = relationship("Action", back_populates="email", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="email", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="email", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_emails_thread_id", "thread_id"),
        Index("idx_emails_sender", "sender"),
        Index("idx_emails_sentiment_score", "sentiment_score"),
        Index("idx_emails_timestamp", "timestamp"),
    )