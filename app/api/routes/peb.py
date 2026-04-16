# app/api/routes/peb.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse # Tambah ini
from sqlalchemy.orm import Session
from typing import List
import uuid
import os

from app.db.session import get_db
from app.models.peb_model import PEB
from app.models.user_model import User
from app.api.deps import get_current_user
from app.core.response import success_response, error_response

# 🔥 OCR SERVICES (existing kamu)
from app.services.pdf_service import extract_pdf
from app.services.parser_service import parse_peb, parse_items
from app.utils.text_cleaner import clean_text

router = APIRouter(prefix="/peb", tags=["PEB"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =============================
# 🔹 HELPER
# =============================
def to_float(val):
    try:
        return float(val)
    except:
        return 0


# =========================================
# 🔹 CREATE PEB (UPLOAD + OCR + SAVE DB)
# =========================================
@router.post("/upload")
async def upload_peb(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = []

    for file in files:
        temp_path = None

        try:
            # =============================
            # TEMP FILE NAME
            # =============================
            temp_file_name = f"temp_{uuid.uuid4()}_{file.filename}"
            temp_path = os.path.join(UPLOAD_DIR, temp_file_name)

            # =============================
            # SAVE TEMP FILE
            # =============================
            with open(temp_path, "wb") as f:
                f.write(await file.read())

            # =============================
            # OCR PROCESS
            # =============================
            text, tables = extract_pdf(temp_path)
            text = clean_text(text)

            items = parse_items(tables)
            header = parse_peb(text, items)

            # =============================
            # DOCUMENT NUMBER
            # =============================
            nomor_daftar = header.get("nomor_pendaftaran")
            nomor_aju = header.get("nomor_pengajuan")

            document_number = None
            if nomor_daftar and nomor_aju:
                document_number = f"{nomor_daftar}#{nomor_aju}"
            else:
                document_number = nomor_daftar or nomor_aju

            # =============================
            # DUPLICATE CHECK
            # =============================
            existing = db.query(PEB).filter(
                PEB.document_number == document_number
            ).first()

            if existing:
                results.append({
                    "file_name": file.filename,
                    "status": "duplicate",
                    "document_number": document_number
                })

                # 🔥 HAPUS FILE TEMP
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                continue

            # =============================
            # FINAL FILE NAME
            # =============================
            final_file_name = f"{uuid.uuid4()}_{file.filename}"
            final_path = os.path.join(UPLOAD_DIR, final_file_name)

            # pindahkan file dari temp → final
            os.rename(temp_path, final_path)

            # =============================
            # MAPPING DATA
            # =============================
            nilai_fob = to_float(header.get("nilai_fob"))/100
            nilai_tukar = to_float(header.get("nilai_tukar"))/100

            peb = PEB(
                buyer_name=header.get("nama_pembeli"),
                buyer_address=header.get("alamat_pembeli"),

                document_number=document_number,
                document_date=header.get("tanggal_peb"),

                invoice=header.get("invoice"),
                invoice_date=None,

                nilai_fob=nilai_fob,
                nilai_tukar=nilai_tukar,

                file_path=final_path,
                file_name=final_file_name,

                user_id=current_user.id
            )

            db.add(peb)
            db.commit()
            db.refresh(peb)

            results.append({
                "id": peb.id,
                "file_name": peb.file_name,
                "document_number": peb.document_number,
                "status": "success"
            })

        except Exception as e:
            # 🔥 CLEANUP kalau error
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": str(e)
            })

    return success_response(
        data=results,
        message="Berhasil upload & parsing PEB"
    )


# =========================================
# 🔹 GET ALL PEB
# =========================================
@router.get("/")
def get_peb(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pebs = db.query(PEB).all()

    return success_response(
        data=[
            {
                "id": p.id,
                "buyer_name": p.buyer_name,
                "buyer_address": p.buyer_address,
                "document_number": p.document_number,
                "document_date": p.document_date,
                "invoice": p.invoice,
                "nilai_fob": p.nilai_fob,
                "nilai_tukar": p.nilai_tukar,
                "file_name": p.file_name,
                "created_at": p.created_at
            }
            for p in pebs
        ],
        message="Success"
    )

# =========================================
# 🔹 VIEW / DOWNLOAD PDF
# =========================================
@router.get("/{peb_id}/view")
async def view_peb_pdf(
    peb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Cari data di DB
    peb = db.query(PEB).filter(PEB.id == peb_id).first()

    if not peb:
        return error_response("Data PEB tidak ditemukan", 404)

    # 2. Cek apakah file fisik ada di storage
    if not peb.file_path or not os.path.exists(peb.file_path):
        return error_response("File fisik tidak ditemukan di server", 404)

    # 3. Return FileResponse
    # media_type="application/pdf" memaksa browser membuka viewer PDF bawaan
    return FileResponse(
        path=peb.file_path,
        filename=peb.file_name,
        media_type="application/pdf"
    )

# =========================================
# 🔹 UPDATE PEB
# =========================================
@router.put("/{peb_id}")
def update_peb(
    peb_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    peb = db.query(PEB).filter(
        PEB.id == peb_id,
    ).first()

    if not peb:
        return error_response("Data PEB tidak ditemukan", 404)

    for key, value in payload.items():
        if hasattr(peb, key):
            setattr(peb, key, value)

    db.commit()
    db.refresh(peb)

    return success_response(
        data={"id": peb.id},
        message="PEB berhasil diupdate"
    )


# =========================================
# 🔹 DELETE PEB
# =========================================
@router.delete("/{peb_id}")
def delete_peb(
    peb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        return error_response("Akses ditolak (admin only)", 403)

    
    peb = db.query(PEB).filter(
        PEB.id == peb_id,
    ).first()

    if not peb:
        return error_response("Data tidak ditemukan", 404)

    # =============================
    # 🔥 DELETE FILE
    # =============================
    if peb.file_path and os.path.exists(peb.file_path):
        try:
            os.remove(peb.file_path)
        except Exception as e:
            # optional: log error, tapi jangan gagalkan delete DB
            print(f"Gagal hapus file: {e}")

    # =============================
    # DELETE DB
    # =============================
    db.delete(peb)
    db.commit()

    return success_response(
        message="PEB berhasil dihapus"
    )