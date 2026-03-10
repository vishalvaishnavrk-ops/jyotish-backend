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
@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(
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

    sql+=" ORDER BY priority ASC,id DESC"

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

    return f"""
<html>

<body style="font-family:Arial;background:#f6efe9">

<div style="background:#8b0000;color:white;padding:20px;text-align:center">

<div style="font-size:22px;font-weight:bold">
ADMIN DASHBOARD
</div>

<div style="font-size:14px;margin-top:4px">
आचार्य विशाल वैष्णव – हस्तरेखा विशेषज्ञ एवं वैदिक ज्योतिषज्ञ
</div>

</div>

<a href="/admin/add-client">➕ Add New Client</a>

<br><br>

<form method="get">

<input type="text" name="q" placeholder="Client Code / Name" value="{q or ''}">

<select name="plan">
<option value="">All Plans</option>
<option value="₹51 – बेसिक प्लान">₹51 – बेसिक प्लान</option>
<option value="₹151 – एडवांस प्लान">₹151 – एडवांस प्लान</option>
<option value="₹251 – प्रो प्लान">₹251 – प्रो प्लान</option>
<option value="₹501 – अल्टीमेट प्लान">₹501 – अल्टीमेट प्लान</option>
</select>

<select name="source">
<option value="">All Sources</option>
<option value="Website">Website</option>
<option value="Manual">Manual</option>
</select>

<select name="status">
<option value="">All Status</option>
<option value="Pending">Pending</option>
<option value="Reviewed">Reviewed</option>
<option value="Completed">Completed</option>
</select>

<select name="payment">
<option value="">All Payment</option>
<option value="Pending">Pending</option>
<option value="Paid">Paid</option>
</select>

<input type="date" name="start_date">
<input type="date" name="end_date">

<button>Filter</button>

</form>

<br>

<table border="1" cellpadding="10" style="background:white;width:100%">

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

    generate_ai_draft(client_id)

    return RedirectResponse("/admin/dashboard",status_code=302)

# ---------- CLIENT DETAIL ----------
@router.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s", (client_id,))
    cdata = c.fetchone()

    conn.close()

    images_html = ""

    images=str(cdata[8]) if cdata[8] else ""

    for img in images.split(","):
        img=img.strip()
        if img!="":
            images_html+=f"""
            <img src="/uploads/{img}?v=1"
            style="width:170px;border-radius:10px;margin:6px;border:1px solid #ccc;">
            """
    return f"""
<html>

<div style="border-bottom:2px solid #d4af37;margin-bottom:20px"></div>

<body style="font-family:Arial;background:#f6efe9">

<h2 style="background:#8b0000;color:white;padding:15px">
Client Detail
</h2>

<div style="padding:30px;border-radius:12px;background:white">

<p><b>Client Code:</b> {cdata[1]}</p>
<p><b>Name:</b> {cdata[2]}</p>
<p><b>Phone:</b> {cdata[3]}</p>
<p><b>Plan:</b> {cdata[7]}</p>

<p><b>Palm Images:</b><br>{images_html}</p>

<hr>

<h3>Payment</h3>

<p><b>Status:</b> {cdata[12] or "Pending"}</p>
<p><b>Payment Date:</b> {cdata[13] or "-"}</p>
<p><b>Payment Ref:</b> {cdata[14] or "-"}</p>

<form method="post" action="/admin/mark-paid/{client_id}">
<button style="background:#28a745;color:white;padding:10px;border:none">
Mark Payment Paid
</button>
</form>

<hr>

<h3>AI Draft</h3>

<form method="post" action="/admin/client/{client_id}/update">

<textarea name="ai_draft" rows="12" style="width:100%">
{cdata[15]}
</textarea>

<br><br>

<label>Status</label>

<select name="status">

<option {"selected" if cdata[11]=="Pending" else ""}>Pending</option>
<option {"selected" if cdata[11]=="Reviewed" else ""}>Reviewed</option>
<option {"selected" if cdata[11]=="Completed" else ""}>Completed</option>

</select>

<br><br>

<button style="background:#8b0000;color:white;padding:10px;border:none">
Save Update
</button>

</form>

<hr>

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

<br><br>

<a href="/admin/dashboard"> Back to Dashboard</a>

</div>

</body>

</html>
"""


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
def manual_ai_generate(client_id:int):

    generate_ai_draft(client_id)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)


# ---------- GENERATE PDF ----------
@router.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT status FROM clients WHERE id=%s",(client_id,))
    data=c.fetchone()

    conn.close()

    if data[0]!="Reviewed":
        return HTMLResponse(
        "<h3 style='color:red;text-align:center;margin-top:80px;'>PDF Generate blocked. Mark draft Reviewed first.</h3>"
        )

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)


# ---------- DOWNLOAD PDF ----------
@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id: int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT client_code,status FROM clients WHERE id=%s",(client_id,))
    data = c.fetchone()

    conn.close()

    if data[1]!="Reviewed":
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

    c.execute("SELECT name, phone, client_code FROM clients WHERE id=%s",(client_id,))
    data = c.fetchone()

    if not data:
        conn.close()
        return HTMLResponse("Client not found")

    name, phone_number, client_code = data

    c.execute("UPDATE clients SET status='Completed' WHERE id=%s",(client_id,))
    conn.commit()
    conn.close()

    base_url = "https://jyotish-backend-gbr9.onrender.com"

    pdf_url = f"{base_url}/reports/{client_code}.pdf"

    message=f"""नमस्ते {name},

    आपकी हस्तरेखा रिपोर्ट तैयार है।

    PDF डाउनलोड करें:
    {pdf_url}

    – आचार्य विशाल वैष्णव
    """

    encoded=urllib.parse.quote(message)

    link=f"https://wa.me/91{phone_number}?text={encoded}"

    return RedirectResponse(link)    

# ---------- ADD CLIENT FORM ----------
@router.get("/admin/add-client", response_class=HTMLResponse)
def add_client_form():

    return """
<html>
<body style="font-family:Arial;background:#f6efe9">

<div style="width:650px;margin:40px auto;background:white;padding:25px;border-radius:10px">

<h2 style="color:#8b0000;text-align:center">नया क्लाइंट जोड़ें</h2>

<form method="post" action="/admin/add-client" enctype="multipart/form-data">

नाम<br>
<input name="name" required style="width:100%;padding:8px"><br><br>

मोबाइल नंबर<br>
<input name="phone" required style="width:100%;padding:8px"><br><br>

जन्म तिथि<br>
<input name="dob" required style="width:100%;padding:8px"><br><br>

जन्म समय
<input name="birth_time" style="width:100%;padding:8px" placeholder="HH:MM">

जन्म स्थान
<input name="birth_place" style="width:100%;padding:8px" placeholder="City">

मुख्य प्रश्न<br>
<textarea name="questions" required style="width:100%;padding:8px"></textarea><br><br>

प्लान चुनें<br>

<select name="plan" style="width:100%;padding:8px">

<option value="₹51 – बेसिक प्लान">₹51 – बेसिक प्लान</option>
<option value="₹151 – एडवांस प्लान">₹151 – एडवांस प्लान</option>
<option value="₹251 – प्रो प्लान">₹251 – प्रो प्लान</option>
<option value="₹501 – अल्टीमेट प्लान">₹501 – अल्टीमेट प्लान</option>

</select>

<br><br>

हथेली की फोटो<br>
<input type="file" name="images" multiple>

<br><br>

<button style="padding:10px 20px;background:#8b0000;color:white;border:none">
Save Client
</button>

</form>

<br>

<a href="/admin/dashboard">
<button style="background:#555;color:white;padding:10px;border:none;border-radius:6px;">
Back to Dashboard
</button>
</a>

</div>

</body>
</html>
"""

@router.post("/admin/add-client")
async def add_client(
name:str=Form(...),
phone:str=Form(...),
dob:str=Form(...),
birth_time: str = Form(...),
birth_place: str = Form(...),
questions:str=Form(...),
plan:str=Form(...),
images: List[UploadFile] = File(None)
):

    saved_files=[]

    if images:
        for img in images:

            unique_name=f"{uuid.uuid4().hex}_{img.filename}"

            file_path=os.path.join(UPLOAD_DIR,unique_name)

            with open(file_path,"wb") as f:
                f.write(await img.read())

            saved_files.append(unique_name)

    image_names=",".join(saved_files)

    conn=get_db()
    c=conn.cursor()

    client_code=generate_client_code()

    c.execute(
        """
        INSERT INTO clients
        (client_code,name,phone,dob,birth_time,birth_place,questions,plan,images,source,status,payment_status,created_at,priority,ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_code,
            name,
            phone,
            dob,
            birth_time,
            birth_place,
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
