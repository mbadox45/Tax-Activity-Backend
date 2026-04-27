# app/api/routes/document.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os, uuid

from app.db.session import get_db
from app.models.document_model import Document
from app.schemas.document_schema import DocumentCreate, DocumentResponse
from app.api.deps import get_current_user
from app.core.response import success_response, error_response

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = "uploads/documents"

# 🔹 CREATE FOLDER (Perbaikan)
@router.post("/folder")
def create_folder(
    data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    folder_data = data.model_dump()
    
    # 🔥 Pastikan parent_id 0 diubah menjadi None
    if folder_data.get("parent_id") == 0:
        folder_data["parent_id"] = None
        
    folder_data.pop("is_folder", None)

    new_folder = Document(
        **folder_data,
        is_folder=True,
        user_id=current_user.id,
        file_type="folder"
    )
    
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    return success_response(
        data=new_folder,
        message="Folder berhasil ditambahkan"
    )

# 🔹 UPLOAD FILE (Multiple Support)
@router.post("/upload") 
async def upload_document(
    files: List[UploadFile] = File(...), # Gunakan List dan ubah nama variabel jadi jamak
    parent_id: Optional[int] = Form(None),
    is_shared: bool = Form(False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Pastikan folder penyimpanan ada
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Handle parent_id 0 menjadi None
    actual_parent_id = None if parent_id == 0 else parent_id
    
    uploaded_records = []

    for file in files:
        # 1. Logika simpan file fisik
        file_ext = file.filename.split(".")[-1] if "." in file.filename else ""
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        # Baca konten file
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)

        # 2. Buat record database
        new_file = Document(
            name=file.filename,
            is_folder=False,
            is_shared=is_shared,
            file_path=file_path,
            file_type=file_ext,
            file_size=len(content),
            parent_id=actual_parent_id,
            user_id=current_user.id
        )
        db.add(new_file)
        uploaded_records.append(new_file)

    # 3. Commit semua sekaligus
    try:
        db.commit()
        for record in uploaded_records:
            db.refresh(record)
            
        return success_response(
            data=uploaded_records,
            message=f"{len(uploaded_records)} file berhasil diunggah"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal menyimpan data ke database: {str(e)}", code=500)

        
# 🔹 GET DOCUMENTS (LISTING)
@router.get("/") # Hapus response_model=List[DocumentResponse]
def get_documents(
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Jika frontend mengirim string "0", konversi ke None
    actual_parent_id = None if parent_id == 0 else parent_id

    result = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.parent_id == actual_parent_id
    ).all()

    return success_response(
        data=result,
        message="Load data berhasil"
    )


def delete_recursive(db: Session, document: Document):
    """
    Menghapus record di database dan file fisik di storage secara permanen.
    """
    if document.is_folder:
        # 1. Cari semua isi di dalam folder ini (sub-folder & file)
        children = db.query(Document).filter(Document.parent_id == document.id).all()
        for child in children:
            # Panggil fungsi ini secara rekursif untuk menghapus isi di dalamnya
            delete_recursive(db, child)
    else:
        # 2. Jika ini adalah FILE, hapus file fisiknya dari storage
        if document.file_path:
            # Cek apakah path file-nya ada di server
            if os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                except Exception as e:
                    # Log error jika gagal hapus file fisik, tapi tetap lanjut hapus record DB
                    print(f"Gagal menghapus file fisik: {document.file_path}. Error: {e}")

    # 3. Hapus record dari database
    db.delete(document)

# 🔹 DELETE ROUTE
@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        return error_response(message="Data tidak ditemukan", code=404)

    try:
        # Eksekusi penghapusan rekursif (File fisik + Database)
        delete_recursive(db, document)
        db.commit()
        
        return success_response(
            data=None,
            message="Data dan file fisik berhasil dihapus permanen"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal menghapus: {str(e)}", code=500)