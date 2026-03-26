from fastapi import FastAPI
from app.api.routes_peb import router as peb_router

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="PEB PDF Parser API",
    version="1.0.0"
)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # atau ["*"] untuk sementara
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(peb_router, prefix="/api/peb")