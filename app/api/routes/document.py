# app/api/routes/document.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os, uuid
import mimetypes

from app.db.session import get_db
from app.models.document_model import Document
from app.schemas.document_schema import DocumentCreate, DocumentResponse, DocumentMove, BulkDeleteRequest, BulkMoveRequest, BulkShareRequest
from app.api.deps import get_current_user
from app.core.response import success_response, error_response

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = "uploads/documents"

@router.get("/{document_id}/view")
async def view_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Cari dokumen di database
    document = db.query(Document).filter(
        Document.id == document_id,
        # Document.user_id == current_user.id
    ).first()

    if not document:
        return error_response(message="File tidak ditemukan", code=404)

    if document.user_id != current_user.id and not document.is_shared:
        return error_response(message="Anda tidak memiliki akses ke file ini", code=403)

    file_path = document.file_path
    if not os.path.exists(file_path):
        return error_response(message="File fisik tidak ditemukan di server", code=404)

    # 2. Identifikasi tipe file berdasarkan ekstensi atau content
    mime_type, _ = mimetypes.guess_type(file_path)
    extension = document.file_type.lower()

    # --- LOGIKA KONVERSI (Word/Text ke PDF) ---
    if extension in ['doc', 'docx', 'txt', 'rtf']:
        
        if extension == 'txt':
            return FileResponse(file_path, media_type="text/plain", filename=document.name)
        
        return FileResponse(file_path, media_type="application/msword", filename=document.name)

    # --- LOGIKA IMAGE ---
    if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        return FileResponse(file_path, media_type=mime_type or "image/jpeg")

    # --- LOGIKA PDF ---
    if extension == 'pdf':
        return FileResponse(file_path, media_type="application/pdf")

    # --- LOGIKA AUDIO & VIDEO ---
    if extension in ['mp4', 'webm', 'ogg', 'mov']:
        return FileResponse(file_path, media_type="video/mp4")
    
    if extension in ['mp3', 'wav', 'flac']:
        return FileResponse(file_path, media_type="audio/mpeg")

    # Default: Kirim file apa adanya (inline)
    return FileResponse(
        file_path, 
        media_type=mime_type or "application/octet-stream",
        filename=document.name
    )

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

