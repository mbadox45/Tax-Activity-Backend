# app/api/routes/document_sharing.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.models.user_model import User
from app.schemas.document_schema import DocumentResponse  # Pastikan schema ini sudah ada
from app.api.deps import get_current_user  
from app.core.security import get_accessible_documents  # Menggunakan logika filter sebelumnya
from app.core.response import success_response, error_response

router = APIRouter(prefix="/document-sharing", tags=["Document Sharing"])

# Dependency untuk menyediakan session database per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================================
# ROUTE: Load Accessible Documents (Owned & Shared)
# =========================================================================
@router.get("/shared")
def load_shared_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil semua dokumen yang berhak diakses oleh user yang sedang login.
    Logika penyaringan (Otorisasi) menggunakan fungsi terpusat get_accessible_documents.
    """
    try:
        # Jalankan fungsi filter query berdasarkan hak akses user saat ini
        documents = get_accessible_documents(db=db, current_user=current_user)
        
        # Karena success_response mengembalikan dict, FastAPI sekarang bebas merendernya tanpa komplain
        return success_response(data=documents, message="Dokumen berhasil dimuat.")
        
    except Exception as e:
        return error_response(
            message=f"Terjadi kesalahan saat memuat dokumen: {str(e)}", 
            code=500
        )