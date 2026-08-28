# app/api/routes/peb.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Response
from fastapi.responses import FileResponse # Tambah ini
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, date
import uuid
import os

from app.db.session import get_db
from app.models.peb_model import PEB
from app.models.peb_terbit_model import PEBTerbit
from app.models.user_model import User
from app.api.deps import get_current_user
from app.core.response import success_response, error_response
from app.schemas.peb_schema import PEBResponse, BulkDeleteRequest

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
@router.post("/upload")
async def upload_peb(
    files: List[UploadFile] = File(...),
    masa_terbit: str = Form("Mar 2026"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = []

    for file in files:
        temp_path = None

        try:
            # 1. Simpan ke TEMP
            temp_file_name = f"temp_{uuid.uuid4()}_{file.filename}"
            temp_path = os.path.join(UPLOAD_DIR, temp_file_name)
            with open(temp_path, "wb") as f:
                f.write(await file.read())

            # 2. OCR & Parsing (Gunakan file di temp_path)
            text, tables = extract_pdf(temp_path)
            header = parse_peb(clean_text(text), parse_items(tables))

            # 3. Tentukan Document Number
            nomor_daftar = header.get("nomor_pendaftaran")
            nomor_aju = header.get("nomor_pengajuan")
            document_number = f"{nomor_daftar}#{nomor_aju}" if nomor_daftar and nomor_aju else (nomor_daftar or nomor_aju)

            # ======================================================
            # 🔥 4. DUPLICATE CHECK (LAKUKAN DI SINI)
            # ======================================================
            existing = db.query(PEB).filter(PEB.document_number == document_number).first()

            if existing:
                if os.path.exists(temp_path):
                    os.remove(temp_path) # Hapus temp agar tidak jadi sampah
                
                results.append({
                    "file_name": file.filename,
                    "status": "duplicate",
                    "document_number": document_number
                })
                continue # Lanjut

            # 5. PINDAHKAN FILE KE FINAL (Hanya jika lolos cek duplikat)
            final_file_name = f"{uuid.uuid4()}_{file.filename}"
            final_path = os.path.join(UPLOAD_DIR, final_file_name)
            os.rename(temp_path, final_path)

            # 6. Database Transaction
            try:
                # =============================
                # MAPPING DATA
                # =============================
                nilai_fob = to_float(header.get("nilai_fob"))/100
                nilai_tukar = to_float(header.get("nilai_tukar"))/100

                # Insert PEB
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
                db.flush()

                # Insert PEB_Terbit
                new_terbit = PEBTerbit(
                    peb_id=peb.id,          # ID dari proses flush di atas
                    masa_terbit=masa_terbit, # Diambil dari input "Mar 2026"       # Status awal
                    user_id=current_user.id
                )
                db.add(new_terbit)

                db.commit()
                # db.refresh(peb)

                results.append({
                    "id": peb.id,
                    "file_name": peb.file_name,
                    "document_number": peb.document_number,
                    "masa_terbit": masa_terbit,
                    "status": "success"
                })
            
            except Exception as db_err:
                db.rollback() # Batalkan transaksi DB
                if final_path and os.path.exists(final_path):
                    os.remove(final_path) # Hapus file jika DB gagal
                raise db_err # Lempar ke blok except luar

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
    masa_terbit: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(PEB).join(PEBTerbit)
    
    if masa_terbit:
        query = query.filter(PEBTerbit.masa_terbit == masa_terbit)
    
    # 3. Ambil data (Gunakan joinedload agar akses p.terbit tidak lambat)
    pebs = query.options(joinedload(PEB.terbit)).all()

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
                "masa_terbit": p.terbit.masa_terbit if p.terbit else None,
                "created_at": p.created_at
            }
            for p in pebs
        ],
        message="Success"
    )

