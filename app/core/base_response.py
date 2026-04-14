# app/core/base_response.py

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int
    status: bool
    message: str
    data: Optional[T]