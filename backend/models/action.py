from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    agent_reasoning_log = Column(JSONB)
    action_type = Column(String(100))
    proposed_content = Column(Text)
    is_approved = Column(Boolean, server_default=text("false"))
    approved_by = Column(String(255))
    executed_at = Column(DateTime(timezone=True))

    email = relationship("Email", back_populates="actions")