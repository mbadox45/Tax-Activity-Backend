from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.activity_model import ActivityCategory


class ActivityCreate(BaseModel):
    title: str
    category: ActivityCategory
    description: Optional[str] = None


class ActivityResponse(BaseModel):
    id: int
    title: str
    category: ActivityCategory
    description: Optional[str]

    class Config:
        from_attributes = True