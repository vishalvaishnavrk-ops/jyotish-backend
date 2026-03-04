from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.routes.admin import router as admin_router
from app.routes.website import router as website_router

app = FastAPI(title="Jyotish SaaS Backend")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

app.include_router(admin_router)
app.include_router(website_router)

@app.get("/")
def root():
    return {"status": "Jyotish SaaS Backend Running"}
