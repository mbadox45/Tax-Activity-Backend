# app/api/routes/dashboard.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import math
from datetime import datetime, timedelta  # 🔥 Tambahkan import timedelta dan datetime

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.document_model import Document
from app.api.deps import get_current_user  
from app.core.response import success_response, error_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper baru untuk memisahkan Angka Nilai dan Simbol Satuan Ukuran
def dms_split_storage(size_bytes: int):
    if size_bytes == 0:
        return 0, "B"
    
    size_name = ("B", "KB", "MB", "GB", "TB")
    # Tentukan index satuan berdasarkan kelipatan 1024
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    
    # Ambil nilai angka bulat / desimal halus
    value = round(size_bytes / p, 2)
    
    # Jika hasilnya angka bulat (misal 3.0), ubah ke integer (3) agar rapi sesuai request
    if value.is_integer():
        value = int(value)
        
    return value, size_name[i]


@router.get("/storage-stats")
def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Tentukan Kuota Maksimum Global
        TOTAL_STORAGE_LIMIT_BYTES = 512 * 1024 * 1024 * 1024 

        # 2. Hitung Storage yang Digunakan
        storage_used_raw = db.query(func.sum(Document.file_size)).filter(
            Document.user_id == current_user.id,
            Document.is_folder == False
        ).scalar()

        storage_used_bytes = int(storage_used_raw) if storage_used_raw is not None else 0

        # 3. Hitung Persentase Penggunaan Storage
        percentage_used = 0.0
        if TOTAL_STORAGE_LIMIT_BYTES > 0:
            percentage_used = round((storage_used_bytes / TOTAL_STORAGE_LIMIT_BYTES) * 100, 2)

        # 4. Pecah nilai bytes ke bentuk Angka Terpisah & Satuan Terpisah
        total_val, total_unit = dms_split_storage(TOTAL_STORAGE_LIMIT_BYTES)
        used_val, used_unit = dms_split_storage(storage_used_bytes)

        # 5. 🔥 GENERATE ACTIVITY DATA (30 Hari Terakhir)
        activity_data = []
        today = datetime.now()

        # Looping mundur dari 29 hari yang lalu sampai hari ini (total 30 hari)
        for i in range(29, -1, -1):
            target_date = today - timedelta(days=i)
            activity_data.append({
                "day": target_date.strftime("%Y-%m-%d"),  # Format: "2026-06-05" (bisa diubah sesuai kebutuhan chart)
                "tasks": 0
            })

        # 6. Susun Payload Data Lengkap
        dashboard_data = {
            "total_storage": total_val,
            "total_storage_bytes": TOTAL_STORAGE_LIMIT_BYTES,
            "total_storage_formatted": total_unit,
            "storage_used": used_val,
            "storage_used_bytes": storage_used_bytes,
            "storage_used_formatted": used_unit,
            "percentage_used": percentage_used,
            "activityData": activity_data  # 🔥 Injeksi data aktivitas dummy di sini
        }

        return success_response(
            data=dashboard_data,
            message="Statistik penyimpanan dashboard berhasil dimuat."
        )

    except Exception as e:
        return error_response(
            message=f"Terjadi kesalahan saat memuat dashboard: {str(e)}", 
            code=500
        )