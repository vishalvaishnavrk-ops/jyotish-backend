from fastapi import FastAPI, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional
import sqlite3, os
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

app = FastAPI()

DB_PATH = "clients.db"
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"

if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)
    
# ---- CREATE FOLDER FIRST ----
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ---- THEN MOUNT ----
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_code TEXT,
        name TEXT,
        phone TEXT,              -- ✅ ADD THIS
        dob TEXT,
        tob TEXT,
        place TEXT,
        plan TEXT,
        questions TEXT,
        images TEXT,
        source TEXT,
        status TEXT,
        payment_status TEXT DEFAULT 'Pending',  -- ✅ ADD THIS
        payment_date TEXT,
        payment_ref TEXT,
        ai_draft TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def ensure_client_code_column():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE clients ADD COLUMN client_code TEXT")
        conn.commit()
    except:
        pass
    conn.close()

ensure_client_code_column()

def ensure_phone_and_payment_columns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE clients ADD COLUMN phone TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE clients ADD COLUMN payment_status TEXT DEFAULT 'Unpaid'")
    except:
        pass
    try:
        c.execute("ALTER TABLE clients ADD COLUMN payment_date TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE clients ADD COLUMN payment_ref TEXT")
    except:
        pass
    conn.commit()
    conn.close()

ensure_phone_and_payment_columns()

# ---------- PAYMENT & PRIORITY COLUMNS ----------
def ensure_payment_columns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    columns = [
        "phone TEXT",
        "payment_status TEXT DEFAULT 'Pending'",
        "payment_date TEXT",
        "payment_ref TEXT",
        "priority INTEGER DEFAULT 99",
        "ai_generated INTEGER DEFAULT 0"
    ]

    for col in columns:
        try:
            c.execute(f"ALTER TABLE clients ADD COLUMN {col}")
        except:
            pass

    conn.commit()
    conn.close()

ensure_payment_columns()

def generate_client_code():
    year = datetime.now(ZoneInfo("Asia/Kolkata")).year
    short_unique = int(time.time()) % 100000   # last 5 digits
    return f"AVV-{year}-{short_unique}"

