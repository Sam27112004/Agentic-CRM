from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_doc = Column(String(255))
    chunk_text = Column(Text)
    embedding = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())