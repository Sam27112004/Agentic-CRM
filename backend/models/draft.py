from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, server_default="Pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))

    email = relationship("Email", back_populates="drafts")

    __table_args__ = (Index("idx_drafts_email_id", "email_id"),)