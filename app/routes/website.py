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
    client_request_id: str = Form(...),    
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

    # 🔥 DUPLICATE CHECK (यहीं add करना है)
    c.execute(
        "SELECT client_code FROM clients WHERE client_request_id=%s",
        (client_request_id,)
    )
    existing = c.fetchone()

    if existing:
        conn.close()
        return {
            "success": True,
            "client_code": existing[0]
        }

    # ✅ STEP 1: GENERATE CLIENT CODE
    client_code = generate_client_code()

    # 🔥 AUTO CAPITAL (SAFE)
    name = name.strip().upper()
    phone = phone.strip().upper() if phone else phone
    place = place.strip().upper() if place else place
    plan = plan.strip().upper() if plan else plan
    tob = tob.strip().upper() if tob else tob

    # ✅ STEP 2: INSERT CLIENT (WITHOUT IMAGES)
    c.execute(
        """
        INSERT INTO clients
        (client_code,client_request_id,name,phone,dob,tob,place,plan,questions,images,
        source,status,payment_status,payment_date,payment_ref,
        ai_draft,created_at,priority,ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_code,
            client_request_id,
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
            1,
            0
        )
    )

    conn.commit()

    # ✅ STEP 3: UPLOAD IMAGES (AFTER DB INSERT)
    saved_files = []

    for img in images:

        file_bytes = await img.read()

        unique_name = f"{uuid.uuid4().hex}_{img.filename}"

        file_url = upload_palm_image(file_bytes, unique_name, client_code)

        saved_files.append(file_url)

    # 🔥 STRICT: exactly 4 images required
    if len(saved_files) != 4:
        conn.close()
        return {
            "success": False,
            "error": "4 valid images required"
        }

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
