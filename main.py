from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

app = FastAPI()

# In-memory client store (TESTING ONLY)
CLIENTS = []

@app.get("/")
def root():
    return {"status": "Backend v2 running successfully"}

# -------- ADMIN LOGIN --------
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

# -------- DASHBOARD --------
@app.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard():
    rows = ""
    for c in CLIENTS:
        rows += f"<tr><td>{c['name']}</td><td>{c['plan']}</td><td>{c['source']}</td></tr>"

    return f"""
    <h2>Admin Dashboard</h2>
    <a href="/admin/add-client">➕ Add New Client (Manual)</a><br><br>
    <table border="1" cellpadding="6">
        <tr><th>Name</th><th>Plan</th><th>Source</th></tr>
        {rows}
    </table>
    """

# -------- MANUAL CLIENT ENTRY --------
@app.get("/admin/add-client", response_class=HTMLResponse)
def add_client_form():
    return """
    <h2>Add New Client (Manual)</h2>
    <form method="post" action="/admin/add-client" enctype="multipart/form-data">
        Name: <input name="name"><br><br>
        Plan:
        <select name="plan">
            <option>₹51</option>
            <option>₹151</option>
            <option>₹251</option>
            <option>₹501</option>
        </select><br><br>
        Palm Images (4):<br>
        <input type="file" name="images" multiple><br><br>
        <button type="submit">Save Client</button>
    </form>
    """

@app.post("/admin/add-client")
async def add_client(
    name: str = Form(...),
    plan: str = Form(...),
    images: List[UploadFile] = File(...)
):
    CLIENTS.append({
        "name": name,
        "plan": plan,
        "source": "Manual",
        "ai_draft": "DUMMY AI OUTPUT – Testing mode"
    })
    return RedirectResponse("/admin/dashboard", status_code=302)
