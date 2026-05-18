# app/api/routes/storage.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, is_admin
from app.models.storage_model import UserStorage
from app.models.document_model import Document
from app.core.response import success_response, error_response
from app.schemas.storage_schema import StorageResponse, StorageUpdateRequest

router = APIRouter(prefix="/storage", tags=["Storage Management"])

# 🔹 USER: Cek Sisa Kuota
@router.get("/me") 
def get_my_storage(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # 1. Ambil batasan max_storage dari tabel UserStorage
    storage = db.query(UserStorage).filter(UserStorage.user_id == current_user.id).first()
    
    if not storage:
        # Jika belum ada record limit, buatkan dengan default (100MB)
        storage = UserStorage(user_id=current_user.id)
        db.add(storage)
        db.commit()
        db.refresh(storage)

    # 2. Hitung TOTAL UKURAN FILE langsung dari tabel Document milik user ini
    # Hanya hitung yang 'is_folder=False' (karena folder ukurannya 0/tidak punya file fisik)
    total_used = db.query(func.sum(Document.file_size)).filter(
        Document.user_id == current_user.id,
        Document.is_folder == False
    ).scalar()

    # Jika user belum pernah upload file sama sekali, func.sum akan menghasilkan None, ubah ke 0
    used_bytes = total_used or 0
    max_bytes = storage.max_storage or 104857600 # default 100MB jika null
    
    result = {
        "user_id": storage.user_id,
        "used_storage_bytes": used_bytes,
        "max_storage_bytes": max_bytes,
        "percentage": round((used_bytes / max_bytes) * 100, 2) if max_bytes > 0 else 0.0
    }

    return success_response(data=result, message="Storage info retrieved successfully")

# 🔹 ADMIN: Tambah Kuota User
@router.post("/add-quota")
def add_user_quota(
    payload: StorageUpdateRequest, 
    db: Session = Depends(get_db), 
    current_admin = Depends(is_admin) # Hanya admin yang bisa akses
):
    storage = db.query(UserStorage).filter(UserStorage.user_id == payload.user_id).first()
    
    if not storage:
        return error_response(message="User storage record not found", status_code=404)

    # Konversi MB ke Bytes
    additional_bytes = payload.additional_storage_mb * 1024 * 1024
    storage.max_storage += additional_bytes
    
    db.commit()
    return success_response(message=f"Berhasil menambah {payload.additional_storage_mb}MB ke User {payload.user_id}")