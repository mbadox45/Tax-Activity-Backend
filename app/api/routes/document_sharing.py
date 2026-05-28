# app/api/routes/document_sharing.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.group_model import Group
from app.models.document_model import Document
from app.models.document_access_model import DocumentAccess, AccessLevel 

from app.schemas.document_schema import DocumentResponse, UnifiedShareRequest 
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
# HELPER: Fungsi Rekursif Berbasis Group ID (Sangat Efisien)
# =========================================================================
def process_share_recursive(db: Session, doc: Document, payload: UnifiedShareRequest):
    """
    Menulis aturan hak akses baru langsung ke group_id (bukan user_id) 
    secara berantai ke seluruh anak folder.
    """
    # 1. Clear hak akses lama pada dokumen ini (Sync Mode)
    db.query(DocumentAccess).filter(DocumentAccess.document_id == doc.id).delete()
    
    # 2. Update flag di tabel dokumen utama
    if not payload.is_shared:
        doc.is_shared = False
        doc.share_with_all = False
    else:
        doc.is_shared = True
        
        # A. Opsi: Public Share (group_id diset NULL sesuai rancangan model)
        if payload.share_with_all:
            doc.share_with_all = True
            new_access = DocumentAccess(
                document_id=doc.id,
                group_id=None,  # NULL = Public Access
                access_level=AccessLevel.VIEWER
            )
            db.add(new_access)
            
        # B. Opsi: Group & Sub-group Sharing (Cukup simpan Group ID-nya saja!)
        if payload.group_ids:
            for gid in payload.group_ids:
                new_access = DocumentAccess(
                    document_id=doc.id,
                    group_id=gid,
                    access_level=AccessLevel.VIEWER  # Default akses grup adalah viewer
                )
                db.add(new_access)

    # 3. Rekursi Domino ke Sub-Folder / File di dalamnya
    if doc.is_folder:
        child_documents = db.query(Document).filter(Document.parent_id == doc.id).all()
        for child in child_documents:
            process_share_recursive(db=db, doc=child, payload=payload)


# =========================================================================
# 1. ROUTE: Load Accessible Documents (Owned & Shared)
# =========================================================================
@router.get("/shared")
def load_shared_documents(
    parent_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Mengambil daftar list dokumen yang berhak diakses user saat ini
        all_documents = get_accessible_documents(db=db, current_user=current_user)
        
        # Filter berdasarkan navigasi parent folder saat ini
        filtered_documents = [doc for doc in all_documents if doc.parent_id == parent_id]
        
        # Kelompokkan berkas agar frontend NextJS mudah melakukan rendering
        folders = [doc for doc in filtered_documents if doc.is_folder]
        files = [doc for doc in filtered_documents if not doc.is_folder]
        
        return success_response(
            data={
                "current_folder_id": parent_id,
                "folders": folders,
                "files": files
            }, 
            message="Dokumen dan folder berhasil dimuat."
        )
    except Exception as e:
        return error_response(message=f"Terjadi kesalahan saat memuat dokumen: {str(e)}", code=500)


# =========================================================================
# 2. ROUTE: Unified Share & Unshare Documents (Group Based)
# =========================================================================
@router.post("/share")
def unified_share_documents(
    payload: UnifiedShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validasi kepemilikan dokumen root yang ditembak oleh frontend
    root_documents = db.query(Document).filter(
        Document.id.in_(payload.document_ids),
        Document.user_id == current_user.id
    ).all()

    if not root_documents:
        return error_response(message="Dokumen tidak ditemukan atau Anda bukan pemilik dokumen ini", code=404)

    # 2. Validasi validitas Group IDs yang dikirimkan payload jika is_shared=True
    if payload.is_shared and payload.group_ids:
        valid_groups_count = db.query(Group.id).filter(Group.id.in_(payload.group_ids)).count()
        if valid_groups_count != len(payload.group_ids):
            return error_response(message="Ada satu atau beberapa Group ID yang tidak valid", code=400)

    try:
        # 3. Jalankan rekursi pemrosesan ke dalam database
        for doc in root_documents:
            process_share_recursive(db=db, doc=doc, payload=payload)
        
        # 4. Commit data jika seluruh proses rekursif selesai tanpa hambatan
        db.commit()
        
        status_action = "dibagikan" if payload.is_shared else "ditarik dari pembagian"
        return success_response(
            data=None,
            message=f"{len(root_documents)} item utama beserta sub-kontennya berhasil {status_action}."
        )

    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal mengubah status sharing grup: {str(e)}", code=500)