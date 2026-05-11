from sqlalchemy.orm import Session
from sqlalchemy import or_
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