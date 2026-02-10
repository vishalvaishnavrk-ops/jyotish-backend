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
    c.execute("SELECT id,name,plan,source,status FROM clients ORDER BY id DESC")
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
    <h2>Add New Client (Manual)</h2>
    <form method="post" action="/admin/add-client" enctype="multipart/form-data">
        Name: <input name="name"><br><br>
        DOB: <input name="dob"><br><br>
        TOB: <input name="tob"><br><br>
        Place: <input name="place"><br><br>
        Questions:<br>
        <textarea name="questions"></textarea><br><br>
    P<select name="plan">
        <option value="₹51 – बेसिक प्लान">₹51 – बेसिक प्लान</option>
        <option value="₹151 – एडवांस प्लान">₹151 – एडवांस प्लान</option>
        <option value="₹251 – प्रो प्लान">₹251 – प्रो प्लान</option>
        <option value="₹501 – अल्टीमेट प्लान">₹501 – अल्टीमेट प्लान</option>
    </select><br><br>
        Palm Images:
        <input type="file" name="images" multiple><br><br>
        <button type="submit">Save Client</button>
    </form>
    """

@app.post("/admin/add-client")
async def add_client(
    name: str = Form(...),
    dob: str = Form(...),
    tob: Optional[str] = Form(None),      # optional
    place: Optional[str] = Form(None),    # optional
    questions: str = Form(...),
    plan: str = Form(...),
    images: List[UploadFile] = File(...)
):
    image_names = ",".join([img.filename for img in images])
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO clients
        (name,dob,tob,place,plan,questions,images,source,status,ai_draft,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        name,dob,tob,place,plan,questions,image_names,
        "Manual","Pending","DUMMY AI OUTPUT",
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
    <h2>Client Detail</h2>
    <p><b>Name:</b> {cdata[1]}</p>
    <p><b>DOB:</b> {cdata[2]}</p>
    <p><b>TOB:</b> {cdata[3]}</p>
    <p><b>Place:</b> {cdata[4]}</p>
    <p><b>Plan:</b> {cdata[5]}</p>
    <p><b>Questions:</b><br>{cdata[6]}</p>

    <h3>AI Draft (Internal)</h3>
    <form method="post" action="/admin/client/{client_id}/update">
        <textarea name="ai_draft" rows="10" cols="80">{cdata[10]}</textarea><br><br>
        Status:
        <select name="status">
            <option {"selected" if cdata[9]=="Pending" else ""}>Pending</option>
            <option {"selected" if cdata[9]=="Reviewed" else ""}>Reviewed</option>
            <option {"selected" if cdata[9]=="Completed" else ""}>Completed</option>
        </select><br><br>
        <button type="submit">Save</button>
    </form>
    <br><a href="/admin/dashboard">⬅ Back</a>
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
    c.execute("""
        INSERT INTO clients
        (name,dob,tob,place,plan,questions,images,source,status,ai_draft,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        name, dob, tob, place, plan, questions,
        image_names,
        "Website", "Pending", "AI draft pending",
        datetime.datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

    return {"success": True}
