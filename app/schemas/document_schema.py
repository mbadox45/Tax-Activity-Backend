# app/schemas/document_schema.py
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from datetime import datetime
from app.models.document_access_model import AccessLevel

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

class DocumentRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ShareMember(BaseModel):
    user_id: Optional[int] = None # Jika None dan is_public True, maka untuk semua
    access_level: AccessLevel

class DocumentShareRequest(BaseModel):
    document_ids: List[int]
    is_public: bool = False
    members: List[ShareMember] = []

class BulkShareRequest(BaseModel):
    document_ids: List[int]
    is_shared: bool
    share_with_all: Optional[bool] = False  # True jika ingin dibagikan ke semua user aplikasi
    group_ids: Optional[List[int]] = []     # List ID Group/Sub-Group yang diberikan akses


# =========================================================================
# 🔥 TAMBAHAN BARU: SKEMA UNTUK ROUTE SHARE TERPADU (UNIFIED SHARE)
# =========================================================================

class GroupShareItem(BaseModel):
    """Skema untuk mendefinisikan user spesifik beserta level hak aksesnya"""
    id: int
    access_level: AccessLevel = AccessLevel.VIEWER

class UnifiedShareRequest(BaseModel):
    """
    Satu skema request untuk menghandle semua jenis pembagian dokumen:
    - Ke Semua Orang (Public)
    - Ke Group / Sub-group
    - Ke Spesifik User (Member kustom)
    - Serta proses Pembatalan Akses (Unshare)
    """
    document_ids: List[int]
    is_shared: bool  # True untuk membagikan, False untuk unshare (tarik akses)
    
    # Opsi Target 1: Semua Orang (Public)
    share_with_all: bool = False  
    
    # Opsi Target 2: Berdasarkan Group / Sub-group (Menggunakan ID Group)
    group_ids: List[GroupShareItem] = []  # List ID Group/Sub-group yang diberikan akses  