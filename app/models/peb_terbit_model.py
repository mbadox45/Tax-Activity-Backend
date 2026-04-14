# app/models/peb_terbit_model.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class PEBTerbit(Base):
    __tablename__ = "peb_terbit"

    id = Column(Integer, primary_key=True, index=True)

    peb_id = Column(Integer, ForeignKey("peb.id"), unique=True)
    masa_terbit = Column(String(20))  # contoh: "Mar 2026"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 RELATION
    peb = relationship("PEB", back_populates="terbit")
    user = relationship("User", back_populates="peb_terbits")