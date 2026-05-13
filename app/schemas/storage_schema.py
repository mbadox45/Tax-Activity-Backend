# app/schemas/storage_schema.py
from pydantic import BaseModel

class StorageResponse(BaseModel):
    user_id: int
    used_storage_mb: float
    max_storage_mb: float
    percentage: float

class StorageUpdateRequest(BaseModel):
    user_id: int
    additional_storage_mb: int # Jumlah MB yang ingin ditambahkan