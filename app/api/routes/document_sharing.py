# app/api/routes/document_sharing.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
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
# =========================================================================
# HELPER: Fungsi Rekursif Berbasis Group ID & Custom Access Level
# =========================================================================
def process_share_recursive(db: Session, doc: Document, payload: UnifiedShareRequest):
    """
    Menulis aturan hak akses baru ke group_id secara berantai ke seluruh anak folder,
    mendukung level akses dinamis (viewer/editor) dari payload objek.
    """
    # 1. Bersihkan seluruh hak akses lama pada dokumen ini (Sync Mode)
    db.query(DocumentAccess).filter(DocumentAccess.document_id == doc.id).delete()
    
    # 2. Update flag di tabel dokumen utama
    if not payload.is_shared:
        doc.is_shared = False
        doc.share_with_all = False
    else:
        doc.is_shared = True
        
        # A. Opsi: Public Share (group_id = None, default level = viewer)
        if payload.share_with_all:
            doc.share_with_all = True
            new_access = DocumentAccess(
                document_id=doc.id,
                group_id=None,  # NULL = Public Access
                access_level=AccessLevel.VIEWER
            )
            db.add(new_access)
            
        # B. Opsi: Group & Sub-group Sharing (Membaca list of objects)
        # ⚠️ PERBAIKAN: Melakukan iterasi terhadap objek, bukan lagi integer ID mentah
        if payload.group_ids:
            for group_item in payload.group_ids:
                new_access = DocumentAccess(
                    document_id=doc.id,
                    group_id=group_item.id,  # Mengambil ID dari property '.id' objek
                    access_level=group_item.access_level  # Menggunakan level dinamis ('viewer'/'editor')
                )
                db.add(new_access)

    # 3. REKURSI DOMINO: Jika item adalah FOLDER, turunkan aturan ke seluruh isinya
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
        # 👑 Cek apakah user adalah Super Admin
        is_super_admin = current_user.role == "super_admin"

        if is_super_admin:
            # -----------------------------------------------------------------
            # JALUR KHUSUS SUPER ADMIN:
            # Mengambil semua dokumen yang is_shared=True ATAU milik dia sendiri
            # -----------------------------------------------------------------
            accessible_documents = db.query(Document).filter(
                Document.parent_id == parent_id,
                Document.is_shared == True,
            ).all()
            
            # Super Admin otomatis mendapatkan akses EDITOR ke semua dokumen shared yang tampil
            document_access_map = {doc.id: "editor" for doc in accessible_documents}

        else:
            # -----------------------------------------------------------------
            # JALUR USER BIASA (Logika Otorisasi Grup Berbasis Level)
            # -----------------------------------------------------------------
            # 1. Kumpulkan semua Group ID yang relevan dengan user ini
            user_group_ids = []
            if current_user.group_id:
                user_group_ids.append(current_user.group_id)

            # 2. Ambil ID dokumen-dokumen yang di-share ke grup user atau publik
            access_records_query = db.query(DocumentAccess.document_id, DocumentAccess.access_level)
            if user_group_ids:
                access_records_query = access_records_query.filter(
                    or_(
                        DocumentAccess.group_id.in_(user_group_ids),
                        DocumentAccess.group_id.is_(None)
                    )
                )
            else:
                access_records_query = access_records_query.filter(DocumentAccess.group_id.is_(None))
            
            # Buat mapping dictionary { document_id: access_level } untuk pencarian cepat O(1)
            document_access_map = {rec.document_id: rec.access_level.value for rec in access_records_query.all()}

            # 3. Query Utama Dokumen untuk User Biasa
            accessible_documents = db.query(Document).filter(
                Document.parent_id == parent_id,
                Document.is_shared == True,
                or_(
                    Document.user_id == current_user.id,                    # Milik sendiri
                    Document.id.in_(list(document_access_map.keys())),      # Hasil share ke group
                    Document.share_with_all == True                         # Flag global public share
                )
            ).all()

        # -----------------------------------------------------------------
        # 3. PENYUSUNAN RESPONSE DATA & INJEKSI ACCESS LEVEL ITEM
        # -----------------------------------------------------------------
        folders = []
        files = []

        for doc in accessible_documents:
            doc_data = {
                "id": doc.id,
                "name": doc.name,
                "is_folder": doc.is_folder,
                "is_shared": doc.is_shared,
                "file_path": doc.file_path,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "parent_id": doc.parent_id,
                "user_id": doc.user_id,
                "share_with_all": doc.share_with_all,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                # Jika milik sendiri atau super_admin = 'editor', sisanya ambil dari map grup
                "access_level": "editor" if doc.user_id == current_user.id else document_access_map.get(doc.id, "viewer")
            }

            if doc.is_folder:
                folders.append(doc_data)
            else:
                files.append(doc_data)

        # -----------------------------------------------------------------
        # 4. TENTUKAN HAK AKSES UNTUK FOLDER AKTIF (CURRENT FOLDER)
        # -----------------------------------------------------------------
        current_folder_access_level = "viewer"  # Fallback aman
        
        if parent_id is None:
            # Jika berada di Root Directory shared, berikan hak editor agar bisa interaksi awal
            current_folder_access_level = "viewer" if not is_super_admin else "editor"
        elif is_super_admin:
            current_folder_access_level = "editor"
        else:
            current_folder = db.query(Document).filter(Document.id == parent_id).first()
            if current_folder:
                if current_folder.user_id == current_user.id:
                    current_folder_access_level = "editor"
                else:
                    current_folder_access_level = document_access_map.get(parent_id, "viewer")
        
        # 5. Return JSON terstruktur
        return success_response(
            data={
                "current_folder_id": parent_id,
                "current_folder_access_level": current_folder_access_level,
                "folders": folders,
                "files": files
            }, 
            message="Dokumen dan folder berhasil dimuat berdasarkan hak akses grup." if not is_super_admin 
                    else "Semua dokumen shared berhasil dimuat (Mode Super Admin)."
        )
        
    except Exception as e:
        return error_response(
            message=f"Terjadi kesalahan saat memuat dokumen: {str(e)}", 
            code=500
        )


