import pytesseract
from pdf2image import convert_from_bytes
from app.core.config import TESSERACT_PATH
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def ocr_pdf(file_bytes: bytes):
    print("=== OCR START ===")

    images = convert_from_bytes(
        file_bytes,
        poppler_path=r"C:\poppler\Library\bin"
    )

    print(f"Total pages: {len(images)}")

    full_text = ""

    for i, img in enumerate(images):
        print(f"Processing page {i+1}")
        text = pytesseract.image_to_string(img, lang="eng")
        full_text += "\n" + text

    print("=== OCR DONE ===")

    return full_text


def parse_peb_from_text(text: str):
    data = {}

    def extract(pattern):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    data["nomor_peb"] = extract(r"PEB\s*No[:\s]*([A-Z0-9\-\/]+)")
    data["npwp"] = extract(r"NPWP[:\s]*([\d\.]+)")
    data["tanggal_peb"] = extract(r"Tanggal[:\s]*([\d\-\/]+)")
    data["nama_eksportir"] = extract(r"Nama[:\s]*(.+)")
    data["negara_tujuan"] = extract(r"Negara Tujuan[:\s]*(.+)")
    data["nilai_fob"] = extract(r"FOB[:\s]*([\d,\.]+)")

    return data