from fastapi import APIRouter, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
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

router = APIRouter()

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"


# ---------- ADMIN LOGIN ----------
@router.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
<html>
<head>
<title>Admin Login</title>
<style>
body{font-family:Arial;background:#f6efe9;}
.login-box{
width:360px;margin:120px auto;padding:25px;background:white;
border-radius:10px;box-shadow:0 0 12px rgba(0,0,0,0.15);}
.login-box h2{text-align:center;color:#8b0000;}
.login-box input{width:100%;padding:8px;margin-top:6px;}
.login-box button{
width:100%;margin-top:15px;padding:10px;
background:#8b0000;color:white;border:none;border-radius:5px;}
</style>
</head>
<body>
<div class="login-box">
<h2>Admin Login</h2>
<form method="post" action="/admin/login">
Username
<input name="username" required>
Password
<input type="password" name="password" required>
<button>Login</button>
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
@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(q: str = Query(None), plan: str = Query(None), payment: str = Query(None)):

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
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if plan:
        sql += " AND plan=%s"
        params.append(plan)

    if payment:
        sql += " AND payment_status=%s"
        params.append(payment)

    sql += " ORDER BY priority ASC,id DESC"

    c.execute(sql, params)
    rows_db = c.fetchall()
    conn.close()

    rows = ""

    for r in rows_db:

        dt = datetime.strptime(str(r[7])[:19], "%Y-%m-%d %H:%M:%S")
        formatted = dt.strftime("%d-%m-%Y %I:%M %p")

        if r[8] == "Paid":
            payment_badge = "🟢 Paid"
        else:
            payment_badge = f"""
🔴 Pending
<form method="post" action="/admin/mark-paid/{r[0]}" style="display:inline;">
<button style="background:#28a745;color:white;border:none;padding:4px 8px;border-radius:4px;">Mark Paid</button>
</form>
"""

        rows += f"""
<tr>
<td>{r[1]}</td>
<td>{r[2]}</td>
<td>{r[4]}</td>
<td>{r[5]}</td>
<td>{r[6]}</td>
<td>{r[3]}</td>
<td>{payment_badge}</td>
<td>{formatted}</td>
<td><a href="/admin/client/{r[0]}">View</a></td>
</tr>
"""

    return f"""
<html>
<head>
<style>
body {{font-family:Arial;background:#f6efe9;margin:0;}}
.header {{background:#8b0000;color:white;padding:15px;font-size:20px;}}
.container {{padding:25px;}}
table {{width:100%;border-collapse:collapse;background:white;}}
th {{background:#f1e2d3;padding:10px;}}
td {{padding:10px;border-top:1px solid #ddd;}}
tr:hover {{background:#faf3ec;}}
</style>
</head>

<body>
<div class="header">ADMIN DASHBOARD</div>

<div class="container">

<a href="/admin/add-client">➕ Add New Client</a>

<br><br>

<form method="get">
<input type="text" name="q" placeholder="Client Code / Name">

<select name="plan">
<option value="">All Plans</option>
<option value="₹51 – बेसिक प्लान">₹51 – बेसिक प्लान</option>
<option value="₹151 – एडवांस प्लान">₹151 – एडवांस प्लान</option>
<option value="₹251 – प्रो प्लान">₹251 – प्रो प्लान</option>
<option value="₹501 – अल्टीमेट प्लान">₹501 – अल्टीमेट प्लान</option>
</select>

<select name="payment">
<option value="">All Payment</option>
<option value="Pending">Pending</option>
<option value="Paid">Paid</option>
</select>

<button type="submit">Filter</button>
</form>

<br>

<table>

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


# ---------- MARK PAID ----------
@router.post("/admin/mark-paid/{client_id}")
def mark_paid(client_id: int):

    conn = get_db()
    c = conn.cursor()

    payment_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    UPDATE clients
    SET payment_status='Paid',payment_date=%s,priority=1
    WHERE id=%s
    """,(payment_date,client_id))

    conn.commit()
    conn.close()

    generate_ai_draft(client_id)

    return RedirectResponse("/admin/dashboard",status_code=302)


# ---------- CLIENT DETAIL ----------
@router.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s",(client_id,))
    cdata=c.fetchone()

    conn.close()

    images_html=""

    if cdata[9]:
        for img in cdata[9].split(","):
            img=img.strip()
            if img:
                images_html+=f'<img src="/uploads/{img}" width="150" style="margin:5px;border:1px solid #ccc;">'

    return f"""
<html>
<body style="font-family:Arial;background:#f6efe9">

<h2 style="background:#8b0000;color:white;padding:15px">
Client Detail
</h2>

<div style="padding:25px;background:white">

<p><b>Client Code:</b> {cdata[1]}</p>
<p><b>Name:</b> {cdata[2]}</p>
<p><b>Phone:</b> {cdata[3]}</p>
<p><b>Plan:</b> {cdata[7]}</p>

<p><b>Palm Images:</b><br>{images_html}</p>

<br>

<form method="post" action="/admin/client/{client_id}/generate-ai">
<button style="background:#007bff;color:white;padding:10px;border:none">
Generate AI Draft
</button>
</form>

<br>

<form method="post" action="/admin/client/{client_id}/generate-pdf">
<button style="background:#6f42c1;color:white;padding:10px;border:none">
Generate PDF
</button>
</form>

<br>

<a href="/admin/client/{client_id}/pdf">
<button style="background:#8b0000;color:white;padding:10px;border:none">
Download PDF
</button>
</a>

<br><br>

<a href="/admin/client/{client_id}/send-whatsapp">
<button style="background:#25D366;color:white;padding:10px;border:none">
Send WhatsApp
</button>
</a>

</div>
</body>
</html>
"""


# ---------- GENERATE PDF ----------
@router.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT status FROM clients WHERE id=%s",(client_id,))
    data=c.fetchone()

    conn.close()

    if data[0]!="Reviewed":
        return HTMLResponse("<h3 style='color:red;text-align:center'>Review draft before generating PDF</h3>")

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)


# ---------- DOWNLOAD PDF ----------
@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT client_code FROM clients WHERE id=%s",(client_id,))
    data=c.fetchone()

    conn.close()

    if not data:
        return HTMLResponse("Report not found")

    file_name=f"{data[0]}.pdf"
    file_path=os.path.join(REPORT_DIR,file_name)

    if not os.path.exists(file_path):
        return HTMLResponse("PDF not generated yet")

    return FileResponse(file_path,media_type="application/pdf",filename=file_name)


# ---------- SEND WHATSAPP ----------
@router.get("/admin/client/{client_id}/send-whatsapp")
def send_whatsapp(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT name,phone,client_code FROM clients WHERE id=%s",(client_id,))
    data=c.fetchone()

    if not data:
        conn.close()
        return HTMLResponse("Client not found")

    name,phone,client_code=data

    c.execute("UPDATE clients SET status='Completed' WHERE id=%s",(client_id,))
    conn.commit()
    conn.close()

    base_url="https://jyotish-backend-gbr9.onrender.com"
    pdf_url=f"{base_url}/reports/{client_code}.pdf"

    message=f"""नमस्ते {name},

आपकी हस्तरेखा रिपोर्ट तैयार है।

PDF डाउनलोड करें:
{pdf_url}

– आचार्य विशाल वैष्णव
"""

    encoded=urllib.parse.quote(message)

    link=f"https://wa.me/91{phone}?text={encoded}"

    return RedirectResponse(link)
