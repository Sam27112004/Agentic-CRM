from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, nullable=False)
    subject = Column(Text)
    sender_email = Column(String(255), ForeignKey("contacts.email"), nullable=False)
    first_seen_at = Column(DateTime(timezone=True))
    last_updated_at = Column(DateTime(timezone=True))
    status = Column(String(50), nullable=False, server_default="Open")
    assigned_to = Column(String(255))

    contact = relationship("Contact", back_populates="threads_sent")
    emails = relationship("Email", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_threads_sender_email", "sender_email"),
        Index("idx_threads_status", "status"),
    )