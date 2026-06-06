# ==========================================
# STAGE 1: Builder (Proses Install Dependencies)
# ==========================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install package system yang dibutuhkan untuk compile (jika ada library C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements saja terlebih dahulu agar memanfaatkan cache Docker
COPY requirements.txt .

# Install dependencies ke dalam folder lokal .venv
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt


# ==========================================
# STAGE 2: Runtime (Image Akhir yang Ringan)
# ==========================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Install runtime library untuk PostgreSQL (libpq) yang dibutuhkan aplikasi
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Salin virtual environment (.venv) hasil compile dari stage builder
COPY --from=builder /app/.venv /app/.venv

# Salin seluruh source code project ke dalam container
COPY . .

# Pastikan environment menggunakan virtual environment yang baru disalin
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 🔥 Buka port 3032 untuk FastAPI di dalam container
EXPOSE 3032

# 🔥 Jalankan Uvicorn dengan mengarahkan port ke 3032
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3032"]