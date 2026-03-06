from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routes import admin
from app.routes import website

app = FastAPI()


# ---------- FOLDERS ----------
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"


if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)


# ---------- STATIC ----------
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- ROUTERS ----------
app.include_router(admin.router)
app.include_router(website.router)


# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "Jyotish AI Backend Running"}
