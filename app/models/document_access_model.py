# app/models/document_access_model.py
from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base

class AccessLevel(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"

class DocumentAccess(Base):
    __tablename__ = "document_access"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    
    # Target sharing berbasis Group (NULL berarti Public / Semua User)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    
    access_level = Column(Enum(AccessLevel), default=AccessLevel.VIEWER)

    # Relationships (Menghubungkan ke Document dan Group)
    document = relationship("Document", back_populates="shared_with")
    group = relationship("Group", back_populates="shared_documents")