# app/api/routes/group.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.models.group_model import Group
from app.models.user_model import User
from app.schemas.group_schema import GroupCreate, GroupUpdate, GroupResponse, GroupTreeResponse
from app.api.deps import get_current_user

# 🔥 Import format respons standar aplikasi Anda
from app.core.response import success_response, error_response

router = APIRouter(prefix="/groups", tags=["Groups"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================================
# 1. ENDPOINT: Ambil Semua Group dalam Bentuk Pohon Hierarki (Tree)
# =========================================================================
@router.get("/tree")
def get_group_tree(db: Session = Depends(get_db)):
    """
    Mengambil semua group utama beserta sub-group di dalamnya secara terstruktur.
    """
    try:
        # 1. Ambil semua Group Utama yang tidak memiliki parent (Akar Hierarki)
        parent_groups = db.query(Group).filter(Group.parent_id == None).all()
        
        # 2. Fungsi pembantu untuk merubah struktur objek ORM menjadi Dictionary secara rekursif
        def format_group_node(group_obj: Group) -> dict:
            return {
                "id": group_obj.id,
                "name": group_obj.name,
                "is_active": group_obj.is_active,
                "parent_id": group_obj.parent_id,
                # Rekursif panggil dirinya sendiri untuk mengonversi seluruh sub-group di bawahnya
                "sub_groups": [format_group_node(sub) for sub in group_obj.sub_groups]
            }
        
        # 3. Eksekusi semua data utama
        data = [format_group_node(g) for g in parent_groups]
        
        return success_response(
            data=data, 
            message="Berhasil mengambil struktur hierarki group"
        )
        
    except Exception as e:
        return error_response(
            message=f"Gagal mengambil struktur group: {str(e)}", 
            code=500  # Sesuaikan dengan nama argumen response helper Anda (code / status_code)
        )

# =========================================================================
# 2. ENDPOINT: Ambil Flat List Semua Group/Sub-Group
# =========================================================================
@router.get("/")
def get_all_groups(db: Session = Depends(get_db)):
    """
    Mengambil daftar semua group dan sub-group tanpa struktur hirarki (Flat List).
    """
    try:
        groups = db.query(Group).all()
        data = [GroupResponse.model_validate(g).model_dump() for g in groups]
        
        return success_response(data=data, message="Berhasil mengambil semua daftar group")
    except Exception as e:
        return error_response(
            message=f"Gagal mengambil daftar group: {str(e)}", 
            code=500
        )

# =========================================================================
# 3. ENDPOINT: Tambah Group atau Sub-Group Baru
# =========================================================================
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Proteksi: Hanya super_admin yang boleh membuat group
    if current_user.role != "super_admin":
        return error_response(message="Akses ditolak. Anda bukan Super Admin.", status_code=403)

    # Validasi duplikasi nama group
    existing_group = db.query(Group).filter(Group.name == payload.name).first()
    if existing_group:
        return error_response(message="Nama Group/Sub-Group sudah digunakan", status_code=400)

    # Jika membuat sub-group, pastikan parent_id nya ada di database
    if payload.parent_id:
        parent = db.query(Group).filter(Group.id == payload.parent_id).first()
        if not parent:
            return error_response(message="Parent Group tidak ditemukan", status_code=404)

    try:
        new_group = Group(
            name=payload.name,
            parent_id=payload.parent_id
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        data = GroupResponse.model_validate(new_group).model_dump()
        return success_response(data=data, message="Group/Sub-Group berhasil ditambahkan")
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal membuat group: {str(e)}", status_code=500)

# =========================================================================
# 4. ENDPOINT: Update Group / Sub-Group
# =========================================================================
@router.put("/{group_id}")
def update_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "super_admin":
        return error_response(message="Akses ditolak.", status_code=403)

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return error_response(message="Group tidak ditemukan", status_code=404)

    # Update field jika dikirim di payload
    if payload.name is not None:
        group.name = payload.name
    if payload.is_active is not None:
        group.is_active = payload.is_active
    if payload.parent_id is not None:
        if payload.parent_id == group.id:
            return error_response(message="Group tidak bisa menjadi parent dari dirinya sendiri", status_code=404)
        group.parent_id = payload.parent_id

    try:
        db.commit()
        db.refresh(group)
        data = GroupResponse.model_validate(group).model_dump()
        return success_response(data=data, message="Group berhasil diperbarui")
    except Exception as e:
        db.rollback()
        return error_response(message=f"Gagal memperbarui group: {str(e)}", status_code=500)

# =========================================================================
# 5. ENDPOINT: Hapus Group / Sub-Group
# =========================================================================
@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "super_admin":
        return error_response(message="Akses ditolak.", status_code=403)

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return error_response(message="Group tidak ditemukan", status_code=404)

    try:
        db.delete(group)
        db.commit()
        return success_response(data=None, message="Group berhasil dihapus")
    except Exception:
        db.rollback()
        return error_response(
            message="Gagal menghapus. Pastikan hapus semua Sub-Group di bawahnya terlebih dahulu.", 
            status_code=400
        )