# ---------- AI GENERATION ENGINE ----------
def generate_ai_draft(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT name, plan, questions FROM clients WHERE id=?", (client_id,))
    data = c.fetchone()

    if not data:
        conn.close()
        return

    name, plan, questions = data

    if "501" in plan:
        q_depth = "Deep karmic and destiny level explanation"
        remedy_level = "Advanced spiritual remedies"
        q_limit = 5
    elif "251" in plan:
        q_depth = "Strategic life guidance"
        remedy_level = "Spiritual + discipline remedies"
        q_limit = 3
    elif "151" in plan:
        q_depth = "Detailed practical explanation"
        remedy_level = "Weekly mantra + routine remedies"
        q_limit = 2
    else:
        q_depth = "Simple direct guidance"
        remedy_level = "Basic daily remedies"
        q_limit = 1

    draft = f"""
Palm Reading Report

Client Name: {name}
Plan: {plan}

Section 1 – Haath ki Sanrachna
Aapke haath ki banavat aapki personality aur decision making ko darshati hai.

Section 2 – Parvat Vishleshan
Mount of Venus – Emotional energy  
Mount of Jupiter – Leadership  
Mount of Saturn – Responsibility  
Mount of Sun – Fame  

Section 3 – Mukhya Rekhayein
Life Line – Jeevan shakti  
Head Line – Soch aur planning  
Heart Line – Emotions  
Fate Line – Career  

Section 4 – Aapke Prashn ka Uttar
Analysis Type: {q_depth}
Allowed Questions: {q_limit}

{questions}

Section 5 – Upay
Remedy Level: {remedy_level}

Antim Sandesh:
Shraddha aur sahi karm se bhagya majboot hota hai.

– आचार्य विशाल वैष्णव
"""

    c.execute("""
        UPDATE clients
        SET ai_draft=?, ai_generated=1
        WHERE id=?
    """, (draft.strip(), client_id))

    conn.commit()
    conn.close()
    
def generate_pdf_report(client_id):

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT client_code,name,phone,plan,ai_draft,created_at FROM clients WHERE id=?", (client_id,))
    data = c.fetchone()
    conn.close()

    if not data:
        return None

    client_code, name, phone, plan, ai_draft, created_at = data

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)
    font_config = FontConfiguration()
    
    html_template = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>

        @page {{
            size: A4;
            margin: 35px;
       
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 11px;
                color: #777;
            }}
        }}

        @font-face {{
            font-family: 'NotoDev';
            src: url('NotoSansDevanagari-Regular.ttf');
        }}

        body {{
            font-family: 'NotoDev';
            color: #2c2c2c;
            background-color: #faf6ef;
            margin: 0;
        }}

        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 190px;
            color: rgba(139,0,0,0.04);
            z-index: -1;
            text-align: center;
            width: 100%;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(to right, #7b0000, #b22222);
            color: white;
            padding: 35px;
            border-radius: 12px;
            margin-bottom: 35px;
        }}

        .title {{
            font-size: 36px;
            font-weight: 700;
            margin-top: 10px;
        }}

        .subtitle {{
            font-size: 17px;
            opacity: 0.95;
            margin-top: 6px;
        }}

        .client-box {{
            background: #fff3e6;
            padding: 20px;
            border-left: 6px solid #d4af37;
            border-radius: 10px;
            margin-bottom: 30px;
        }} 
        
        .section-title {{
            font-size: 26px;
            font-weight: 700;
            color: #7b0000;
            margin-bottom: 30px;
            border-bottom: 3px solid #d4af37;
            padding-bottom: 10px;
        }}

        .section-block {{
            background: linear-gradient(to bottom, #fffdf9, #fff4dd);
            padding: 22px;
            border-left: 6px solid #b8860b;
            border-radius: 8px;
            margin-bottom: 30px;
            page-break-inside: avoid;
            box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        }}

        .report-content {{
            font-size: 16px;
            line-height: 1.9;
            text-align: justify;
        }}

        .page {{
            position: relative;
            width: 100%;
            height: 1000px;   /* FIXED HEIGHT */
            padding: 40px;
            box-sizing: border-box;
            border: 2px solid #c6a74d;
            background: linear-gradient(to bottom, #fffdf9, #fff6e8);
            page-break-after: always;
        }}

        .page-content {{
            padding-bottom: 80px;
        }}

        .footer {{
            position: absolute;
            bottom: 25px;
            left: 40px;
            right: 40px;
            text-align: center;
            font-size: 12px;
            color: #777;
        }}

        .footer hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin-bottom: 10px;
        }} 
        
        </style>
    </head>

    <body>

    <div class="watermark">ॐ</div>

    <!-- PAGE 1 -->
    <div class="page">

        <div class="page-content">

            <div class="header">
                <img src="ganesha.png" style="width:100%; border-radius:8px; margin-bottom:25px;">

                <div class="title">आचार्य विशाल वैष्णव</div>
                <div class="subtitle">हस्तरेखा विशेषज्ञ एवं वैदिक ज्योतिषज्ञ</div>
            </div>

            <div class="client-box">
                <b>Client Code:</b> {client_code}<br>
                <b>Name:</b> {name}<br>
                <b>Mobile:</b> {phone}<br>
                <b>Plan:</b> {plan}<br>
                <b>Date:</b> {created_at}
            </div>

        </div>

        <div class="footer">
            <hr>
            © 2026 आचार्य विशाल वैष्णव | All Rights Reserved <br>
            WhatsApp: +91-6000376976
        </div>

    </div>


    <!-- PAGE 2 -->
    <div class="page">

        <div class="page-content">

            <div class="section-title">Palm Reading Detailed Report</div>

            <div class="report-content">
                {report_text}
            </div>

        </div>

        <div class="footer">
            <hr>
            © 2026 आचार्य विशाल वैष्णव | All Rights Reserved <br>
            WhatsApp: +91-6000376976
        </div>

    </div>
        
    </body>
    </html>
    """

    sections = ai_draft.split("Section")

    formatted_blocks = ""

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        formatted_blocks += f"""
        <div class="section-block">
            {sec.replace("\n", "<br>")}
        </div>
        """

    html_content = html_template.format(
        client_code=client_code,
        name=name,
        phone=phone,
        plan=plan,
        created_at=created_at,
        report_text = formatted_blocks
    )

    HTML(string=html_content, base_url=os.getcwd()).write_pdf(
        file_path,
        font_config=font_config
    )

    return file_name

# ---------- HELPERS ----------
def get_db():
    return sqlite3.connect(DB_PATH)

# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "Backend with Database running"}

# ---------- ADMIN LOGIN ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
<html>
<head>
<title>Admin Login</title>
<style>
body{
  font-family: Arial, sans-serif;
  background: #f6efe9;
}
.login-box{
  width: 360px;
  margin: 120px auto;
  padding: 25px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 0 12px rgba(0,0,0,0.15);
}
.login-box h2{
  text-align: center;
  color: #8b0000;
}
.login-box input{
  width: 100%;
  padding: 8px;
  margin-top: 6px;
}
.login-box button{
  width: 100%;
  margin-top: 15px;
  padding: 10px;
  background: #8b0000;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}
</style>
</head>

<body>
<div class="login-box">
  <h2>Admin Login</h2>
  <form method="post" action="/admin/login">
    Username:
    <input name="username" required>
    Password:
    <input type="password" name="password" required>
    <button type="submit">Login</button>
  </form>
</div>
</body>
</html>
"""