# =========================================================================
# 2. ROUTE: Unified Share & Unshare Documents (Group Based)
# =========================================================================
@router.post("/share")
def unified_share_documents(
    payload: UnifiedShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    root_documents = db.query(Document).filter(
        Document.id.in_(payload.document_ids),
        Document.user_id == current_user.id
    ).all()

    if not root_documents:
        return error_response(message="Dokumen tidak ditemukan", code=404)

    # Validasi Group IDs (Mengekstrak ID dari list of objects)
    if payload.is_shared and payload.group_ids:
        extracted_ids = [g.id for g in payload.group_ids]
        valid_groups_count = db.query(Group.id).filter(Group.id.in_(extracted_ids)).count()
        if valid_groups_count != len(extracted_ids):
            return error_response(message="Ada Group ID yang tidak valid", code=400)

    try:
        for doc in root_documents:
            process_share_recursive(db=db, doc=doc, payload=payload)
        
        db.commit()
        return success_response(data=None, message="Status sharing berhasil diperbarui.")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), code=500)


@router.get("/{document_id}/detail")
def get_document_detail_with_sharing(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Ambil data dokumen utama beserta data User (owner) menggunakan Join
        query_result = db.query(Document, User).\
            join(User, Document.user_id == User.id).\
            filter(Document.id == document_id).first()
            
        if not query_result:
            return error_response(message="Dokumen tidak ditemukan", code=404)

        # Pecah hasil tuple query
        doc, owner = query_result

        # 👑 Cek status Super Admin
        is_super_admin = current_user.role == "super_admin"

        # 2. Logika Otorisasi Dasar: Apakah user ini berhak melihat detail dokumen ini?
        if not is_super_admin and doc.user_id != current_user.id and not doc.is_shared:
            return error_response(message="Anda tidak memiliki akses ke dokumen ini", code=403)

        # 3. Hitung Access Level untuk User yang sedang login saat ini
        current_user_access_level = "viewer"  # Default fallback
        
        if doc.user_id == current_user.id or is_super_admin:
            current_user_access_level = "editor"
        else:
            # Jika dokumen milik orang lain dan di-share, cek hak akses spesifik grup user ini
            user_group_ids = [current_user.group_id] if current_user.group_id else []
            
            if user_group_ids:
                specific_access = db.query(DocumentAccess).filter(
                    DocumentAccess.document_id == doc.id,
                    DocumentAccess.group_id.in_(user_group_ids)
                ).first()
                if specific_access:
                    current_user_access_level = specific_access.access_level.value

        # 4. Ambil Daftar Grup yang memiliki akses ke dokumen ini (Hanya jika is_shared = True)
        shared_groups_list = []
        
        if doc.is_shared:
            # Join dengan tabel Group untuk mengambil nama dan informasi grup secara lengkap
            access_records = db.query(DocumentAccess, Group).\
                join(Group, DocumentAccess.group_id == Group.id).\
                filter(DocumentAccess.document_id == doc.id).all()
                
            for access, group in access_records:
                shared_groups_list.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "access_level": access.access_level.value  # 'viewer' atau 'editor'
                })

        # 5. Susun Payload Output Secara Mendetail
        document_detail = {
            "id": doc.id,
            "name": doc.name,
            "is_folder": doc.is_folder,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "parent_id": doc.parent_id,
            
            # 👤 Informasi Pemilik Dokumen (Owner Info)
            "owner_id": doc.user_id,
            "owner_name": owner.name,  # 🔥 Penambahan Baru: Nama lengkap/username dari pemilik dokumen
            
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            
            # 🔒 Status Sharing Konten
            "is_shared": doc.is_shared,
            "share_with_all": doc.share_with_all,
            
            # 👤 Hak Akses User yang sedang menembak API saat ini
            "my_access_level": current_user_access_level,
            
            # 👥 Daftar Grup yang diberikan akses
            "shared_groups": shared_groups_list
        }

        return success_response(
            data=document_detail,
            message="Detail dokumen dan informasi pemilik berhasil dimuat."
        )

    except Exception as e:
        return error_response(
            message=f"Terjadi kesalahan saat memuat detail dokumen: {str(e)}", 
            code=500
        )