# app/api/routes/document_sharing.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import SessionLocal
from app.models.user_model import User
from app.schemas.document_schema import DocumentResponse 
from app.api.deps import get_current_user  
from app.core.security import get_accessible_documents 
from app.core.response import success_response, error_response

router = APIRouter(prefix="/document-sharing", tags=["Document Sharing"])

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
    parent_id: Optional[int] = None, # 📂 Filter untuk navigasi masuk-keluar folder
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil semua dokumen (Milik Sendiri & Shared) yang berhak diakses oleh user saat ini,
    dikelompokkan berdasarkan struktur Folder dan File agar sesuai dengan sistem Load Document utama.
    """
    try:
        # 1. Ambil data list dokumen yang berhak diakses dari fungsi keamanan
        all_documents = get_accessible_documents(db=db, current_user=current_user)
        
        # 2. Lakukan filtering berbasis Python List (mengatasi error 'list' object has no attribute 'filter')
        # Kita hanya mengambil dokumen yang parent_id-nya cocok dengan posisi navigasi user saat ini
        filtered_documents = [
            doc for doc in all_documents 
            if doc.parent_id == parent_id
        ]
        
        # 3. Pisahkan hasil filter ke dalam kelompok Folders dan Files
        folders = [doc for doc in filtered_documents if doc.is_folder]
        files = [doc for doc in filtered_documents if not doc.is_folder]
        
        # 4. Kemas response agar identik dengan struktur load_documents bawaan Anda
        result_data = {
            "current_folder_id": parent_id,
            "folders": folders,
            "files": files
        }
        
        return success_response(
            data=result_data, 
            message="Dokumen dan folder berhasil dimuat."
        )
        
    except Exception as e:
        return error_response(
            message=f"Terjadi kesalahan saat memuat dokumen: {str(e)}", 
            code=500
        )