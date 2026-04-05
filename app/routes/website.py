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
    dob: str = Form(...),
    questions: str = Form(...),
    plan: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    images: List[UploadFile] = File(...)
):

    client_code = generate_client_code()

    saved_files = []

    for img in images:
        unique_name = f"{uuid.uuid4().hex}_{img.filename}"

        file_bytes = await img.read()

        # 🔥 TEMP PATH (NO CLIENT CODE YET)
        temp_path = f"temp/{unique_name}"

        supabase.storage.from_("palms").upload(
            temp_path,
            file_bytes,
            {"content-type": "image/jpeg"}
        )

        temp_url = f"{SUPABASE_URL}/storage/v1/object/public/palms/{temp_path}"

        saved_files.append(temp_url)
    
    image_names = ",".join(saved_files)

    conn = get_db()
    c = conn.cursor()

    client_code = generate_client_code()

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
            image_names,
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
    conn.close()

    # 🔥 FINAL MOVE TO CORRECT CLIENT FOLDER

    final_images = []

    for url in saved_files:
        filename = url.split("/")[-1]

        new_path = f"client_images/{client_code}/{filename}"

        # copy file
        supabase.storage.from_("palms").copy(
            f"temp/{filename}",
            new_path
        )

        # delete temp file
        supabase.storage.from_("palms").remove([f"temp/{filename}"])

        final_url = f"{SUPABASE_URL}/storage/v1/object/public/palms/{new_path}"

        final_images.append(final_url)

    # 🔥 UPDATE DB WITH FINAL URLs
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "UPDATE clients SET images=%s WHERE client_code=%s",
        (",".join(final_images), client_code)
    )

    conn.commit()
    conn.close()  
    
    return {
        "success": True,
        "client_code": client_code
    }
