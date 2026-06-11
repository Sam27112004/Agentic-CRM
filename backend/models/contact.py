from sqlalchemy import Column, DateTime, Integer, Numeric, String, func, text
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    company = Column(String(255))
    status = Column(String(50), nullable=False, server_default=text("'Active'"))
    account_value = Column(Numeric(12, 2))
    churn_risk_score = Column(Numeric(3, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_contact_at = Column(DateTime(timezone=True))

    threads_sent = relationship("Thread", back_populates="contact", cascade="all, delete-orphan")