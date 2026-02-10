from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional
import sqlite3, os, datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "clients.db"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        dob TEXT,
        tob TEXT,
        place TEXT,
        plan TEXT,
        questions TEXT,
        images TEXT,
        source TEXT,
        status TEXT,
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

def generate_client_code():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clients")
    count = c.fetchone()[0] + 1
    conn.close()

    year = datetime.datetime.now().year
    return f"AVV-{year}-{str(count).zfill(4)}"

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
def dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id,client_code,name,plan,source,status FROM clients ORDER BY id DESC")
    rows_db = c.fetchall()
    conn.close()

    rows = ""
    for r in rows_db:
        rows += f"""
        <tr>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
            <td>{r[4]}</td>
            <td>{r[5]}</td>
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

  <table>
    <tr>
      <th>Client Code</th>
      <th>Name</th>
      <th>Plan</th>
      <th>Source</th>
      <th>Status</th>
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
    dob: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    questions: str = Form(...),
    plan: str = Form(...),
    images: List[UploadFile] = File(...)
):
    image_names = ",".join([img.filename for img in images])
    conn = get_db()
    c = conn.cursor()

    client_code = generate_client_code()

    c.execute("""
        INSERT INTO clients
        (client_code,name,dob,tob,place,plan,questions,images,source,status,ai_draft,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        client_code, name, dob, tob, place, plan, questions, image_names,
        "Manual", "Pending", "DUMMY AI OUTPUT",
        datetime.datetime.now().isoformat()
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
    <p><span class="label">नाम:</span> {cdata[1]}</p>
    <p><span class="label">जन्म तिथि:</span> {cdata[2]}</p>
    <p><span class="label">जन्म समय:</span> {cdata[3] or "—"}</p>
    <p><span class="label">जन्म स्थान:</span> {cdata[4] or "—"}</p>
    <p><span class="label">प्लान:</span> {cdata[5]}</p>
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

# ---------- WEBSITE FORM SUBMIT API ----------
@app.post("/api/website-submit")
async def website_submit(
    name: str = Form(...),
    dob: str = Form(...),
    questions: str = Form(...),
    plan: str = Form(...),
    tob: Optional[str] = Form(None),      # ✅ optional
    place: Optional[str] = Form(None),    # ✅ optional
    images: List[UploadFile] = File(...)
):
    # Save only filenames for now (storage later)
    image_names = ",".join([img.filename for img in images])

    conn = get_db()
    c = conn.cursor()
    
    client_code = generate_client_code()
    
    c.execute("""
    INSERT INTO clients
    (client_code,name,dob,tob,place,plan,questions,images,source,status,ai_draft,created_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    client_code, name, dob, tob, place, plan, questions,
    image_names,
    "Website", "Pending", "AI draft pending",
    datetime.datetime.now().isoformat()
))

    conn.commit()
    conn.close()

    return {"success": True}
