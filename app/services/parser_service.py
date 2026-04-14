# app/services/parser_service.py
import re

def extract_field(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None

def clean_text(val):
    if not val:
        return val

    # stop kalau ketemu keyword lain
    val = re.split(r"(Jenis\s*:|NIPER\s*:|Status\s*:|NPWP\s*:)", val)[0]

    return val.strip()

def clean_number(value):
    if not value:
        return None
    return re.sub(r"[^\d]", "", value)  # hilangkan titik/koma

def extract_invoice_from_items(items):
    invoices = []

    for item in items:
        values = list(item.values())

        # =============================
        # CASE 1: STRUCTURED TABLE
        # =============================
        if "Jenis Dokumen" in item and "Nomor Dokumen" in item:
            if item["Jenis Dokumen"] and "INVOICE" in item["Jenis Dokumen"].upper():
                invoices.append(item["Nomor Dokumen"])

        # =============================
        # CASE 2: MULTILINE TEXT
        # =============================
        for val in values:
            if not val:
                continue

            text = str(val)
            text = text.replace("\n", " ")
            text = re.sub(r"\s+", " ", text)

            if "INVOICE" in text.upper():
                match = re.search(
                    r"Nomor\s*Dokumen\s*[:\-]?\s*([A-Z0-9\-\/\.]+)",
                    text,
                    re.IGNORECASE,
                )
                if match:
                    invoices.append(match.group(1).strip())

    # remove duplicate
    return list(set(invoices)) if invoices else None


import re

def parse_peb(text, items=None):

    # =============================
    # NORMALIZE TEXT (FIX PDF BUG)
    # =============================
    text = text.replace("\n", " ")
    text = re.sub(r"([A-Z])(\d{1,2}\.)", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text)

    # =============================
    # NOMOR PENGAJUAN
    # =============================
    nomor_pengajuan = extract_field(
        r"Nomor\s*Pengajuan\s*[:\-]?\s*([A-Z0-9]+)", text
    )

    # =============================
    # NOMOR PENDAFTARAN (SECTION J)
    # =============================
    nomor_pendaftaran = extract_field(
        r"Pendaftaran[\s\S]*?Nomor\s*[:\-]?\s*([A-Z0-9]+)", text
    )

    # =============================
    # FALLBACK KE ITEMS
    # =============================
    if not nomor_pengajuan and items:
        nomor_pengajuan = extract_from_items(items, "Nomor Pengajuan")

    if not nomor_pendaftaran and items:
        nomor_pendaftaran = extract_from_items(items, "Nomor Pendaftaran")

    # =============================
    # INVOICE (FINAL FIX)
    # =============================
    invoice = None

    matches = re.findall(
        r"[A-Z0-9]+\/INV[\-A-Z0-9\/\.]*",
        text,
        re.IGNORECASE
    )

    if matches:
        invoice = max(matches, key=len)

    # =============================
    # PEMBELI
    # =============================
    pembeli_block = None

    match_block = re.search(
        r"PEMBELI(.*?)(PENERIMA|DATA TRANSAKSI|DOKUMEN)",
        text,
        re.IGNORECASE
    )

    if match_block:
        pembeli_block = match_block.group(1)


    # =============================
    # NAMA PEMBELI
    # =============================
    nama_pembeli = None

    if pembeli_block:
        match_nama = re.search(
            r"Nama\s*:\s*(.*?)\s*\d+\.",
            pembeli_block
        )

        if match_nama:
            nama_pembeli = match_nama.group(1).strip()

    # =============================
    # ALAMAT PEMBELI
    # =============================
    alamat_pembeli = None

    if pembeli_block:
        match_alamat = re.search(
            r"Alamat\s*:\s*(.*?)\s*\d+\.",
            pembeli_block
        )

        if match_alamat:
            alamat_pembeli = match_alamat.group(1).strip()

    # =============================
    # RETURN FINAL
    # =============================
    return {
        "tanggal_peb": extract_field(
            r"Tanggal\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})", text
        ),

        "nilai_fob": clean_number(
            extract_field(r"FOB\s*[:\-]?\s*([\d\.,]+)", text)
        ),

        "nilai_tukar": clean_number(
            extract_field(r"Nilai\s*Tukar\s*[:\-]?\s*([\d\.,]+)", text)
        ),

        "nama_pembeli": clean_text(nama_pembeli),

        "alamat_pembeli": clean_text(alamat_pembeli),

        "nomor_pengajuan": nomor_pengajuan,
        "nomor_pendaftaran": nomor_pendaftaran,

        "invoice": invoice,
    }

def extract_from_items(items, keyword):
    for item in items:
        for value in item.values():
            if not value:
                continue

            text = str(value)

            # NORMALIZE (PENTING 🔥)
            text = text.replace("\n", " ")
            text = re.sub(r"\s+", " ", text)

            if keyword.lower() in text.lower():
                # ambil angka setelah titik dua
                match = re.search(rf"{keyword}.*?:\s*([A-Z0-9]+)", text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

    return None


def parse_items(tables):
    items = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        headers = table[0]

        for row in table[1:]:
            if len(row) != len(headers):
                continue

            item = dict(zip(headers, row))
            items.append(item)

    return items