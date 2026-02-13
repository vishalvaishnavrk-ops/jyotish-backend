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

app = FastAPI()

DB_PATH = "clients.db"
UPLOAD_DIR = "uploads"

# ---- CREATE FOLDER FIRST ----
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ---- THEN MOUNT ----
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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
        payment_status TEXT DEFAULT 'Unpaid',  -- ✅ ADD THIS
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
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    
    conn = get_db()
    c = conn.cursor()

    sql = "SELECT id,client_code,name,phone,plan,source,status,created_at,payment_status,priority FROM clients WHERE 1=1"
    params = []

    if q:
        sql += " AND (name LIKE ? OR client_code LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    if plan:
        sql += " AND plan=?"
        params.append(plan)

    if source:
        sql += " AND source=?"
        params.append(source)

    if status:
        sql += " AND status=?"
        params.append(status)

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

        payment_badge = "🟢 Paid" if r[8] == "Paid" else "🔴 Pending"

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
        "Unpaid",           # payment_status
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
    if cdata[7]:
        for img in cdata[7].split(","):
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
  <p><span class="label">Client Code:</span> <b>{cdata[12]}</b></p>
  <p><span class="label">नाम:</span> {cdata[1]}</p>
  <p><span class="label">जन्म तिथि:</span> {cdata[2]}</p>
  <p><span class="label">जन्म समय:</span> {cdata[3] or "—"}</p>
  <p><span class="label">जन्म स्थान:</span> {cdata[4] or "—"}</p>
  <p><span class="label">प्लान:</span> {cdata[5]}</p>
  <p><span class="label">Palm Images:</span></p>
  {images_html}

</div>

<div class="card">
<h3>Payment Details</h3>

<p><b>Status:</b> {cdata[14] or "Pending"}</p>
<p><b>Payment Date:</b> {cdata[15] or "-"}</p>
<p><b>Payment Ref:</b> {cdata[16] or "-"}</p>

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
    <p>{cdata[6]}</p>
  </div>

  <div class="card">
    <h3>AI ड्राफ्ट (Internal Use)</h3>
    <form method="post" action="/admin/client/{client_id}/update">
      <textarea name="ai_draft" rows="10">{cdata[10]}</textarea><br><br>

      <label class="label">Status:</label><br>
      <select name="status">
        <option {"selected" if cdata[9]=="Pending" else ""}>Pending</option>
        <option {"selected" if cdata[9]=="Reviewed" else ""}>Reviewed</option>
        <option {"selected" if cdata[9]=="Completed" else ""}>Completed</option>
      </select><br><br>

      <button type="submit">Save Update</button>
    </form>
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

    c.execute("""
        UPDATE clients
        SET payment_status=?, payment_date=?, payment_ref=?, priority=?
        WHERE id=?
    """, (payment_status, payment_date, payment_ref, priority, client_id))

    conn.commit()
    conn.close()

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

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
        "Unpaid",
        None,
        None,
        "AI draft pending",
        datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        99,
        0
    ))

    conn.commit()
    conn.close()

    return {"success": True}
