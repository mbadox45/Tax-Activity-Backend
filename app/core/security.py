# app/core/security.py
import os
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException, UploadFile, status
from app.models.storage_model import UserStorage
from app.models.document_model import Document
from app.models.document_access_model import DocumentAccess, AccessLevel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

secret_key = settings.SECRET_KEY
algorithm = settings.ALGORITHM
access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

def check_document_access(db: Session, document_id: int, user_id: int, need_editor: bool = False):
    """
    Mengecek apakah user memiliki akses ke dokumen.
    1. Cek apakah user adalah owner.
    2. Cek apakah ada record di DocumentAccess (spesifik user atau public).
    """
    # 1. Cari dokumen
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None  # Indikasi dokumen tidak ditemukan

    # 2. Jika user adalah owner, berikan akses penuh (True)
    if doc.user_id == user_id:
        return True

    # 3. Cek tabel akses (Share)
    # Mencari akses yang ditujukan untuk user_id ini ATAU user_id IS NULL (Public)
    access = db.query(DocumentAccess).filter(
        DocumentAccess.document_id == document_id,
        or_(DocumentAccess.user_id == user_id, DocumentAccess.user_id == None)
    ).first()

    if not access:
        return False

    # 4. Jika butuh akses edit (need_editor=True), cek levelnya
    if need_editor and access.access_level != AccessLevel.EDITOR:
        return False

    return True

async def check_storage_limit(db: Session, user_id: int, file: UploadFile):
    """
    Mengecek apakah penyimpanan user masih mencukupi untuk mengunggah file baru.
    Aman dari masalah kompatibilitas fungsi seek().
    """
    # 1. Ambil ukuran file (dalam bytes) menggunakan properti bawaan FastAPI
    # Jika versi FastAPI Anda mendukung .size, gunakan itu. Jika tidak, gunakan len(content)
    file_size = getattr(file, "size", None)
    
    if file_size is None:
        # Jalur alternatif jika properti .size tidak tersedia di versi FastAPI Anda
        content = await file.read()
        file_size = len(content)
        await file.seek(0) # Kembalikan ke 0 agar saat di-route utama bisa dibaca ulang

    # 2. Cari batasan kuota (max_storage) user di database
    storage = db.query(UserStorage).filter(UserStorage.user_id == user_id).first()
    
    if not storage:
        storage = UserStorage(user_id=user_id)
        db.add(storage)
        db.commit()
        db.refresh(storage)

    # 3. Hitung TOTAL UKURAN FILE yang sudah ada di DB secara real-time
    current_used_bytes = db.query(func.sum(Document.file_size)).filter(
        Document.user_id == user_id,
        Document.is_folder == False
    ).scalar() or 0

    # 4. Kalkulasi: Cek apakah file baru ini akan melebihi limit?
    if current_used_bytes + file_size > storage.max_storage:
        max_mb = round(storage.max_storage / (1024 * 1024), 2)
        used_mb = round(current_used_bytes / (1024 * 1024), 2)
        current_file_mb = round(file_size / (1024 * 1024), 2)
        
        raise HTTPException(
            status_code=400,
            detail=f"Penyimpanan penuh. Kuota: {max_mb}MB, Terpakai: {used_mb}MB. "
                   f"File Anda ({current_file_mb}MB) melebihi sisa kuota."
        )

    return file_size