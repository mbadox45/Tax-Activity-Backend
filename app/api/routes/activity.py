# app/api/routes/activity.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity_model import Activity
from app.models.log_activity_model import LogActivity, ActivityStatus
from app.schemas.activity_schema import ActivityCreate
from app.schemas.log_activity_schema import LogActivityCreate
from app.core.response import success_response, error_response
from app.api.deps import get_current_user
from app.models.user_model import User

router = APIRouter(prefix="/activities", tags=["Activities"])

# Create Activity
@router.post("/")
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = Activity(
        title=payload.title,
        category=payload.category,
        description=payload.description,
        user_id=current_user.id
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    # 🔥 AUTO LOG: pending
    log = LogActivity(
        activity_id=activity.id,
        status=ActivityStatus.on_progress,
        user_id=current_user.id
    )

    db.add(log)
    db.commit()

    return success_response(
        data={
            "id": activity.id,
            "title": activity.title,
            "category": activity.category,
            "description": activity.description,
            "created_at": activity.created_at
        },
        message="Activity created"
    )

# Get Activities
@router.get("/")
def get_activities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activities = db.query(Activity).all()

    return success_response(
        data=[
            {
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "description": a.description,
                "created_at": a.created_at,

                # 🔥 INCLUDE LOG ACTIVITY
                "logs": [
                    {
                        "id": log.id,
                        "status": log.status,
                        "keterangan": log.keterangan,
                        "created_at": log.created_at,
                        "user_id": log.user_id
                    }
                    for log in a.logs
                ]
            }
            for a in activities
        ],
        message="Success"
    )

# Get Activity Detail
@router.get("/{activity_id}")
def get_activity_detail(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = db.query(Activity).filter(
        Activity.id == activity_id
    ).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return success_response(
        data={
            "id": activity.id,
            "title": activity.title,
            "category": activity.category,
            "logs": [
                {
                    "status": log.status,
                    "created_at": log.created_at,
                    "keterangan": log.keterangan
                }
                for log in activity.logs
            ]
        },
        message="Success"
    )

# Add Log Activity
@router.post("/log")
def add_log_activity(
    payload: LogActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = db.query(Activity).filter(
        Activity.id == payload.activity_id
    ).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    log = LogActivity(
        activity_id=payload.activity_id,
        status=payload.status,
        user_id=current_user.id,
        keterangan=payload.keterangan
    )

    db.add(log)
    db.commit()

    return success_response(
        message="Log activity created"
    )

# Delete Activity
@router.delete("/{activity_id}")
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # =============================
    # 🔥 ROLE CHECK (ADMIN ONLY)
    # =============================
    if current_user.role != "admin":
        return error_response("Akses ditolak (admin only)", 403)

    activity = db.query(Activity).filter(
        Activity.id == activity_id
    ).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    db.delete(activity)
    db.commit()

    return success_response(message="Activity deleted")