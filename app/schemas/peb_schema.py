from pydantic import BaseModel
from typing import List, Optional

class PEBHeader(BaseModel):
    nomor_peb: Optional[str]
    tanggal_peb: Optional[str]
    npwp: Optional[str]
    nama_eksportir: Optional[str]
    negara_tujuan: Optional[str]
    nilai_fob: Optional[str]


class PEBItem(BaseModel):
    hs_code: Optional[str]
    uraian: Optional[str]
    jumlah: Optional[str]


class PEBResponse(BaseModel):
    header: PEBHeader
    items: List[PEBItem]

class BulkDeleteRequest(BaseModel):
    ids: List[int]