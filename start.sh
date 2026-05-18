#!/bin/bash
# 1. Masuk ke direktori proyek
cd /home/ict-production/Documents/tax/Tax-Activity-Backend

# 2. Aktifkan virtual environment
source venv/bin/activate

# 3. Jalankan uvicorn dengan port 3032 dan fitur --reload (worker otomatis harus 1)
exec uvicorn app.main:app --host 0.0.0.0 --port 3032 --reload