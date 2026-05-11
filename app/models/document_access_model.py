from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, Enum
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
    
    # Jika user_id NULL, berarti ini akses "All Users" (Public)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    access_level = Column(Enum(AccessLevel), default=AccessLevel.VIEWER)

    # Relationships
    document = relationship("Document", back_populates="shared_with")
    user = relationship("User", back_populates="shared_documents")