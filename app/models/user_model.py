# app/models/user_model.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)
    role = Column(String(50), default="user", nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)

    # RELATIONS
    activities = relationship(
        "Activity",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    log_activities = relationship(
        "LogActivity",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    pebs = relationship(
        "PEB",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    peb_terbits = relationship(   # ✅ plural
        "PEBTerbit",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    documents = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    storage = relationship(
        "UserStorage",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    group = relationship("Group", back_populates="users")
