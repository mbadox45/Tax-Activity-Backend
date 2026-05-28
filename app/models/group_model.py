# app/models/group_model.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from app.db.base import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    
    # Hierarki: Self-referential untuk Sub-Group
    parent_id = Column(Integer, ForeignKey("groups.id", ondelete="RESTRICT"), nullable=True)

    # Relasi Hierarki Internal
    sub_groups = relationship(
        "Group",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        single_parent=True
    )

    # Relasi ke User (Anggota di dalam grup ini)
    users = relationship("User", back_populates="group")

    # 🔥 RELASI KE AKSES DOKUMEN: Berpasangan dengan 'group' di DocumentAccess
    shared_documents = relationship(
        "DocumentAccess",
        back_populates="group",
        cascade="all, delete-orphan"
    )