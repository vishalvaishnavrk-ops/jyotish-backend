from fastapi import APIRouter, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import os
import urllib.parse

from app.database import get_db
from app.utils.helpers import generate_client_code
from app.services.ai_engine import generate_ai_draft
from app.services.pdf_engine import generate_pdf_report
from app.services.supabase_storage import upload_palm_image

templates = Jinja2Templates(directory="templates")

router = APIRouter()

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"


# ---------- ADMIN LOGIN ----------
@router.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
<html>
<body style="font-family:Arial;background:#f6efe9">

<div style="width:360px;margin:120px auto;background:white;padding:25px;border-radius:10px">

<h2 style="text-align:center;color:#8b0000">Admin Login</h2>

<form method="post" action="/admin/login">

Username<br>
<input name="username" required style="width:100%;padding:8px"><br><br>

Password<br>
<input type="password" name="password" required style="width:100%;padding:8px"><br><br>

<button style="width:100%;padding:10px;background:#8b0000;color:white;border:none">
Login
</button>

</form>

</div>

</body>
</html>
"""


@router.post("/admin/login")
def admin_login_post(username: str = Form(...), password: str = Form(...)):

    if username == "admin" and password == "admin123":
        return RedirectResponse("/admin/dashboard", status_code=302)

    return HTMLResponse("<h3>Invalid Login</h3>")


# ---------- DASHBOARD ----------
@router.get("/admin/dashboard")
def dashboard(request: Request,
q: str = Query(None),
plan: str = Query(None),
source: str = Query(None),
status: str = Query(None),
payment: str = Query(None),
start_date: str = Query(None),
end_date: str = Query(None)
):
    conn = get_db()
    c = conn.cursor()

    sql = """
    SELECT id,client_code,name,phone,plan,source,status,created_at,payment_status,priority
    FROM clients
    WHERE 1=1
    """

    params=[]

    if q:
        sql+=" AND (name ILIKE %s OR client_code ILIKE %s OR phone ILIKE %s)"
        params.extend([f"%{q}%",f"%{q}%",f"%{q}%"])

    if plan:
        sql+=" AND plan=%s"
        params.append(plan)

    if source:
        sql+=" AND source=%s"
        params.append(source)

    if status:
        sql+=" AND status=%s"
        params.append(status)

    if payment:
        sql+=" AND payment_status=%s"
        params.append(payment)

    if start_date:
        sql+=" AND created_at >= %s"
        params.append(start_date+" 00:00:00")

    if end_date:
        sql+=" AND created_at <= %s"
        params.append(end_date+" 23:59:59")

    sql += """
    ORDER BY
    CASE
    WHEN payment_status='Paid' AND status='Reviewed' THEN 1
    WHEN payment_status='Paid' AND status='Pending' THEN 2
    WHEN payment_status='Pending' THEN 3
    WHEN status='Completed' THEN 4
    ELSE 5
    END,
    priority ASC,
    created_at DESC
    """

    c.execute(sql,params)
    rows_db=c.fetchall()
    conn.close()


    rows=""

    for r in rows_db:

        dt=datetime.strptime(str(r[7])[:19],"%Y-%m-%d %H:%M:%S")
        formatted_date=dt.strftime("%d-%m-%Y %I:%M %p")

        if r[8]=="Paid":
            payment_badge="🟢 Paid"
        else:
            payment_badge=f"""
🔴 Pending
<form method="post" action="/admin/mark-paid/{r[0]}" style="display:inline;">
<button style="background:#28a745;color:white;border:none;padding:4px 8px;border-radius:4px">
Mark Paid
</button>
</form>
"""

        rows+=f"""
