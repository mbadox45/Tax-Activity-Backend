# app/schemas/group.py
from pydantic import BaseModel
from typing import Optional, List

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
    parent_id: Optional[int] = None
    is_active: bool
    sub_groups: List["GroupTreeResponse"] = []  # Relasi rekursif ke dirinya sendiri

    class Config:
        from_attributes = True