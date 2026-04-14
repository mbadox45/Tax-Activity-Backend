from pydantic import BaseModel
from typing import Optional
from app.models.log_activity_model import ActivityStatus


class LogActivityCreate(BaseModel):
    activity_id: int
    status: ActivityStatus
    keterangan: Optional[str] = None