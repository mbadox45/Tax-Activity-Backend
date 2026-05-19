# app/models/group_model.py

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base  # Sesuaikan dengan base class Anda

# =========================================================================
# TABEL RELASI (Association Table) untuk Sharing Dokumen ke Group/Sub-Group
# =========================================================================
document_group_sharing = Table(
    "document_group_sharing",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
)

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    
    # Hierarki: Self-referential untuk Sub-Group
    parent_id = Column(Integer, ForeignKey("groups.id", ondelete="RESTRICT"), nullable=True)

    # 🔴 PERBAIKAN: Hapus kondisi 'if parent_id' karena SQLAlchemy mengurusnya secara internal
    sub_groups = relationship(
        "Group", 
        backref="parent", 
        remote_side=[id],
        cascade="all, delete-orphan",
        single_parent=True
    )

    # Relasi ORM ke User (Satu Group/Sub-Group bisa memiliki banyak anggota User)
    users = relationship("User", back_populates="group")

    # Relasi ORM ke Dokumen yang dibagikan ke Group ini
    shared_documents = relationship(
        "Document",
        secondary=document_group_sharing,
        back_populates="shared_with_groups"
    )