@app.post("/admin/login")
def admin_login_post(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        return RedirectResponse("/admin/dashboard", status_code=302)
    return HTMLResponse("<h3>Invalid Login</h3>")

# ---------- DASHBOARD ----------
@app.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(
    q: str = Query(None),
    plan: str = Query(None),
    source: str = Query(None),
    status: str = Query(None),
    payment: str = Query(None),   # 🔥 ADD THIS
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    
    conn = get_db()
    c = conn.cursor()

    sql = "SELECT id,client_code,name,phone,plan,source,status,created_at,payment_status,priority FROM clients WHERE 1=1"
    params = []

    if q:
        sql += " AND (name LIKE ? OR client_code LIKE ? OR phone LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if plan:
        sql += " AND plan=?"
        params.append(plan)

    if source:
        sql += " AND source=?"
        params.append(source)

    if status:
        sql += " AND status=?"
        params.append(status)

    if payment:
        sql += " AND payment_status=?"
        params.append(payment)

    if start_date:
        sql += " AND created_at >= ?"
        params.append(start_date + " 00:00:00")

    if end_date:
        sql += " AND created_at <= ?"
        params.append(end_date + " 23:59:59")

    sql += " ORDER BY priority ASC, id DESC"

    c.execute(sql, params)
    rows_db = c.fetchall()
    conn.close()

    rows = ""
    for r in rows_db:

        # r index mapping:
        # 0=id
        # 1=client_code
        # 2=name
        # 3=phone
        # 4=plan
        # 5=source
        # 6=status
        # 7=created_at
        # 8=payment_status
        # 9=priority

        payment_status = r[8]

        if payment_status == "Paid":
            payment_badge = "🟢 Paid"
        else:
            payment_badge = f"""
            🔴 Pending
            <form method="post" action="/admin/mark-paid/{r[0]}" style="display:inline;">
                <button style="background:#28a745;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;">
                    Mark Paid
                </button>
            </form>
            """

        dt = datetime.strptime(r[7], "%Y-%m-%d %H:%M:%S")
        formatted_date = dt.strftime("%d-%m-%Y %I:%M %p")

        rows += f"""
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
<head>
<title>Admin Dashboard</title>
<style>
body {{
  font-family: Arial, sans-serif;
  background: #f6efe9;
  margin: 0;
  padding: 0;
}}

.header {{
  background: #8b0000;
  color: white;
  padding: 15px 25px;
  font-size: 20px;
}}

.header-inner{{
  text-align: center;
}}

.header .title{{
  font-size: 22px;
  font-weight: bold;
}}

.header .subtitle{{
  font-size: 14px;
  margin-top: 4px;
  opacity: 0.9;
}}

.header span {{
  font-size: 14px;
  display: block;
  opacity: 0.9;
}}

.container {{
  padding: 25px;
}}

.top-actions {{
  margin-bottom: 15px;
}}

.top-actions a {{
  background: #8b0000;
  color: white;
  padding: 8px 14px;
  text-decoration: none;
  border-radius: 5px;
  font-size: 14px;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 0 10px rgba(0,0,0,0.1);
}}

th {{
  background: #f1e2d3;
  color: #333;
  padding: 10px;
  text-align: left;
}}

td {{
  padding: 10px;
  border-top: 1px solid #ddd;
}}

tr:hover {{
  background: #faf3ec;
}}

.status-pending {{
  color: #d35400;
  font-weight: bold;
}}

.status-completed {{
  color: green;
  font-weight: bold;
}}

.status-reviewed {{
  color: #2980b9;
  font-weight: bold;
}}

.action-link {{
  color: #8b0000;
  text-decoration: none;
  font-weight: bold;
}}

</style>
</head>

<body>

<div class="header">
  <div class="header-inner">
    <div class="title">ADMIN DASHBOARD</div>
    <div class="subtitle">
      आचार्य विशाल वैष्णव – हस्तरेखा विशेषज्ञ एवं वैदिक ज्योतिषज्ञ
    </div>
  </div>
</div>


<div class="container">

  <div class="top-actions">
    <a href="/admin/add-client">➕ Add New Client (Manual)</a>
  </div>

<form method="get" style="margin-bottom:15px;">
  <input type="text" name="q" placeholder="Client Code / Name" value="{q or ''}">

  <select name="plan">
  <option value="" {"selected" if not plan else ""}>All Plans</option>
  <option value="₹51 – बेसिक प्लान" {"selected" if plan=="₹51 – बेसिक प्लान" else ""}>₹51 – बेसिक प्लान</option>
  <option value="₹151 – एडवांस प्लान" {"selected" if plan=="₹151 – एडवांस प्लान" else ""}>₹151 – एडवांस प्लान</option>
  <option value="₹251 – प्रो प्लान" {"selected" if plan=="₹251 – प्रो प्लान" else ""}>₹251 – प्रो प्लान</option>
  <option value="₹501 – अल्टीमेट प्लान" {"selected" if plan=="₹501 – अल्टीमेट प्लान" else ""}>₹501 – अल्टीमेट प्लान</option>
</select>

  <select name="source">
  <option value="" {"selected" if not source else ""}>All Sources</option>
  <option value="Website" {"selected" if source=="Website" else ""}>Website</option>
  <option value="Manual" {"selected" if source=="Manual" else ""}>Manual</option>
</select>

  <select name="status">
  <option value="" {"selected" if not status else ""}>All Status</option>
  <option value="Pending" {"selected" if status=="Pending" else ""}>Pending</option>
  <option value="Reviewed" {"selected" if status=="Reviewed" else ""}>Reviewed</option>
  <option value="Completed" {"selected" if status=="Completed" else ""}>Completed</option>
</select>

  <select name="payment">
  <option value="" {"selected" if not payment else ""}>All Payment</option>
  <option value="Pending" {"selected" if payment=="Pending" else ""}>Pending</option>
  <option value="Paid" {"selected" if payment=="Paid" else ""}>Paid</option>
</select>

  <input type="date" name="start_date" value="{start_date or ''}">
  <input type="date" name="end_date" value="{end_date or ''}">
  
  <button type="submit">Filter</button>
</form>

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

# ---------- MANUAL CLIENT ENTRY ----------
@app.get("/admin/add-client", response_class=HTMLResponse)
def add_client_form():
    return """
<html>
<head>
<title>Add Client</title>
<style>
body{
  font-family: Arial;
  background:#f6efe9;
}
.form-box{
  width:600px;
  margin:40px auto;
  background:#fff;
  padding:25px;
  border-radius:10px;
  box-shadow:0 0 12px rgba(0,0,0,0.15);
}
.form-box h2{
  text-align:center;
  color:#8b0000;
}
.form-box label{
  font-weight:bold;
}
.form-box input,
.form-box textarea,
.form-box select{
  width:100%;
  padding:8px;
  margin-top:5px;
  margin-bottom:12px;
}
.form-box button{
  background:#8b0000;
  color:white;
  padding:10px;
  border:none;
  width:100%;
  border-radius:5px;
  cursor:pointer;
}
.back-link{
  text-align:center;
  margin-top:10px;
}
</style>
</head>

<body>

<div class="form-box">
<h2>नया क्लाइंट जोड़ें (Manual)</h2>

<form method="post" action="/admin/add-client" enctype="multipart/form-data">

<label>नाम</label>
<input name="name" required>

<label>मोबाइल नंबर *</label>
<input name="phone" required>

<label>जन्म तिथि</label>
<input name="dob" required>

<label>जन्म समय (Optional)</label>
<input name="tob">

<label>जन्म स्थान (Optional)</label>
<input name="place">

<label>मुख्य प्रश्न</label>
<textarea name="questions" required></textarea>

<label>प्लान चुनें</label>
<select name="plan">
  <option value="₹51 – बेसिक प्लान">₹51 – बेसिक प्लान</option>
  <option value="₹151 – एडवांस प्लान">₹151 – एडवांस प्लान</option>
  <option value="₹251 – प्रो प्लान">₹251 – प्रो प्लान</option>
  <option value="₹501 – अल्टीमेट प्लान">₹501 – अल्टीमेट प्लान</option>
</select>

<label>हथेली की फोटो</label>
<input type="file" name="images" multiple>

<button type="submit">सेव करें</button>
</form>

<div class="back-link">
<a href="/admin/dashboard">⬅ डैशबोर्ड पर जाएँ</a>
</div>

</div>

</body>
</html>
"""

@app.post("/admin/add-client")
async def add_client(
    name: str = Form(...),
    phone: str = Form(...),      # ✅ ADD
    dob: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    questions: str = Form(...),
    plan: str = Form(...),
    images: List[UploadFile] = File(...)
):
    
    saved_files = []

    for img in images:
        unique_name = f"{uuid.uuid4().hex}_{img.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
             f.write(await img.read())
        saved_files.append(unique_name)

    image_names = ",".join(saved_files)

    conn = get_db()
    c = conn.cursor()

    client_code = generate_client_code()

    c.execute("""
    INSERT INTO clients
    (client_code,name,phone,dob,tob,place,plan,questions,images,
     source,status,payment_status,payment_date,payment_ref,
     ai_draft,created_at,priority,ai_generated)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        client_code,
        name,
        phone,
        dob,
        tob,
        place,
        plan,
        questions,
        image_names,
        "Manual",
        "Pending",          # status
        "Pending",           # payment_status
        None,               # payment_date
        None,               # payment_ref
        "AI draft pending", # ai_draft
        datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        99,                 # priority
        0                   # ai_generated
    ))

    conn.commit()
    conn.close()

    return RedirectResponse("/admin/dashboard", status_code=302)

