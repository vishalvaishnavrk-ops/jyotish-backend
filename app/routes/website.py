from fastapi import APIRouter, Form, UploadFile, File
from typing import List, Optional
import uuid
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_db
from app.utils.helpers import generate_client_code
from app.services.supabase_storage import upload_palm_image

router = APIRouter()

UPLOAD_DIR = "uploads"


@router.post("/api/website-submit")
async def website_submit(
    name: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(None),
    questions: str = Form(...),
    plan: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    images: List[UploadFile] = File(...)
):

    conn = get_db()
    c = conn.cursor()

    # ✅ STEP 1: GENERATE CLIENT CODE
    client_code = generate_client_code()

    # ✅ STEP 2: INSERT CLIENT (WITHOUT IMAGES)
    c.execute(
        """
        INSERT INTO clients
        (client_code,name,phone,dob,tob,place,plan,questions,images,
        source,status,payment_status,payment_date,payment_ref,
        ai_draft,created_at,priority,ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_code,
            name,
            phone,
            dob,
            tob,
            place,
            plan,
            questions,
            "",  # 🔥 EMPTY IMAGES
            "Website",
            "Pending",
            "Pending",
            None,
            None,
            "AI draft pending",
            datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            99,
            0
        )
    )

    conn.commit()

    # ✅ STEP 3: UPLOAD IMAGES (AFTER DB INSERT)
    saved_files = []

    for img in images:
        unique_name = f"{uuid.uuid4().hex}_{img.filename}"

        file_bytes = await img.read()

        file_url = upload_palm_image(file_bytes, unique_name, client_code)

        saved_files.append(file_url)

    # ✅ STEP 4: UPDATE DB WITH IMAGE URLS
    c.execute(
        "UPDATE clients SET images=%s WHERE client_code=%s",
        (",".join(saved_files), client_code)
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "client_code": client_code
    }
