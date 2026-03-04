from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os

from app.models import init_db
from app.routes import admin
from app.routes import website


app = FastAPI()


# ---------- INIT DB ----------
init_db()


# ---------- STATIC ----------
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")


# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- ROUTES ----------
app.include_router(admin.router)
app.include_router(website.router)


@app.get("/")
def root():
    return {"status": "Backend running"}