# ---------- CLIENT DETAIL ----------
@app.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    cdata = c.fetchone()
    conn.close()

    # ✅ ---- ADD THIS BLOCK HERE ----
    images_html = ""
    if cdata[9]:
        for img in cdata[9].split(","):
            img = img.strip()
            if img:
                images_html += f'<img src="/uploads/{img}" width="150" style="margin:5px;border:1px solid #ccc;">'
    # ✅ ---- END BLOCK ----

    return f"""
    <html>

<head>
<title>Client Detail</title>
<style>
body {{
  font-family: Arial, sans-serif;
  background: #f6efe9;
  margin: 0;
  padding: 0;
}}

.header {{
  background: #8b0000;
  color: white;
  padding: 15px;
  text-align: center;
}}

.container {{
  padding: 25px;
}}

.card {{
  background: #ffffff;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 0 12px rgba(0,0,0,0.15);
  margin-bottom: 20px;
}}

.card h3 {{
  color: #8b0000;
  border-bottom: 1px solid #ddd;
  padding-bottom: 5px;
}}

.label {{
  font-weight: bold;
}}

textarea {{
  width: 100%;
  padding: 10px;
  margin-top: 8px;
}}

select {{
  padding: 6px;
  margin-top: 5px;
}}

button {{
  background: #8b0000;
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}}

.back-link {{
  text-align: center;
  margin-top: 15px;
}}
</style>
</head>

<body>

<div class="header">
  क्लाइंट विवरण – आचार्य विशाल वैष्णव
</div>

<div class="container">

  <div class="card">
  <h3>क्लाइंट जानकारी</h3>
  <p><span class="label">Client Code:</span> <b>{cdata[1]}</b></p>
  <p><span class="label">नाम:</span> {cdata[2]}</p>
  <p><span class="label">मोबाइल:</span> {cdata[3]}</p>
  <p><span class="label">जन्म तिथि:</span> {cdata[4]}</p>
  <p><span class="label">जन्म समय:</span> {cdata[5] or "—"}</p>
  <p><span class="label">जन्म स्थान:</span> {cdata[6] or "—"}</p>
  <p><span class="label">प्लान:</span> {cdata[7]}</p>
  <p><span class="label">Palm Images:</span></p>
  {images_html}

</div>

<div class="card">
<h3>Payment Details</h3>

<p><b>Status:</b> {cdata[12] or "Pending"}</p>
<p><b>Payment Date:</b> {cdata[13] or "-"}</p>
<p><b>Payment Ref:</b> {cdata[14] or "-"}</p>

<form method="post" action="/admin/client/{client_id}/payment">

<label>Update Payment Status:</label><br>
<select name="payment_status">
<option value="Pending">Pending</option>
<option value="Paid">Paid</option>
</select><br><br>

<label>Payment Ref:</label><br>
<input name="payment_ref"><br><br>

<button type="submit">Save Payment</button>

</form>
</div>

  <div class="card">
    <h3>मुख्य प्रश्न</h3>
    <p>{cdata[8]}</p>
  </div>

  <div class="card">
    <h3>AI ड्राफ्ट (Internal Use)</h3>
    <form method="post" action="/admin/client/{client_id}/update">
      <textarea name="ai_draft" rows="10">{cdata[15]}</textarea><br><br>

      <label class="label">Status:</label><br>
      <select name="status">
        <option {"selected" if cdata[11]=="Pending" else ""}>Pending</option>
        <option {"selected" if cdata[11]=="Reviewed" else ""}>Reviewed</option>
        <option {"selected" if cdata[11]=="Completed" else ""}>Completed</option>
      </select><br><br>

      <button type="submit">Save Update</button>
    </form>

    <form method="post" action="/admin/client/{client_id}/generate-ai">
        <button style="background:#007bff;color:white;padding:8px 12px;border:none;border-radius:5px;">
            Generate AI Draft Now
        </button>
    </form>

    <form method="post" action="/admin/client/{client_id}/generate-pdf" style="margin-top:10px;">
        <button style="background:#6f42c1;">
            Generate PDF Report
        </button>
    </form>

    <br><br>
    <a href="/admin/client/{client_id}/pdf" target="_blank">
        <button style="background:#8b0000;">
            Download PDF Report
        </button>
    </a>
  </div>

  <div class="back-link">
    <a href="/admin/dashboard">⬅ डैशबोर्ड पर जाएँ</a>
  </div>

</div>

</body>
</html>
"""

