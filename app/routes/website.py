from fastapi import APIRouter, Form
from app.models import create_client
import uuid
from datetime import datetime

router = APIRouter()

def generate_client_code():
    return "AVV-" + str(uuid.uuid4())[:8]

@router.post("/api/website-submit")
def website_submit(
    name: str = Form(...),
    phone: str = Form(...),
    plan: str = Form(...)
):

    client_code = generate_client_code()

    data = (
        client_code,
        name,
        phone,
        None,
        None,
        None,
        plan,
        "",
        "",
        "Website",
        "Pending",
        "Pending",
        datetime.now(),
        99,
        0
    )

    create_client(data)

    return {"success": True, "client_code": client_code}
