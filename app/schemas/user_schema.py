from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    name: str
    username: str
    password: str = Field(min_length=6, max_length=72)
    role: Optional[str] = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None  # Tambahkan ini
    group_id: Optional[int] = None    # Tambahkan ini

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

# Untuk User ganti password sendiri
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, description="Minimal 6 karakter")

# Untuk Admin/Superadmin yang mereset password user lain
class AdminResetPasswordRequest(BaseModel):
    # opsional jika ingin custom password, tapi bisa dikosongkan jika ingin otomatis ke default
    password: str = "123456"