<tr>
<td>{r[1]}</td>
<td>{r[2]}</td>
<td>{r[4]}</td>
<td>{r[5]}</td>
<td>{r[6]}</td>
<td>{r[3]}</td>
<td>{payment_badge}</td>
<td>{formatted_date}</td>
<td><a href="/admin/client/{r[0]}">View</a></td>
</tr>
"""

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "clients": rows_db,
            "total_clients": len(rows_db),
            "pending_payment": sum(1 for r in rows_db if r[8] != "Paid"),
            "completed_reports": sum(1 for r in rows_db if r[6] == "Completed"),
            "reviewed_reports": sum(1 for r in rows_db if r[6] == "Reviewed"),
            "pending_reports": sum(
                1 for r in rows_db
                if r[8] == "Paid" and r[6] == "Pending"
            ),

            "total_revenue": sum(
                501 if "501" in r[4] else
                251 if "251" in r[4] else
                151 if "151" in r[4] else
                51
                for r in rows_db if r[8] == "Paid"
            ),

            # FILTER VALUES RETURN
            "q": q,
            "plan": plan,
            "source": source,
            "status": status,
            "payment": payment,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


# ---------- MARK PAID ----------
@router.post("/admin/mark-paid/{client_id}")
def mark_paid(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT plan FROM clients WHERE id=%s",(client_id,))
    plan=c.fetchone()[0]

    priority=4

    if "501" in plan:
        priority=1
    elif "251" in plan:
        priority=2
    elif "151" in plan:
        priority=3

    payment_date=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    UPDATE clients
    SET payment_status='Paid',payment_date=%s,priority=%s
    WHERE id=%s
    """,(payment_date,priority,client_id))

    conn.commit()
    conn.close()

    try:
        generate_ai_draft(client_id)
    except Exception as e:
        print("AI ERROR:", e)

    return RedirectResponse("/admin/dashboard",status_code=302)

# ---------- CLIENT DETAIL ----------
@router.get("/admin/client/{client_id}")
def client_detail(client_id: int, request: Request):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s", (client_id,))
    cdata = c.fetchone()

    conn.close()

    if not cdata:
        return HTMLResponse("Client not found")

    # ---------- IMAGES ----------
    images_list = []

    images_raw = cdata[9] if cdata[9] else ""

    if isinstance(images_raw, str):
        for img in images_raw.split(","):
            img = img.strip()
            if img != "":
                images_list.append(img)

    # ---------- CLIENT ----------
    client = {
        "id": cdata[0],
        "client_code": cdata[1],
        "name": cdata[2],
        "phone": cdata[3],
        "plan": cdata[7],
        "status": cdata[11],
        "payment_status": cdata[12],
        "payment_date": cdata[13],
        "payment_ref": cdata[14],
        "ai_draft": cdata[15],
        "ai_generated": cdata[17] if len(cdata) > 17 else 0,
    }

    ai_draft = client.get("ai_draft")
    status = client.get("status")
    
    return templates.TemplateResponse(
        "admin/client_detail.html",
        {
            "request": request,
            "client": client,
            "images": images_list,

            # 🔥 FLAGS FOR BUTTON CONTROL
            "can_generate_ai": client["payment_status"] == "Paid" and client.get("ai_generated", 0) == 0,
            "can_generate_pdf": (ai_draft and status == "Reviewed") or status == "Completed",
            "pdf_ready": os.path.exists(os.path.join(REPORT_DIR, f"{client['client_code']}.pdf")),
        },
    )

# ---------- UPDATE PAYMENT ----------
@router.post("/admin/client/{client_id}/payment")
def update_payment(
    client_id: int,
    payment_status: str = Form(...),
    payment_ref: str = Form(None)
):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT plan, ai_generated FROM clients WHERE id=%s",(client_id,))
    row = c.fetchone()
    plan = row[0]
    ai_generated = row[1] if row[1] is not None else 0

    payment_date = None
    priority = 99

    if payment_status == "Paid":

        payment_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

        if "501" in plan:
            priority = 1
        elif "251" in plan:
            priority = 2
        elif "151" in plan:
            priority = 3
        else:
            priority = 4

    c.execute("""
        UPDATE clients
        SET payment_status=%s,
            payment_date=%s,
            payment_ref=%s,
            priority=%s
        WHERE id=%s
    """,(payment_status,payment_date,payment_ref,priority,client_id))

    conn.commit()
    conn.close()

    # AI draft only first time
    if payment_status == "Paid" and ai_generated == 0:
        try:
            generate_ai_draft(client_id)
        except Exception as e:
            print("AI ERROR:", e)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)
    
# ---------- UPDATE CLIENT ----------
@router.post("/admin/client/{client_id}/update")
def update_client(client_id:int, ai_draft:str=Form(...), status:str=Form(...)):

    conn=get_db()
    c=conn.cursor()

    c.execute(
        "UPDATE clients SET ai_draft=%s,status=%s WHERE id=%s",
        (ai_draft,status,client_id)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)