@app.post("/admin/client/{client_id}/update")
def update_client(client_id: int, ai_draft: str = Form(...), status: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE clients SET ai_draft=?, status=? WHERE id=?",
              (ai_draft,status,client_id))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

@app.post("/admin/client/{client_id}/payment")
def update_payment(
    client_id: int,
    payment_status: str = Form(...),
    payment_ref: str = Form(None)
):

    conn = get_db()
    c = conn.cursor()

    payment_date = None
    priority = 99

    if payment_status == "Paid":
        payment_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

        # get plan
        c.execute("SELECT plan FROM clients WHERE id=?", (client_id,))
        plan = c.fetchone()[0]

        if "501" in plan:
            priority = 1
        elif "251" in plan:
            priority = 2
        elif "151" in plan:
            priority = 3
        else:
            priority = 4

        # 🔥 ADD THIS LINE
        generate_ai_draft(client_id)

    c.execute("""
        UPDATE clients
        SET payment_status=?, payment_date=?, payment_ref=?, priority=?
        WHERE id=?
    """, (payment_status, payment_date, payment_ref, priority, client_id))

    conn.commit()
    conn.close()

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

@app.post("/admin/mark-paid/{client_id}")
def mark_paid(client_id: int):

    conn = get_db()
    c = conn.cursor()

    # get plan for priority
    c.execute("SELECT plan FROM clients WHERE id=?", (client_id,))
    plan = c.fetchone()[0]

    priority = 4
    if "501" in plan:
        priority = 1
    elif "251" in plan:
        priority = 2
    elif "151" in plan:
        priority = 3

    payment_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    # update payment
    c.execute("""
        UPDATE clients
        SET payment_status='Paid',
            payment_date=?,
            priority=?
        WHERE id=?
    """, (payment_date, priority, client_id))

    conn.commit()
    conn.close()

    # 🔥🔥🔥 TRIGGER AI AFTER PAYMENT
    generate_ai_draft(client_id)

    return RedirectResponse("/admin/dashboard", status_code=302)

