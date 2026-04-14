# app/models/activity_model.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class ActivityCategory(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    category = Column(Enum(ActivityCategory), default=ActivityCategory.medium)
    description = Column(Text)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 RELATION
    logs = relationship("LogActivity", back_populates="activity", cascade="all, delete")
    user = relationship("User", back_populates="activities")