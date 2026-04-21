from fastapi import APIRouter, Form, UploadFile, File, BackgroundTasks
from typing import List, Optional
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_db
from app.utils.helpers import generate_client_code
from app.services.supabase_storage import upload_palm_image

router = APIRouter()


# 🔥 BACKGROUND IMAGE PROCESS FUNCTION
def process_images(images: List[UploadFile], client_code: str):

    saved_files = []

    for img in images:
        try:
            file_bytes = img.file.read()
            unique_name = f"{uuid.uuid4().hex}_{img.filename}"
            file_url = upload_palm_image(file_bytes, unique_name, client_code)
            saved_files.append(file_url)
        except:
            continue

    # DB UPDATE AFTER UPLOAD
    if len(saved_files) == 4:
        conn = get_db()
        c = conn.cursor()

        c.execute(
            "UPDATE clients SET images=%s WHERE client_code=%s",
            (",".join(saved_files), client_code)
        )

        conn.commit()
        conn.close()


@router.post("/api/website-submit")
async def website_submit(
    background_tasks: BackgroundTasks,   # 🔥 ADD
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

    # 🔥 DUPLICATE CHECK
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

    # ✅ GENERATE CLIENT CODE
    client_code = generate_client_code()

    # 🔥 CLEAN DATA
    name = name.strip().upper()
    phone = phone.strip().upper() if phone else phone
    place = place.strip().upper() if place else place
    plan = plan.strip().upper() if plan else plan
    tob = tob.strip().upper() if tob else tob

    # ✅ INSERT CLIENT (FAST)
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
            "",  # images blank initially
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
    conn.close()

    # 🔥 BACKGROUND IMAGE UPLOAD (NON-BLOCKING)
    background_tasks.add_task(process_images, images, client_code)

    return {
        "success": True,
        "client_code": client_code
    }
