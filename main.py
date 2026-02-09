from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List
import sqlite3, os, datetime

app = FastAPI()

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
    <h2>Admin Login – Achary Vishal Vaishnav</h2>
    <form method="post" action="/admin/login">
        Username: <input name="username"><br><br>
        Password: <input type="password" name="password"><br><br>
        <button type="submit">Login</button>
    </form>
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
    <h2>Admin Dashboard</h2>
    <a href="/admin/add-client">➕ Add New Client (Manual)</a><br><br>
    <table border="1" cellpadding="6">
        <tr><th>Name</th><th>Plan</th><th>Source</th><th>Status</th><th>Action</th></tr>
        {rows}
    </table>
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
        Plan:
        <select name="plan">
            <option>₹51</option>
            <option>₹151</option>
            <option>₹251</option>
            <option>₹501</option>
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
    tob: str = Form(...),
    place: str = Form(...),
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
