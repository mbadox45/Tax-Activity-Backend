from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    name: str
    username: str
    password: str = Field(min_length=6, max_length=72)
    role: Optional[str] = "user"


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