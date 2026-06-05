from pydantic import BaseModel
from typing import Optional

class StorageDashboardResponse(BaseModel):
    total_storage_bytes: int
    total_storage_formatted: str
    storage_used_bytes: int
    storage_used_formatted: str
    percentage_used: float