from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user_model import User

security = HTTPBearer()


def get_current_user(
    token=Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        username = payload.get("sub")

        user = db.query(User).filter(User.username == username).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def is_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency untuk memvalidasi apakah user memiliki hak akses Admin.
    Digunakan sebagai Depends(is_admin) pada route yang diproteksi.
    """
    # 1. Cek apakah user ditemukan (biasanya sudah ditangani get_current_user)
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="User tidak terautentikasi."
        )
    
    # 2. Cek atribut is_admin pada model User di database
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Akses ditolak. Endpoint ini hanya untuk Administrator."
        )
    
    return current_user