# 🔹 BULK DELETE DOCUMENTS/FOLDERS
@router.post("/bulk-delete") # Menggunakan POST karena membawa body list ID
def bulk_delete_documents(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Cari semua dokumen yang dimiliki user berdasarkan list ID yang dikirim
    documents = db.query(Document).filter(
        Document.id.in_(payload.document_ids),
        Document.user_id == current_user.id
    ).all()

    if not documents:
        return error_response(message="Tidak ada dokumen yang ditemukan untuk dihapus", code=404)

    try:
        count = 0
        for doc in documents:
            # Menggunakan fungsi rekursif yang sudah kita buat sebelumnya
            # Ini memastikan file fisik terhapus dan sub-folder ikut bersih
            delete_recursive(db, doc)
            count += 1
        
        db.commit()
        
        return success_response(
            data=None,
            message=f"{count} item berhasil dihapus secara permanen"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal melakukan penghapusan bulk: {str(e)}", code=500)

# 🔹 MOVE DOCUMENTS/FOLDERS
@router.put("/{document_id}/move")
def move_document(
    document_id: int,
    payload: DocumentMove,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Cari dokumen/folder yang ingin dipindahkan
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        return error_response(message="Dokumen tidak ditemukan", code=404)

    # 2. Tangani jika pindah ke Root (parent_id = 0 atau None)
    target_parent_id = None if payload.parent_id == 0 else payload.parent_id

    # 3. Validasi folder tujuan (jika bukan root)
    if target_parent_id:
        target_folder = db.query(Document).filter(
            Document.id == target_parent_id,
            Document.user_id == current_user.id
        ).first()

        if not target_folder:
            return error_response(message="Folder tujuan tidak ditemukan", code=404)
        
        if not target_folder.is_folder:
            return error_response(message="Target harus berupa folder, bukan file", code=400)

        # 4. Validasi rekursif: Jangan biarkan folder pindah ke dalam dirinya sendiri atau sub-foldernya
        if document.is_folder and target_parent_id == document.id:
            return error_response(message="Tidak dapat memindahkan folder ke dalam dirinya sendiri", code=400)

    # 5. Update parent_id
    document.parent_id = target_parent_id
    
    try:
        db.commit()
        db.refresh(document)
        return success_response(
            data=document,
            message=f"{'Folder' if document.is_folder else 'File'} berhasil dipindahkan"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal memindahkan: {str(e)}", code=500)

# 🔹 BULK MOVE DOCUMENTS (Fixed Version)
@router.post("/bulk-move")
def bulk_move_documents(
    payload: BulkMoveRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Ambil nilai dari target_folder_id sesuai JSON yang Anda kirim
    raw_target_id = payload.target_folder_id
    
    # Logika: Jika 0 atau None maka pindah ke Root
    target_id = None if raw_target_id == 0 or raw_target_id is None else raw_target_id

    # 1. Validasi jika pindah ke folder tertentu (bukan root)
    if target_id is not None:
        target_folder = db.query(Document).filter(
            Document.id == target_id,
            Document.user_id == current_user.id,
            Document.is_folder == True
        ).first()

        if not target_folder:
            return error_response(message=f"Folder tujuan ID {target_id} tidak ditemukan", code=404)

    # 2. Ambil dokumen yang akan dipindahkan
    documents = db.query(Document).filter(
        Document.id.in_(payload.document_ids),
        Document.user_id == current_user.id
    ).all()

    if not documents:
        return error_response(message="Dokumen tidak ditemukan", code=404)

    try:
        moved_count = 0
        for doc in documents:
            # Cegah folder pindah ke dirinya sendiri
            if doc.is_folder and doc.id == target_id:
                continue
                
            doc.parent_id = target_id
            moved_count += 1
        
        db.commit()
        
        return success_response(
            data=None,
            message=f"{moved_count} item berhasil dipindahkan ke {'Root' if target_id is None else 'Folder ID ' + str(target_id)}"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal memindahkan: {str(e)}", code=500)


def update_share_recursive(db: Session, document: Document, is_shared: bool):
    """
    Mengubah status is_shared pada dokumen dan semua turunannya secara rekursif.
    """
    # 1. Update dokumen itu sendiri
    document.is_shared = is_shared
    
    # 2. Jika dokumen adalah folder, cari semua anak-anaknya
    if document.is_folder:
        children = db.query(Document).filter(Document.parent_id == document.id).all()
        for child in children:
            update_share_recursive(db, child, is_shared)

# 🔹 BULK SHARE / UNSHARE (Recursive Version)
@router.post("/share")
def bulk_share_documents(
    payload: BulkShareRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Cari dokumen utama yang dipilih user
    documents = db.query(Document).filter(
        Document.id.in_(payload.document_ids),
        Document.user_id == current_user.id
    ).all()

    if not documents:
        return error_response(message="Dokumen tidak ditemukan", code=404)

    try:
        for doc in documents:
            # Panggil fungsi rekursif untuk memastikan turunannya ikut ter-update
            update_share_recursive(db, doc, payload.is_shared)
        
        db.commit()
        
        action = "dibagikan" if payload.is_shared else "berhenti dibagikan"
        return success_response(
            data=None,
            message=f"{len(documents)} item beserta isinya berhasil {action}"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal mengubah status sharing: {str(e)}", code=500)

# 🔹 GET ALL SHARED DOCUMENTS (Public/Shared Files)
@router.get("/shared-with-me")
def get_shared_documents(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Mengambil semua dokumen yang is_shared=True 
    # DAN bukan milik user yang sedang login (untuk fitur Shared with Me)
    result = db.query(Document).filter(
        Document.is_shared == True,
        Document.user_id != current_user.id
    ).all()

    return success_response(
        data=result,
        message="Daftar file yang dibagikan berhasil dimuat"
    )