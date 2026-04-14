# app/models/peb_model.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import UniqueConstraint


from app.db.base import Base


class PEB(Base):
    __tablename__ = "peb"

    __table_args__ = (
        UniqueConstraint("document_number", name="uq_document_number"),
    )
    
    id = Column(Integer, primary_key=True, index=True)

    buyer_name = Column(String(100))
    buyer_address = Column(String(200))

    document_number = Column(String(50), index=True)
    document_date = Column(String(20))

    invoice = Column(String(100))
    invoice_date = Column(String(20))

    nilai_fob = Column(Float)
    nilai_tukar = Column(Float)
    file_path = Column(String(200))
    file_name = Column(String(100))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 RELATION
    terbit = relationship("PEBTerbit", back_populates="peb", uselist=False)
    user = relationship("User", back_populates="pebs")