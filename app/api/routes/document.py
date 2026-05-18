# app/api/routes/document.py

import os, uuid
import mimetypes
import zipfile
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.storage_model import UserStorage
from app.models.document_model import Document
from app.models.document_access_model import DocumentAccess, AccessLevel
from app.schemas.document_schema import DocumentCreate, DocumentResponse, DocumentMove, BulkDeleteRequest, BulkMoveRequest, BulkShareRequest, DocumentRename, DocumentShareRequest
from app.api.deps import get_current_user
from app.core.security import check_document_access, check_storage_limit
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
    files: List[UploadFile] = File(...), 
    parent_id: Optional[int] = Form(None),
    is_shared: bool = Form(False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Pastikan folder penyimpanan ada
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    actual_parent_id = None if parent_id == 0 else parent_id
    
    # --- LOGIKA PENGECEKAN STORAGE ---
    total_upload_size = 0
    file_sizes = [] 

    for file in files:
        # Panggilan fungsi sekarang lebih bersih tanpa parameter is_admin
        size = await check_storage_limit(
            db=db, 
            user_id=current_user.id, 
            file=file
        )
        total_upload_size += size
        file_sizes.append(size)

    # Re-kalkulasi total akumulasi semua file (Wajib untuk semua user)
    storage = db.query(UserStorage).filter(UserStorage.user_id == current_user.id).first()
    max_bytes = storage.max_storage if storage else 104857600 # Default 100MB jika kosong

    current_used_bytes = db.query(func.sum(Document.file_size)).filter(
        Document.user_id == current_user.id,
        Document.is_folder == False
    ).scalar() or 0

    if current_used_bytes + total_upload_size > max_bytes:
        max_mb = round(max_bytes / (1024 * 1024), 2)
        used_mb = round(current_used_bytes / (1024 * 1024), 2)
        upload_mb = round(total_upload_size / (1024 * 1024), 2)
        raise HTTPException(
            status_code=400, 
            detail=f"Total file ({upload_mb}MB) melebihi sisa kuota Anda. "
                   f"Terpakai: {used_mb}MB / Kuota: {max_mb}MB."
        )
    # --- END LOGIKA PENGECEKAN ---

    uploaded_records = []

    for index, file in enumerate(files):
        file_ext = file.filename.split(".")[-1] if "." in file.filename else ""
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)

        new_file = Document(
            name=file.filename,
            is_folder=False,
            is_shared=is_shared,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_sizes[index], 
            parent_id=actual_parent_id,
            user_id=current_user.id
        )
        db.add(new_file)
        uploaded_records.append(new_file)

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

