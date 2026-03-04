from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from app.database import get_db
from app.services.ai_engine import generate_ai_draft
from app.services.pdf_engine import generate_pdf_report
from app.services.whatsapp_service import generate_whatsapp_link

from datetime import datetime
from zoneinfo import ZoneInfo
import os

router = APIRouter()

# ---------------- ADMIN LOGIN ----------------

@router.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
    <html>
    <body style="font-family:Arial;background:#f6efe9">

    <div style="width:350px;margin:100px auto;background:white;padding:25px;border-radius:10px">

    <h2>Admin Login</h2>

    <form method="post" action="/admin/login">

    Username:<br>
    <input name="username"><br><br>

    Password:<br>
    <input name="password" type="password"><br><br>

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

    return HTMLResponse("Invalid Login")

# ---------------- DASHBOARD ----------------

@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT id,client_code,name,phone,plan,status,created_at
    FROM clients
    ORDER BY priority ASC,id DESC
    """)

    rows = c.fetchall()

    conn.close()

    html = """
    <html>

    <head>

    <title>Admin Dashboard</title>

    <style>

    body{
        font-family:Arial;
        background:#f6efe9;
        padding:20px;
    }

    table{
        width:100%;
        border-collapse:collapse;
        background:white;
    }

    th{
        background:#f1e2d3;
        padding:10px;
    }

    td{
        padding:10px;
        border-top:1px solid #ddd;
    }

    tr:hover{
        background:#faf3ec;
    }

    a{
        color:#8b0000;
        text-decoration:none;
        font-weight:bold;
    }

    </style>

    </head>

    <body>

    <h2>Clients Dashboard</h2>

    <a href="/admin/add-client">
    <button>Add Client</button>
    </a>

    <br><br>

    <table>

    <tr>
    <th>Client Code</th>
    <th>Name</th>
    <th>Plan</th>
    <th>Status</th>
    <th>Phone</th>
    <th>Date</th>
    <th>Action</th>
    </tr>
    """

    for r in rows:

        html += f"""

        <tr>

        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[4]}</td>
        <td>{r[5]}</td>
        <td>{r[3]}</td>
        <td>{r[6]}</td>

        <td>
        <a href="/admin/client/{r[0]}">View</a>
        </td>

        </tr>
        """

    html += "</table></body></html>"

    return HTMLResponse(html)

# ---------------- CLIENT DETAIL ----------------

@router.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s",(client_id,))
    data=c.fetchone()

    conn.close()

    images_html=""

    if data[9]:

        for img in data[9].split(","):

            images_html += f'<img src="/uploads/{img}" width="150">'

    html=f"""

    <h2>Client Detail</h2>

    <b>Client Code:</b> {data[1]} <br>
    <b>Name:</b> {data[2]} <br>
    <b>Phone:</b> {data[3]} <br>
    <b>Plan:</b> {data[7]} <br>

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

    <a href="/admin/client/{client_id}/pdf">
    Download PDF
    </a>

    <br><br>

    <a href="/admin/dashboard">Back</a>

    """

    return HTMLResponse(html)

# ---------------- AI GENERATE ----------------

@router.post("/admin/client/{client_id}/generate-ai")
def ai_generate(client_id:int):

    generate_ai_draft(client_id)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)

# ---------------- PDF GENERATE ----------------

@router.post("/admin/client/{client_id}/generate-pdf")
def pdf_generate(client_id:int):

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)

# ---------------- DOWNLOAD PDF ----------------

@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT client_code FROM clients WHERE id=%s",(client_id,))
    code=c.fetchone()[0]

    conn.close()

    path=f"reports/{code}.pdf"

    return FileResponse(path, media_type="application/pdf")