# ---------- GENERATE AI ----------
@router.post("/admin/client/{client_id}/generate-ai")
def manual_ai_generate(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT payment_status, ai_generated FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    payment_status = data[0]
    ai_generated = data[1] if data[1] else 0

    # ❌ Block if payment not done
    if payment_status != "Paid":
        return HTMLResponse("<h3 style='color:red;text-align:center;'>Payment required before AI generation</h3>")

    # ❌ Block if already generated
    if ai_generated == 1:
        return HTMLResponse("<h3 style='color:red;text-align:center;'>AI already generated</h3>")

    try:
        generate_ai_draft(client_id)
    except Exception as e:
        print("AI ERROR:", e)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

# ---------- GENERATE PDF ----------
@router.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    if data[0] not in ["Reviewed", "Completed"]:
        return HTMLResponse(
            "<h3 style='color:red;text-align:center;margin-top:80px;'>Review required before PDF generation</h3>"
        )

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

# ---------- DOWNLOAD PDF ----------
@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT client_code,status FROM clients WHERE id=%s",(client_id,))
    data = c.fetchone()

    conn.close()

    if data[1] not in ["Reviewed","Completed"]:
        return HTMLResponse("PDF available after review")

    file_name = f"{data[0]}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    if not os.path.exists(file_path):
        return HTMLResponse("PDF not generated yet")

    return FileResponse(file_path,media_type="application/pdf",filename=file_name)


# ---------- SEND WHATSAPP ----------
@router.get("/admin/client/{client_id}/send-whatsapp")
def send_whatsapp(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT name, phone, client_code, status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    if not data:
        conn.close()
        return HTMLResponse("Client not found")

    name, phone_number, client_code, status = data

    # ❌ Block if not reviewed/completed
    if status not in ["Reviewed", "Completed"]:
        conn.close()
        return HTMLResponse("<h3 style='color:red;text-align:center;'>Complete review before sending</h3>")

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    if not os.path.exists(file_path):
        conn.close()
        return HTMLResponse("<h3 style='color:red;text-align:center;'>Generate PDF first</h3>")

    c.execute("UPDATE clients SET status='Completed' WHERE id=%s", (client_id,))
    conn.commit()
    conn.close()

    base_url = "https://jyotish-backend-gbr9.onrender.com"

    pdf_url = f"{base_url}/reports/{client_code}.pdf"

    message = f"""नमस्ते {name},

आपकी हस्तरेखा रिपोर्ट तैयार है।

PDF डाउनलोड करें:
{pdf_url}

– आचार्य विशाल वैष्णव
"""

    encoded = urllib.parse.quote(message)

    link = f"https://wa.me/91{phone_number}?text={encoded}"

    return RedirectResponse(link)    

# ---------- ADD CLIENT FORM ----------
@router.get("/admin/add-client")
def add_client_form(request: Request):
    return templates.TemplateResponse(
        "admin/add_client.html",
        {"request": request}
    )
    
@router.post("/admin/add-client")
async def add_client(
name:str=Form(...),
phone:str=Form(...),
dob:str=Form(...),
tob: str = Form(...),
place: str = Form(...),
questions:str=Form(...),
plan:str=Form(...),
images: List[UploadFile] = File(None)
):

    saved_files=[]

    if images:
        for img in images:

            unique_name = f"{uuid.uuid4().hex}_{img.filename}"

            file_bytes = await img.read()

            image_url = upload_palm_image(file_bytes, unique_name)

            saved_files.append(image_url)

    image_names=",".join(saved_files)

    conn=get_db()
    c=conn.cursor()

    client_code=generate_client_code()

    c.execute(
        """
        INSERT INTO clients
        (client_code,name,phone,dob,tob,place,questions,plan,images,source,status,payment_status,created_at,priority,ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_code,
            name,
            phone,
            dob,
            tob,
            place,
            questions,
            plan,
            image_names,
            "Manual",
            "Pending",
            "Pending",
            datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            99,
            0
        )
    )

    conn.commit()
    conn.close()

    return RedirectResponse("/admin/dashboard",status_code=302)
