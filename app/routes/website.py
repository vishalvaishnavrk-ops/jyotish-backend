from fastapi import APIRouter, Form, UploadFile, File
from typing import List, Optional
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import get_db
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

    # 🔥 STEP 1 — STRICT IMAGE CHECK (सबसे पहले)
    if len(images) != 4:
        return {
            "success": False,
            "error": "4 images required"
        }

    conn = get_db()
    c = conn.cursor()

    # 🔥 STEP 2 — GENERATE CLIENT CODE
    client_code = generate_client_code()

    # 🔥 STEP 3 — CLEAN DATA
    name = name.strip().upper()
    phone = phone.strip()
    place = place.strip().upper() if place else place
    plan = plan.strip().upper()
    tob = tob.strip() if tob else tob

    # 🔥 STEP 4 — FAST DB INSERT (NO IMAGE WAIT)
    c.execute(
        """
        INSERT INTO clients
        (client_code,name,phone,dob,tob,place,plan,questions,images,
        source,status,payment_status,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()

    # 🔥 STEP 5 — IMAGE UPLOAD (NON-BLOCKING SAFE)
    saved_files = []

    for img in images:
        try:
            content = await img.read()
            unique_name = f"{uuid.uuid4().hex}_{img.filename}"

            file_url = upload_palm_image(content, unique_name, client_code)
            saved_files.append(file_url)

        except Exception as e:
            print("Image upload error:", e)
            continue

    # 🔥 STEP 6 — UPDATE IMAGES (ONLY IF ALL 4 SUCCESS)
    if len(saved_files) == 4:
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
