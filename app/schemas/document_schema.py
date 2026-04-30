# app/schemas/document_schema.py
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    name: str
    is_shared: bool = False
    parent_id: Optional[int] = None

class DocumentCreate(BaseModel):
    name: str
    is_shared: bool = False
    is_folder: bool = True
    parent_id: Optional[int] = None

    @field_validator('parent_id')
    @classmethod
    def validate_parent_id(cls, v):
        # Jika frontend mengirim 0 atau string kosong, ubah jadi None
        if v == 0:
            return None
        return v

class DocumentResponse(DocumentBase):
    id: int
    is_folder: bool
    file_type: Optional[str]
    file_size: Optional[int]
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentMove(BaseModel):
    parent_id: Optional[int] = None

class BulkDeleteRequest(BaseModel):
    document_ids: List[int]

class BulkMoveRequest(BaseModel):
    document_ids: List[int]
    target_folder_id: Optional[int] = None # Sesuaikan nama field di sini
    # is_shared: Optional[bool] = None # Tambahkan ini

class BulkShareRequest(BaseModel):
    document_ids: List[int]
    is_shared: bool