@app.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(client_id: int):
    file_name = generate_pdf_report(client_id)
    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

@app.post("/admin/client/{client_id}/generate-ai")
def manual_ai_generate(client_id: int):
     generate_ai_draft(client_id)
     return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

@app.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id: int):

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT client_code FROM clients WHERE id=?", (client_id,))
    data = c.fetchone()
    conn.close()

    if not data:
        return HTMLResponse("Report not found")

    file_name = f"{data[0]}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    if not os.path.exists(file_path):
        return HTMLResponse("PDF not generated yet.")

    return FileResponse(file_path, media_type='application/pdf', filename=file_name)
     
# ---------- WEBSITE FORM SUBMIT API ----------
@app.post("/api/website-submit")
async def website_submit(
    name: str = Form(...),
    phone: str = Form(...),   # ✅ ADD
    dob: str = Form(...),
    questions: str = Form(...),
    plan: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    images: List[UploadFile] = File(...)
):

    saved_files = []

    for img in images:
        unique_name = f"{uuid.uuid4().hex}_{img.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
             f.write(await img.read())
        saved_files.append(unique_name)

    image_names = ",".join(saved_files)

    conn = get_db()
    c = conn.cursor()

    client_code = generate_client_code()

    c.execute("""
    INSERT INTO clients
    (client_code,name,phone,dob,tob,place,plan,questions,images,
    source,status,payment_status,payment_date,payment_ref,
    ai_draft,created_at,priority,ai_generated)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
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
    ))

    conn.commit()
    conn.close()

    return {
    "success": True,
    "client_code": client_code
    }
