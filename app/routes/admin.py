from fastapi import APIRouter, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import os

from app.database import get_db
from app.auth import check_admin
from app.utils.helpers import generate_client_code
from app.services.ai_engine import generate_ai_draft
from app.services.pdf_engine import generate_pdf_report
from app.services.whatsapp_service import generate_whatsapp_link

router = APIRouter()

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"


# ---------------- ADMIN LOGIN ----------------

@router.get("/admin", response_class=HTMLResponse)
def admin_login():

    return """
    <html>
    <head>
    <title>Admin Login</title>
    </head>

    <body style="font-family:Arial;background:#f6efe9">

    <div style="width:350px;margin:120px auto;background:white;padding:25px;border-radius:8px">

    <h2>Admin Login</h2>

    <form method="post" action="/admin/login">

    Username:<br>
    <input name="username"><br><br>

    Password:<br>
    <input type="password" name="password"><br><br>

    <button type="submit">Login</button>

    </form>

    </div>

    </body>
    </html>
    """


@router.post("/admin/login")
def admin_login_post(username: str = Form(...), password: str = Form(...)):

    if check_admin(username, password):
        return RedirectResponse("/admin/dashboard", status_code=302)

    return HTMLResponse("<h3>Invalid Login</h3>")


# ---------------- DASHBOARD ----------------

@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(
    q: str = Query(None),
    plan: str = Query(None),
    source: str = Query(None),
    status: str = Query(None),
    payment: str = Query(None),
):

    conn = get_db()
    c = conn.cursor()

    sql = """
    SELECT id,client_code,name,phone,plan,source,status,created_at,payment_status,priority
    FROM clients
    WHERE 1=1
    """

    params = []

    if q:
        sql += " AND (name ILIKE %s OR client_code ILIKE %s OR phone ILIKE %s)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]

    if plan:
        sql += " AND plan=%s"
        params.append(plan)

    if source:
        sql += " AND source=%s"
        params.append(source)

    if status:
        sql += " AND status=%s"
        params.append(status)

    if payment:
        sql += " AND payment_status=%s"
        params.append(payment)

    sql += " ORDER BY priority ASC, id DESC"

    c.execute(sql, params)

    rows_db = c.fetchall()

    conn.close()

    rows = ""

    for r in rows_db:

        rows += f"""
        <tr>
        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[4]}</td>
        <td>{r[5]}</td>
        <td>{r[6]}</td>
        <td>{r[3]}</td>
        <td>{r[8]}</td>
        <td>{r[7]}</td>
        <td><a href="/admin/client/{r[0]}">View</a></td>
        </tr>
        """

    return f"""
    <html>

    <body style="font-family:Arial;background:#f6efe9">

    <h2 style="background:#8b0000;color:white;padding:10px">
    ADMIN DASHBOARD
    </h2>

    <div style="padding:20px">

    <a href="/admin/add-client">➕ Add Client</a>

    <br><br>

    <table border="1" cellpadding="8" cellspacing="0">

    <tr>
    <th>Client Code</th>
    <th>Name</th>
    <th>Plan</th>
    <th>Source</th>
    <th>Status</th>
    <th>Phone</th>
    <th>Payment</th>
    <th>Date</th>
    <th>Action</th>
    </tr>

    {rows}

    </table>

    </div>

    </body>
    </html>
    """


# ---------------- CLIENT DETAIL ----------------

@router.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s", (client_id,))
    cdata = c.fetchone()

    conn.close()

    if not cdata:
        return HTMLResponse("Client not found")

    images_html = ""

    if cdata[9]:

        for img in cdata[9].split(","):

            images_html += f'<img src="/uploads/{img}" width="140" style="margin:5px;border:1px solid #ccc;">'

    return f"""
    <html>

    <body style="font-family:Arial;background:#f6efe9">

    <h2 style="background:#8b0000;color:white;padding:10px">
    Client Detail
    </h2>

    <div style="padding:20px">

    <b>Client Code:</b> {cdata[1]}<br>
    <b>Name:</b> {cdata[2]}<br>
    <b>Phone:</b> {cdata[3]}<br>
    <b>Plan:</b> {cdata[7]}<br>

    <br>

    {images_html}

    <br><br>

    <form method="post" action="/admin/client/{client_id}/generate-ai">

    <button>Generate AI Draft</button>

    </form>

    <br>

    <form method="post" action="/admin/client/{client_id}/generate-pdf">

    <button>Generate PDF</button>

    </form>

    <br>

    <a href="/admin/client/{client_id}/send-whatsapp">
    <button>Send WhatsApp</button>
    </a>

    <br><br>

    <a href="/admin/dashboard">Back</a>

    </div>

    </body>
    </html>
    """


# ---------------- AI GENERATE ----------------

@router.post("/admin/client/{client_id}/generate-ai")
def manual_ai_generate(client_id: int):

    generate_ai_draft(client_id)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)


# ---------------- PDF GENERATE ----------------

@router.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(client_id: int):

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)


# ---------------- WHATSAPP ----------------

@router.get("/admin/client/{client_id}/send-whatsapp")
def send_whatsapp(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT name, phone, client_code FROM clients WHERE id=%s",
        (client_id,)
    )

    data = c.fetchone()

    conn.close()

    if not data:
        return HTMLResponse("Client not found")

    name, phone, client_code = data

    base_url = "https://jyotish-backend-gbr9.onrender.com"

    pdf_url = f"{base_url}/reports/{client_code}.pdf"

    link = generate_whatsapp_link(name, phone, pdf_url)

    return RedirectResponse(link)


# ---------------- PDF DOWNLOAD ----------------

@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT client_code FROM clients WHERE id=%s",
        (client_id,)
    )

    data = c.fetchone()

    conn.close()

    if not data:
        return HTMLResponse("Report not found")

    file_name = f"{data[0]}.pdf"

    file_path = os.path.join(REPORT_DIR, file_name)

    if not os.path.exists(file_path):
        return HTMLResponse("PDF not generated yet")

    return FileResponse(file_path, filename=file_name)
