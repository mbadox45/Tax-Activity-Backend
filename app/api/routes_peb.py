from fastapi import APIRouter, UploadFile, File
from app.services.pdf_service import extract_pdf
from app.services.parser_service import parse_peb, parse_items
from app.utils.text_cleaner import clean_text
from typing import List
import pdfplumber
import pandas as pd
import uuid
import os

router = APIRouter()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@router.post("/parse-peb-bulk")
async def parse_peb_bulk(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            file_id = str(uuid.uuid4())
            file_path = f"{UPLOAD_DIR}/{file_id}.pdf"

            # =============================
            # SAVE FILE
            # =============================
            with open(file_path, "wb") as f:
                f.write(await file.read())

            # =============================
            # EXTRACT PDF
            # =============================
            text, tables = extract_pdf(file_path)

            # =============================
            # CLEAN TEXT
            # =============================
            text = clean_text(text)

            # =============================
            # PARSE (SAMA DENGAN /upload)
            # =============================
            items = parse_items(tables)
            header = parse_peb(text, items)

            # =============================
            # FLATTEN RESULT
            # =============================
            results.append({
                "file_name": file.filename,
                **header   # 🔥 ini kuncinya (tidak ada nested data lagi)
                # "items": items  ← optional kalau mau
            })

        except Exception as e:
            results.append({
                "file_name": file.filename,
                "error": str(e)
            })

    return {
        "code": 200,
        "status": "success",
        "message": "Berhasil parsing multiple PEB",
        "data": results
    }

@router.post("/upload")
async def upload_peb(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"{UPLOAD_DIR}/{file_id}.pdf"

        # Save file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Extract PDF
        text, tables = extract_pdf(file_path)

        # Clean text
        text = clean_text(text)

        # Parse HEADER ONLY
        items = parse_items(tables)
        header = parse_peb(text, items)

        return {
            "code": 200,
            "status": "success",
            "message": "Berhasil parsing header PEB",
            "data": header,
            # "items": items
        }

    except Exception as e:
        return {
            "code": 500,
            "status": "error",
            "message": str(e),
            "data": None,
            # "items": None
        }

@router.get("/export/{file_id}")
def export_excel(file_id: str):
    # Dummy example (harusnya ambil dari DB / cache)
    data = {
        "items": [
            {"hs_code": "1234", "uraian": "Barang A", "jumlah": 100}
        ]
    }

    df = pd.DataFrame(data["items"])

    output_path = f"{OUTPUT_DIR}/{file_id}.xlsx"
    df.to_excel(output_path, index=False)

    return {"message": "Export success", "file": output_path}
