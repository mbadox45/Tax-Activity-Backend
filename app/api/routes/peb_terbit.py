# app/api/routes/peb_terbit.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from fastapi import Body

from app.db.session import get_db
from app.models.peb_terbit_model import PEBTerbit
from app.models.peb_model import PEB
from app.models.user_model import User

from app.api.deps import get_current_user
from app.core.response import success_response, error_response

router = APIRouter(prefix="/peb-terbit", tags=["PEB Terbit"])

# Get All
@router.get("/")
def get_peb_terbit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = db.query(PEBTerbit).all()

    return success_response(
        data=[
            {
                "id": t.id,
                "masa_terbit": t.masa_terbit,
                "created_at": t.created_at,
                "peb": {
                    "id": t.peb.id,
                    "document_number": t.peb.document_number,
                    "buyer_name": t.peb.buyer_name
                }
            }
            for t in data
        ],
        message="Success"
    )

# Crete PEB Terbit
@router.post("/")
def create_peb_terbit(
    peb_id: int,
    masa_terbit: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # =============================
    # VALIDASI PEB
    # =============================
    peb = db.query(PEB).filter(
        PEB.id == peb_id
    ).first()

    if not peb:
        return error_response("PEB tidak ditemukan", 404)

    # =============================
    # CEK SUDAH TERBIT ATAU BELUM
    # =============================
    existing = db.query(PEBTerbit).filter(
        PEBTerbit.peb_id == peb_id
    ).first()

    if existing:
        return error_response("PEB sudah terbit", 400)

    # =============================
    # CREATE
    # =============================
    terbit = PEBTerbit(
        peb_id=peb_id,
        masa_terbit=masa_terbit,
        user_id=current_user.id
    )

    db.add(terbit)
    db.commit()
    db.refresh(terbit)

    return success_response(
        data={
            "id": terbit.id,
            "peb_id": terbit.peb_id,
            "masa_terbit": terbit.masa_terbit
        },
        message="PEB berhasil ditandai sebagai terbit"
    )

# Create PEB Terbit Bulk
@router.post("/bulk")
def bulk_create_peb_terbit(
    peb_ids: List[int] = Body(...),
    masa_terbit: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = []

    for peb_id in peb_ids:
        try:
            # =============================
            # VALIDASI PEB
            # =============================
            peb = db.query(PEB).filter(
                PEB.id == peb_id
            ).first()

            if not peb:
                results.append({
                    "peb_id": peb_id,
                    "status": "not_found"
                })
                continue

            # =============================
            # CEK DUPLICATE
            # =============================
            existing = db.query(PEBTerbit).filter(
                PEBTerbit.peb_id == peb_id
            ).first()

            if existing:
                results.append({
                    "peb_id": peb_id,
                    "status": "already_exists"
                })
                continue

            # =============================
            # CREATE
            # =============================
            terbit = PEBTerbit(
                peb_id=peb_id,
                masa_terbit=masa_terbit,
                user_id=current_user.id
            )

            db.add(terbit)
            db.commit()
            db.refresh(terbit)

            results.append({
                "peb_id": peb_id,
                "status": "success",
                "id": terbit.id
            })

        except Exception as e:
            results.append({
                "peb_id": peb_id,
                "status": "error",
                "error": str(e)
            })

    return success_response(
        data=results,
        message="Bulk PEB Terbit selesai"
    )

# Update PEB Terbit Masa Terbit
@router.put("/{terbit_id}")
def update_peb_terbit(
    terbit_id: int,
    masa_terbit: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    terbit = db.query(PEBTerbit).filter(
        PEBTerbit.id == terbit_id,
    ).first()

    if not terbit:
        return error_response("Data tidak ditemukan", 404)

    terbit.masa_terbit = masa_terbit

    db.commit()
    db.refresh(terbit)

    return success_response(
        data={
            "id": terbit.id,
            "masa_terbit": terbit.masa_terbit
        },
        message="Masa terbit berhasil diupdate"
    )

# Delete PEB Terbit
@router.delete("/{terbit_id}")
def delete_peb_terbit(
    terbit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # =============================
    # 🔥 ROLE CHECK (ADMIN ONLY)
    # =============================
    if current_user.role != "admin":
        return error_response("Akses ditolak (admin only)", 403)

    # =============================
    # GET DATA
    # =============================
    terbit = db.query(PEBTerbit).filter(
        PEBTerbit.id == terbit_id
    ).first()

    if not terbit:
        return error_response("Data tidak ditemukan", 404)

    # =============================
    # DELETE
    # =============================
    db.delete(terbit)
    db.commit()

    return success_response(
        message="Status PEB terbit berhasil dihapus"
    )