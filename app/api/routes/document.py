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
@router.post("/folder", response_model=DocumentResponse)
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

# 🔹 UPLOAD FILE
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    parent_id: Optional[int] = Form(None),
    is_shared: bool = Form(False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Logika simpan file fisik
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    new_file = Document(
        name=file.filename,
        is_folder=False,
        is_shared=is_shared,
        file_path=file_path,
        file_type=file_ext,
        file_size=len(content),
        parent_id=parent_id,
        user_id=current_user.id
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file

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