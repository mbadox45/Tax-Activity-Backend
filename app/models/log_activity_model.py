# app/models/log_activity_model.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class ActivityStatus(str, enum.Enum):
    pending = "pending"
    on_progress = "on_progress"
    cancel = "cancel"
    done = "done"


class LogActivity(Base):
    __tablename__ = "log_activities"

    id = Column(Integer, primary_key=True, index=True)

    activity_id = Column(Integer, ForeignKey("activities.id"))

    status = Column(Enum(ActivityStatus), nullable=False)
    keterangan = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 RELATION
    activity = relationship("Activity", back_populates="logs")
    user = relationship("User", back_populates="log_activities")