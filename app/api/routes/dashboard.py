# app/api/routes/dashboard.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import math
import shutil  # 🔥 Tambahkan untuk membaca real-time kapasitas partisi server
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.group_model import Group  # 🔥 Import model Group
from app.models.document_model import Document
from app.models.document_access_model import DocumentAccess # 🔥 Import model DocumentAccess
from app.api.deps import get_current_user  
from app.core.response import success_response, error_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def dms_split_storage(size_bytes: int):
    if size_bytes == 0:
        return 0, "B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    value = round(size_bytes / p, 2)
    if value.is_integer():
        value = int(value)
    return value, size_name[i]


@router.get("/storage-stats")
def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        today = datetime.now()

        # =====================================================================
        # 👑 KONDISI A: LOGIKA KHUSUS SUPER_ADMIN
        # =====================================================================
        if current_user.role in ["super_admin", "superadmin"]:
            # 1. Real Server Capacity (Membaca partisi root "/")
            total_disk, used_disk, free_disk = shutil.disk_usage("/")
            
            srv_total_val, srv_total_unit = dms_split_storage(total_disk)
            srv_used_val, srv_used_unit = dms_split_storage(used_disk)
            srv_free_val, srv_free_unit = dms_split_storage(free_disk)

            # 2. Global Used Storage (Total seluruh file di DB dari semua user)
            global_used_raw = db.query(func.sum(Document.file_size)).filter(Document.is_folder == False).scalar()
            global_used_bytes = int(global_used_raw) if global_used_raw is not None else 0
            glob_used_val, glob_used_unit = dms_split_storage(global_used_bytes)

            # 3. Total Group
            total_groups = db.query(func.count(Group.id)).scalar() or 0

            # 4. Shared Folders (Total folder yang memiliki flag is_shared = True)
            shared_folders_count = db.query(func.count(Document.id)).filter(
                Document.is_folder == True,
                Document.is_shared == True
            ).scalar() or 0

            # 5. Today Actions & Server Traffic (30D) - Default dummy 0 karena data log belum ada
            server_traffic_30d = []
            for i in range(29, -1, -1):
                target_date = today - timedelta(days=i)
                server_traffic_30d.append({
                    "day": target_date.strftime("%Y-%m-%d"),
                    "requests": 0
                })

            # 6. Shared Folders by Group (Chart)
            # Menghitung berapa banyak dokumen/folder di tiap grup lewat tabel DocumentAccess
            group_sharing_raw = db.query(Group.name, func.count(DocumentAccess.document_id)).\
                join(DocumentAccess, Group.id == DocumentAccess.group_id).\
                group_by(Group.name).all()
            
            shared_folders_by_group = [
                {"group_name": name, "count": count} for name, count in group_sharing_raw
            ]

            # Susun Payload Super Admin
            super_admin_data = {
                "role": "super_admin",
                "cards": {
                    "server_capacity": {
                        "total": srv_total_val,
                        "formatted": srv_total_unit,
                        "bytes": total_disk
                    },
                    "global_used_storage": {
                        "total": glob_used_val,
                        "formatted": glob_used_unit,
                        "bytes": global_used_bytes
                    },
                    "total_groups": total_groups,
                    "shared_folders": shared_folders_count,
                    "today_actions": 0
                },
                "charts": {
                    "server_health": {
                        "used_storage": srv_used_val,
                        "used_storage_formatted": srv_used_unit,
                        "used_storage_bytes": used_disk,
                        "free_space": srv_free_val,
                        "free_space_formatted": srv_free_unit,
                        "free_space_bytes": free_disk,
                        "percentage_used": round((used_disk / total_disk) * 100, 2) if total_disk > 0 else 0
                    },
                    "shared_folders_by_group": shared_folders_by_group,
                    "server_traffic_30d": server_traffic_30d
                }
            }
            return success_response(data=super_admin_data, message="Dashboard Super Admin berhasil dimuat.")

        # =====================================================================
        # 👤 KONDISI B: LOGIKA USER REGULAR (Sama seperti sebelumnya)
        # =====================================================================
        TOTAL_STORAGE_LIMIT_BYTES = 512 * 1024 * 1024 * 1024 

        storage_used_raw = db.query(func.sum(Document.file_size)).filter(
            Document.user_id == current_user.id,
            Document.is_folder == False
        ).scalar()
        storage_used_bytes = int(storage_used_raw) if storage_used_raw is not None else 0

        percentage_used = 0.0
        if TOTAL_STORAGE_LIMIT_BYTES > 0:
            percentage_used = round((storage_used_bytes / TOTAL_STORAGE_LIMIT_BYTES) * 100, 2)

        total_val, total_unit = dms_split_storage(TOTAL_STORAGE_LIMIT_BYTES)
        used_val, used_unit = dms_split_storage(storage_used_bytes)

        activity_data = []
        for i in range(29, -1, -1):
            target_date = today - timedelta(days=i)
            activity_data.append({
                "day": target_date.strftime("%Y-%m-%d"),
                "tasks": 0
            })

        user_data = {
            "role": "user",
            "total_storage": total_val,
            "total_storage_bytes": TOTAL_STORAGE_LIMIT_BYTES,
            "total_storage_formatted": total_unit,
            "storage_used": used_val,
            "storage_used_bytes": storage_used_bytes,
            "storage_used_formatted": used_unit,
            "percentage_used": percentage_used,
            "activityData": activity_data
        }
        return success_response(data=user_data, message="Statistik penyimpanan dashboard berhasil dimuat.")

    except Exception as e:
        return error_response(message=f"Terjadi kesalahan saat memuat dashboard: {str(e)}", code=500)