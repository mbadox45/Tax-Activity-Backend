# main.py

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import SessionLocal
from app.db.seed import run_seed
# API router
# from app.api.routes_peb import router as peb_router
from app.api.routes.user import router as user_router
from app.api.routes.activity import router as activity_router
from app.api.routes.peb import router as peb_router
from app.api.routes.peb_terbit import router as peb_terbit_router
from app.api.routes.document import router as document_router
from app.api.routes.storage import router as storage_router

# Exception handlers
from app.core.exception_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# 🔥 Parent router (versioning)
api_router = APIRouter(prefix="/api/v1")

app = FastAPI(
    title="ArdiarTax API",
    version="1.0.0"
)

# =============================
# CORS
# =============================
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# =============================
# Root
# =============================
@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to the ArdiarTax Backend!",
        "status": "success",
        "code": 200
    }

# =============================
# REGISTER ROUTES
# =============================
api_router.include_router(user_router)
api_router.include_router(activity_router)
# api_router.include_router(peb_router, prefix="/peb", tags=["PEB"])
api_router.include_router(peb_router)
api_router.include_router(peb_terbit_router)
api_router.include_router(document_router)
api_router.include_router(storage_router)
# 🔥 include ke app
app.include_router(api_router)

# =============================
# SEED
# =============================
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()