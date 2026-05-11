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
    
    # Kategori Sharing yang Anda minta
    is_shared = Column(Boolean, default=False) 
    
    # File metadata (Null jika ini adalah folder)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True) # e.g., 'pdf', 'docx', 'folder'
    file_size = Column(Integer, nullable=True) # dalam bytes

    # Hierarki Folder (Self-Referencing)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    owner = relationship("User", back_populates="documents")
    children = relationship("Document", backref="parent", remote_side=[id])
    shared_with = relationship("DocumentAccess", back_populates="document", cascade="all, delete-orphan")