# =========================================
# 🔹 GET ALL PEB masa terbit
# =========================================
@router.get("/?masa_terbit={masa_terbit}")
def get_peb(
    masa_terbit: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pebs = db.query(PEB).filter(PEB.terbit.has(PEBTerbit.masa_terbit == masa_terbit)).all()

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
                "masa_terbit": p.terbit.masa_terbit if p.terbit else None,
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


def format_document_date(val) -> str:
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    
    val_str = str(val).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return val_str

# =========================================
# 🔹 EXPORT PEB TO XML (Format Coretax/e-Faktur)
# =========================================
@router.get("/export-xml")
def export_peb_xml(
    ids: str = None,  # Komma-separated: ?ids=1,2,3
    masa_terbit: str = None,  # Filter per masa: ?masa_terbit=Mar 2026
    tin_perusahaan: str = "0314973306111000",  # NPWP Perusahaan / Pengusaha
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Query Data PEB
    query = db.query(PEB).join(PEBTerbit)

    if ids:
        id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
        query = query.filter(PEB.id.in_(id_list))
    elif masa_terbit:
        query = query.filter(PEBTerbit.masa_terbit == masa_terbit)

    pebs = query.options(joinedload(PEB.terbit)).all()

    if not pebs:
        return error_response("Tidak ada data PEB untuk diexport", 404)

    # 2. Buat Struktur Root XML
    root = ET.Element("SpecialDocBulk")
    
    tin_elem = ET.SubElement(root, "TIN")
    tin_elem.text = tin_perusahaan

    list_of_doc = ET.SubElement(root, "ListOfSpecialDoc")

    # 3. Loop Data PEB ke XML Node
    for p in pebs:
        doc = ET.SubElement(list_of_doc, "SpecialDoc")

        # Hitung DPP (TaxBase = FOB * Kurs)
        tax_base = float(p.nilai_fob or 0) * float(p.nilai_tukar or 0)
        
        # Format angka jika pecahan .0 hindari eksponen
        tax_base_str = f"{tax_base:.2f}".rstrip('0').rstrip('.') if tax_base % 1 != 0 else str(int(tax_base))

        ET.SubElement(doc, "TransactionType").text = "02"
        ET.SubElement(doc, "TransactionDetail").text = "11"
        ET.SubElement(doc, "TransactionDocument").text = "4"
        ET.SubElement(doc, "AdditionalInformation").text = ""
        ET.SubElement(doc, "DocumentNumber").text = str(p.document_number or "")
        ET.SubElement(doc, "DocumentDate").text = format_document_date(p.document_date)
        ET.SubElement(doc, "Reference").text = ""
        ET.SubElement(doc, "BuyerTIN").text = "0000000000000000"
        ET.SubElement(doc, "BuyerName").text = str(p.buyer_name or "")
        ET.SubElement(doc, "BuyerAddress").text = str(p.buyer_address or "")
        ET.SubElement(doc, "TaxBase").text = tax_base_str
        ET.SubElement(doc, "VAT").text = "0"
        ET.SubElement(doc, "STLG").text = "0"

    # 4. Convert XML Tree ke Format Pretty Printed String
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ", encoding="utf-8")

    # 5. Dynamic Filename
    filename = f"PEB_Export_{masa_terbit.replace(' ', '_') if masa_terbit else 'selected'}.xml"

    # 6. Return response sebagai file XML yang langsung terdownload
    return Response(
        content=pretty_xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
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

# =========================================
# 🔹 BULK DELETE PEB
# =========================================
@router.post("/bulk-delete") # Menggunakan POST agar lebih aman mengirim body list ID
def bulk_delete_peb(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Cek Role
    if current_user.role != "super_admin" and current_user.role != "admin":
        return error_response("Akses ditolak (admin only)", 403)

    # 2. Ambil semua data yang ID-nya ada dalam list
    pebs = db.query(PEB).filter(PEB.id.in_(payload.ids)).all()
    
    if not pebs:
        return error_response("Tidak ada data yang ditemukan untuk dihapus", 404)

    deleted_count = 0
    errors = []

    # 3. Proses penghapusan file fisik & record
    for peb in pebs:
        try:
            # Hapus file fisik jika ada
            if peb.file_path and os.path.exists(peb.file_path):
                os.remove(peb.file_path)
            
            # Hapus dari database
            db.delete(peb)
            deleted_count += 1
        except Exception as e:
            errors.append(f"ID {peb.id}: {str(e)}")

    # 4. Commit perubahan
    db.commit()

    return success_response(
        data={
            "deleted_count": deleted_count,
            "failed_count": len(errors),
            "errors": errors
        },
        message=f"Berhasil menghapus {deleted_count} data PEB"
    )