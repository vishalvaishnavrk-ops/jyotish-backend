from fastapi import APIRouter, Form, UploadFile, File
from typing import List
import uuid
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import create_client
from app.utils.helpers import generate_client_code

UPLOAD_DIR = "uploads"

router = APIRouter()


@router.post("/api/website-submit")
async def website_submit(
    name: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(...),
    questions: str = Form(...),
    plan: str = Form(...),
    tob: str = Form(None),
    place: str = Form(None),
    images: List[UploadFile] = File(...)
):

    saved_files = []

    for img in images:

        unique_name = f"{uuid.uuid4().hex}_{img.filename}"
        path = os.path.join(UPLOAD_DIR, unique_name)

        with open(path, "wb") as f:
            f.write(await img.read())

        saved_files.append(unique_name)

    image_names = ",".join(saved_files)

    client_code = generate_client_code()

    data = (
        client_code,
        name,
        phone,
        dob,
        tob,
        place,
        plan,
        questions,
        image_names,
        "Website",
        "Pending",
        "Pending",
        datetime.now(ZoneInfo("Asia/Kolkata")),
        99,
        0
    )

    create_client(data)

    return {
        "success": True,
        "client_code": client_code
    }
