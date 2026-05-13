# app/api/routes/storage.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, is_admin
from app.models.storage_model import UserStorage
from app.core.response import success_response, error_response
from app.schemas.storage_schema import StorageResponse, StorageUpdateRequest

router = APIRouter(prefix="/storage", tags=["Storage Management"])

# 🔹 USER: Cek Sisa Kuota
@router.get("/me", response_model=StorageResponse)
def get_my_storage(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    storage = db.query(UserStorage).filter(UserStorage.user_id == current_user.id).first()
    
    if not storage:
        # Jika belum ada record (misal user lama), buatkan default
        storage = UserStorage(user_id=current_user.id)
        db.add(storage)
        db.commit()
        db.refresh(storage)

    result = {
        "user_id": storage.user_id,
        "used_storage_mb": round(storage.used_storage / (1024 * 1024), 2),
        "max_storage_mb": round(storage.max_storage / (1024 * 1024), 2),
        "percentage": round((storage.used_storage / storage.max_storage) * 100, 2)
    }

    return success_response(data=result, message="Storage info retrieved successfully", status_code=200)

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
    return success_response(message=f"Berhasil menambah {payload.additional_storage_mb}MB ke User {payload.user_id}", status_code=200)