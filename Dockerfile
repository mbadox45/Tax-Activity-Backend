# Gunakan image Python resmi
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    # Library untuk WeasyPrint (Sudah diperbaiki namanya)
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    # Library untuk PostgreSQL & FFI
    libffi-dev \
    libpq-dev \
    # Tambahkan Tesseract OCR (karena ada di .env Anda)
    tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh project
COPY . .

# Buat folder uploads dan cache
RUN mkdir -p uploads/documents uploads/cache_pdf

# Port FastAPI
EXPOSE 8000

# Jalankan aplikasi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]