# 🔹 RENAME DOCUMENT OR FOLDER
@router.put("/{document_id}/rename")
def rename_document(
    document_id: int,
    payload: DocumentRename,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Cari dokumen/folder berdasarkan ID dan kepemilikan
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        return error_response(message="Dokumen atau folder tidak ditemukan", code=404)

    # 2. Opsional: Validasi jika nama baru sama dengan nama lama (efisiensi)
    if document.name == payload.name:
        return success_response(data=document, message="Nama tetap sama")

    # 3. Simpan nama lama untuk keperluan pesan response
    old_name = document.name
    item_type = "Folder" if document.is_folder else "File"

    try:
        # 4. Update nama
        document.name = payload.name
        
        db.commit()
        db.refresh(document)

        return success_response(
            data=document,
            message=f"{item_type} '{old_name}' berhasil diubah menjadi '{document.name}'"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal mengubah nama: {str(e)}", code=500)

# 🔹 DOWNLOAD FILE
@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    has_access = check_document_access(db, document_id, current_user.id)

    if has_access is None:
        return error_response("Dokumen tidak ditemukan", 404)
    if has_access is False:
        return error_response("Anda tidak memiliki akses ke dokumen ini", 403)
        
    # 1. Cari dokumen di database
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    # 2. Validasi keberadaan dokumen
    if not document:
        return error_response(message="Dokumen tidak ditemukan", code=404)

    if document.is_folder:
        return error_response(message="Folder tidak dapat diunduh langsung sebagai file tunggal", code=400)

    # 3. Cek apakah file fisik benar-benar ada di storage
    # Pastikan document.file_path menyimpan path lengkap atau relatif yang benar
    file_path = document.file_path
    
    if not os.path.exists(file_path):
        return error_response(message="File fisik tidak ditemukan di server", code=404)

    # 4. Tentukan nama file yang akan muncul saat didownload
    # Kita ambil nama asli dari database (misal: "Laporan Pajak.pdf")
    download_name = document.name

    # 5. Kirim file sebagai response download
    return FileResponse(
        path=file_path, 
        filename=download_name,  # Ini yang menentukan nama file saat didownload
        media_type='application/octet-stream'
    )


# 🔹 DOWNLOAD FOLDER AS ZIP
@router.get("/{folder_id}/download-folder")
def download_folder_zip(
    folder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Cari folder utama
    root_folder = db.query(Document).filter(
        Document.id == folder_id,
        Document.user_id == current_user.id,
        Document.is_folder == True
    ).first()

    if not root_folder:
        return error_response(message="Folder tidak ditemukan", code=404)


    # 2. Buat file temporary untuk menyimpan ZIP
    # Kita gunakan tempfile agar tidak memenuhi storage permanen
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()

    try:
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            # Fungsi pembantu untuk menelusuri database secara rekursif
            def add_to_zip(current_folder_id, current_path=""):
                # Cari semua isi folder ini
                items = db.query(Document).filter(
                    Document.parent_id == current_folder_id,
                    Document.user_id == current_user.id
                ).all()

                for item in items:
                    # Tentukan path di dalam ZIP
                    # Misal: "Folder A/Subfolder B/file.pdf"
                    zip_entry_path = os.path.join(current_path, item.name)

                    if item.is_folder:
                        # Jika folder, buat entri folder dan telusuri isinya
                        zf.writestr(zip_entry_path + '/', '') # Menambahkan folder kosong
                        add_to_zip(item.id, zip_entry_path)
                    else:
                        # Jika file, cek keberadaan file fisik dan tambahkan ke ZIP
                        if item.file_path and os.path.exists(item.file_path):
                            zf.write(item.file_path, zip_entry_path)

            # Mulai proses rekursif dari folder utama
            add_to_zip(root_folder.id, root_folder.name)

        # 3. Kirim file ZIP dan hapus file temp setelah selesai dikirim
        # background_tasks memastikan file temp dihapus dari server setelah didownload
        background_tasks.add_task(os.remove, temp_zip_path)

        return FileResponse(
            path=temp_zip_path,
            filename=f"{root_folder.name}.zip",
            media_type="application/x-zip-compressed"
        )

    except Exception as e:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        return error_response(message=f"Gagal membuat ZIP: {str(e)}", code=500)

@router.post("/share-v2")
def share_documents_v2(
    payload: DocumentShareRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        # Loop dokumen yang ingin dibagikan
        for doc_id in payload.document_ids:
            # Validasi: Apakah user ini benar-benar owner? 
            # (Hanya owner yang boleh bagi-bagi akses)
            doc = db.query(Document).filter(
                Document.id == doc_id, 
                Document.user_id == current_user.id
            ).first()

            if not doc:
                continue # Skip jika bukan miliknya atau tidak ada

            # Bersihkan akses lama (Sync mode)
            db.query(DocumentAccess).filter(DocumentAccess.document_id == doc_id).delete()

            if payload.is_public:
                # Tambah akses publik (semua orang)
                new_access = DocumentAccess(
                    document_id=doc_id,
                    user_id=None,
                    access_level=AccessLevel.VIEWER
                )
                db.add(new_access)
            else:
                # Tambah akses spesifik user
                for member in payload.members:
                    new_access = DocumentAccess(
                        document_id=doc_id,
                        user_id=member.user_id,
                        access_level=member.access_level
                    )
                    db.add(new_access)

            # Update flag is_shared di tabel utama
            doc.is_shared = True if (payload.is_public or payload.members) else False

        db.commit()
        return success_response(data=None, message="Berhasil memperbarui hak akses")

    except Exception as e:
        db.rollback()
        return error_response(message=str(e), code=500)