# app/schemas/group.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Schema untuk Input data (Create / Update)
class GroupCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None  # NULL jika Group Utama, isi ID jika Sub-Group

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None

# Schema untuk Output data (Response)
class GroupResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

# Schema khusus untuk menampilkan struktur pohon (Group + Anak-anak SubGroup-nya)
class GroupTreeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # 🔥 Kunci rekursif: Menampung list sub-group di bawahnya
    # Pastikan nama atribut 'children' ini sama dengan backref/relationship di model SQLAlchemy Group Anda
    sub_groups: List['GroupTreeResponse'] = []

    class Config:
        # Pydantic v2 menggunakan from_attributes, v1 menggunakan orm_mode = True
        from_attributes = True