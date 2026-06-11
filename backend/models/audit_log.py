from sqlalchemy import Column, DateTime, Integer, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    action = Column(String(255))
    performed_by = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    diff = Column(JSONB)

    __table_args__ = (Index("idx_audit_log_entity", "entity_type", "entity_id"),)