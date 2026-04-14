from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse
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
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        name=payload.name,
        username=payload.username,
        password=hash_password(payload.password),
        role=payload.role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "code": 200,
        "status": True,
        "message": "User berhasil dibuat",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active
        }
    }

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

# get all users (admin only)
@router.get("/")
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    users = db.query(User).all()

    return success_response(
        data=[
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "role": user.role
            }
            for user in users
        ],
        message="Success"
    )

# update user (admin only)
@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.username = payload.username
    user.name = payload.name
    user.role = payload.role

    if payload.password:
        user.password = hash_password(payload.password)

    db.commit()
    db.refresh(user)

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role
        },
        message="User updated"
    )

# delete user (admin only)
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return success_response(
        data=None,
        message="User deleted"
    )