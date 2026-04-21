from fastapi import APIRouter, Form, UploadFile, File
from typing import List, Optional
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_db, release_db
from app.utils.helpers import generate_client_code
from app.services.supabase_storage import upload_palm_image

router = APIRouter()


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

    # 🔥 STEP 1 — STRICT IMAGE VALIDATION
    if not images or len(images) != 4:
        return {"success": False, "error": "4 images required"}

    valid_images = [img for img in images if img.filename]

    if len(valid_images) != 4:
        return {"success": False, "error": "Invalid images"}

    conn = get_db()
    c = conn.cursor()
    conn.autocommit = True

    try:
        # ✅ STEP 2 — GENERATE CODE
        client_code = generate_client_code()

        name = name.strip().upper()
        phone = phone.strip().upper() if phone else phone
        place = place.strip().upper() if place else place
        plan = plan.strip().upper() if plan else plan
        tob = tob.strip().upper() if tob else tob

        # ✅ STEP 3 — INSERT CLIENT (EMPTY IMAGES)
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
                "",
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

        # ✅ STEP 4 — UPLOAD IMAGES
        saved_files = []

        for img in valid_images:
            file_bytes = await img.read()

            if not file_bytes:
                return {"success": False, "error": "Empty image"}

            unique_name = f"{uuid.uuid4().hex}_{img.filename}"
            file_url = upload_palm_image(file_bytes, unique_name, client_code)

            if not file_url:
                return {"success": False, "error": "Upload failed"}

            saved_files.append(file_url)

        if len(saved_files) != 4:
            return {"success": False, "error": "Upload incomplete"}

        # ✅ STEP 5 — UPDATE IMAGES
        c.execute(
            "UPDATE clients SET images=%s WHERE client_code=%s",
            (",".join(saved_files), client_code)
        )

        return {"success": True, "client_code": client_code}

    finally:
        release_db(conn)
