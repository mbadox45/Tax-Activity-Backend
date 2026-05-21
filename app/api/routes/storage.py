# app/api/routes/storage.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, is_admin
from app.models.user_model import User  # Pastikan mengimpor model User Anda
from app.models.storage_model import UserStorage
from app.models.document_model import Document
from app.core.response import success_response, error_response
from app.schemas.storage_schema import StorageResponse, StorageUpdateRequest

router = APIRouter(prefix="/storage", tags=["Storage Management"])

# 🔹 ADMIN: Get All Users Storage (Melihat kuota & pemakaian seluruh user)
@router.get("/users")
def get_all_users_storage(
    db: Session = Depends(get_db),
    current_admin = Depends(is_admin) # Hanya bisa diakses admin
):
    # 1. Subquery untuk menghitung total pemakaian per user secara efisien
    usage_subquery = (
        db.query(
            Document.user_id.label("user_id"),
            func.sum(Document.file_size).label("total_used")
        )
        .filter(Document.is_folder == False)
        .group_by(Document.user_id)
        .subquery()
    )

    # 2. Join utama: User + UserStorage + Subquery Pemakaian Dokumen
    # Menggunakan outerjoin agar user yang belum punya file/record storage tetap muncul
    results = (
        db.query(
            User.id.label("id"),
            User.name.label("name"),
            User.username.label("username"),
            UserStorage.max_storage.label("max_storage"),
            usage_subquery.c.total_used.label("used_storage")
        )
        .outerjoin(UserStorage, User.id == UserStorage.user_id)
        .outerjoin(usage_subquery, User.id == usage_subquery.c.user_id)
        .all()
    )

    # 3. Mapping data hasil query ke format JSON response
    storage_list = []
    for r in results:
        used_bytes = r.used_storage or 0
        max_bytes = r.max_storage or 104857600  # Default 100MB jika belum ada record di UserStorage
        
        storage_list.append({
            "user_id": r.id,
            "name": r.name,
            "username": r.username,
            "used_storage_bytes": used_bytes,
            "max_storage_bytes": max_bytes,
            "percentage": round((used_bytes / max_bytes) * 100, 2) if max_bytes > 0 else 0.0
        })

    return success_response(
        data=storage_list, 
        message="All users storage info retrieved successfully"
    )


# 🔹 USER: Cek Sisa Kuota Sendiri
@router.get("/me") 
def get_my_storage(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    storage = db.query(UserStorage).filter(UserStorage.user_id == current_user.id).first()
    
    if not storage:
        storage = UserStorage(user_id=current_user.id)
        db.add(storage)
        db.commit()
        db.refresh(storage)

    total_used = db.query(func.sum(Document.file_size)).filter(
        Document.user_id == current_user.id,
        Document.is_folder == False
    ).scalar()

    used_bytes = total_used or 0
    max_bytes = storage.max_storage or 104857600 
    
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
    current_admin = Depends(is_admin)
):
    storage = db.query(UserStorage).filter(UserStorage.user_id == payload.user_id).first()
    
    # Perbaikan: Jika admin mau tambah kuota tapi user belum punya record storage, otomatis buatkan baru
    if not storage:
        storage = UserStorage(user_id=payload.user_id, max_storage=104857600) # Mulai dari default 100MB
        db.add(storage)

    # Konversi MB ke Bytes
    additional_bytes = payload.additional_storage_mb * 1024 * 1024
    storage.max_storage += additional_bytes
    
    db.commit()
    return success_response(message=f"Berhasil menambah {payload.additional_storage_mb}MB ke User {payload.user_id}")