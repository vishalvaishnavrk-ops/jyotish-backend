from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os

from app.routes import admin
from app.routes import website

app = FastAPI()

templates = Jinja2Templates(directory="templates")


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
app.mount("/static", StaticFiles(directory="static"), name="static")

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
