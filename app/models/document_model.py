# app/models/document_model.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_folder = Column(Boolean, default=False)
    
    # Kategori Sharing
    is_shared = Column(Boolean, default=False) 
    
    # File metadata (Null jika ini adalah folder)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True) # e.g., 'pdf', 'docx'
    file_size = Column(Integer, nullable=True) # dalam bytes

    # Hierarki Folder (Self-Referencing)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    share_with_all = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =========================================================================
    # ORM RELATIONSHIPS
    # =========================================================================
    
    # Hubungan ke Pemilik Dokumen (User)
    owner = relationship("User", back_populates="documents")
    
    # Hubungan Struktur Folder (Parent-Child)
    children = relationship("Document", backref="parent", remote_side=[id])
    
    # 🔥 PUSAT OTORISASI: Jembatan menuju Group & Hak Aksesnya
    # Melalui relasi ini, kita bisa tahu Group mana saja yang membaca file ini
    shared_with = relationship(
        "DocumentAccess", 
        back_populates="document", 
        cascade="all, delete-orphan"
    )