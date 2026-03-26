import pdfplumber

def extract_pdf(file_path: str):
    text = ""
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

            page_tables = page.extract_tables()
            for table in page_tables:
                tables.append(table)

    return text, tables