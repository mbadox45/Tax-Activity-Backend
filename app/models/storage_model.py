# app/models/storage_model.py
from sqlalchemy import Column, Integer, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserStorage(Base):
    __tablename__ = "user_storages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Menggunakan BigInteger (dalam bytes) agar akurat (1024^3 = 1GB)
    used_storage = Column(BigInteger, default=0) 
    max_storage = Column(BigInteger, default=104857600) # Default 100MB

    user = relationship("User", back_populates="storage")