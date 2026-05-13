# app/core/security.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, UploadFile, status
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

async def check_storage_limit(db: Session, user_id: int, file: UploadFile, is_admin: bool = False):
    """
    Mengecek apakah penyimpanan user masih mencukupi untuk mengunggah file baru.
    Admin dikecualikan dari pengecekan ini.
    """
    # 1. Jika Admin, langsung izinkan tanpa cek kuota
    if is_admin:
        # Kita tetap ambil size agar return value konsisten (int)
        await file.seek(0, os.SEEK_END)
        file_size = await file.tell()
        await file.seek(0)
        return file_size

    # 2. Ambil ukuran file (dalam bytes)
    await file.seek(0, os.SEEK_END)
    file_size = await file.tell()
    await file.seek(0) # WAJIB agar file tidak korup/kosong saat disave

    # 3. Cari data storage user di database
    storage = db.query(UserStorage).filter(UserStorage.user_id == user_id).first()
    
    if not storage:
        storage = UserStorage(user_id=user_id)
        db.add(storage)
        db.commit()
        db.refresh(storage)

    # 4. Kalkulasi: Cek apakah melebihi limit
    if storage.used_storage + file_size > storage.max_storage:
        max_mb = round(storage.max_storage / (1024 * 1024), 2)
        used_mb = round(storage.used_storage / (1024 * 1024), 2)
        current_file_mb = round(file_size / (1024 * 1024), 2)
        
        raise HTTPException(
            status_code=400,
            detail=f"Penyimpanan penuh. Kuota: {max_mb}MB, Terpakai: {used_mb}MB. "
                   f"File Anda ({current_file_mb}MB) melebihi sisa kuota."
        )

    return file_size # Mengembalikan file_size untuk digunakan saat update DB nanti