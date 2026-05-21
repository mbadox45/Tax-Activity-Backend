# app/api/routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, ChangePasswordRequest, AdminResetPasswordRequest, UserUpdate
from app.core.response import success_response, error_response
from app.core.base_response import BaseResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# Register
@router.post("/register", response_model=BaseResponse[UserResponse])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()

    if existing:
        return error_response(
            data=None,
            message="Username already exists",
            code=400
        )

    # 🔑 Logika Default Password jika kosong atau tidak diisi oleh admin
    raw_password = payload.password if payload.password else "123456"

    user = User(
        name=payload.name,
        username=payload.username,
        password=hash_password(raw_password), # Di-hash dengan aman
        role=payload.role,
        group_id=getattr(payload, 'group_id', None) # Ambil group_id jika ada di skema
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return success_response(
        data={  
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active
        },
        message=f"User berhasil dibuat dengan password: {raw_password}"
    )

# Change Password
@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint khusus untuk user yang sedang login agar bisa mengganti password-nya sendiri.
    """
    # 1. Validasi password lama apakah cocok
    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Password lama yang Anda masukkan salah")

    # 2. Update password baru (di-hash)
    current_user.password = hash_password(payload.new_password)
    db.commit()

    return success_response(
        data=None,
        message="Password Anda berhasil diperbarui"
    )

# Reset Password
@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint khusus Admin & Superadmin untuk mereset password user lain kembali ke default '123456'.
    """
    # 1. Validasi Hak Akses Role
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Forbidden: Hanya Admin atau Superadmin yang diizinkan")

    # 2. Cari target user yang mau direset
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # 3. Proteksi Tingkat Role: Admin biasa tidak boleh mereset password seorang Superadmin
    if current_user.role == "admin" and target_user.role == "super_admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin tidak dapat mereset password Superadmin")

    # 4. Eksekusi Reset Password (jika payload kosong, otomatis default ke "123456")
    target_user.password = hash_password(payload.password)
    db.commit()

    return success_response(
        data={
            "user_id": target_user.id,
            "username": target_user.username,
            "reset_to": payload.password
        },
        message=f"Password untuk user {target_user.username} berhasil direset"
    )

# Login
@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({
        "sub": user.username
    })

    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "name": user.name,
                "username": user.username,
                "role": user.role
            }
        },
        message="Login berhasil"
    )

# Get current user
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data={
            "id": current_user.id,
            "username": current_user.username,
            "name": current_user.name,
            "role": current_user.role
        },
        message="Success"
    )

# get all users (admin & super_admin only)
@router.get("/")
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validasi awal: Hanya admin dan super_admin yang boleh masuk
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Forbidden: Akses ditolak")

    # 2. Inisialisasi query dasar
    query = db.query(User)

    # 3. Logika Filter berdasarkan Role
    if current_user.role == "admin":
        # Admin biasa hanya boleh melihat user dengan role 'user' atau 'admin'
        query = query.filter(User.role.in_(["user", "admin"]))
    
    # Note: Jika current_user.role == "super_admin", query tidak difilter 
    # sehingga otomatis akan menarik semua data user (termasuk super_admin lain)

    # 4. Eksekusi query ke database
    users = query.all()

    return success_response(
        data=[
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "role": user.role,
                # 🔥 Tambahan data group & sub-group dinamis
                "group_id": user.group_id,
                "group_name": user.group.name if user.group else None
            }
            for user in users
        ],
        message="Success fetch all users"
    )

# update user (admin & super_admin only) - termasuk update role & group_id
@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validasi Hak Akses Role
    if current_user.role not in ["admin", "super_admin"]:
        return error_response(
            message="Forbidden: Hanya Admin yang diizinkan",
            code=403
        )

    # 2. Cari Data User yang Akan Di-update
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return error_response(
            message="User tidak ditemukan",
            code=404
        )

    # 3. 🔥 PERBAIKAN: Ekstrak data payload dan map secara otomatis ke model database
    # Menggunakan exclude_unset=True agar field yang tidak dikirim di request tidak ikut menimpa data lama
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "password":
            if value: # Hanya hash password jika ada isinya
                user.password = hash_password(value)
        else:
            # Mengeset nilai ke model user secara dinamis (termasuk group_id & is_active)
            setattr(user, key, value)

    # 4. Simpan ke Database
    try:
        db.commit()
        db.refresh(user)

        # 5. Kembalikan Response Lengkap dengan Status Baru
        return success_response(
            data={
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "group_id": user.group_id,
                "group_name": user.group.name if user.group else None
            },
            message="User updated successfully"
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message=f"Gagal memperbarui data user: {str(e)}",
            code=500
        )

# delete user (super_admin only)
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "super_admin":
        return error_response(
            message="Forbidden: Hanya Super Admin yang diizinkan",
            code=403
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return error_response(
            message="User tidak ditemukan",
            code=404
        )

    db.delete(user)
    db.commit()

    return success_response(
        data=None,
        message="User deleted"
    )