from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

app = FastAPI()

# In-memory store (TESTING)
CLIENTS = []

@app.get("/")
def root():
    return {"status": "Backend v3 running successfully"}

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
    for idx, c in enumerate(CLIENTS):
        rows += f"""
        <tr>
            <td>{c['name']}</td>
            <td>{c['plan']}</td>
            <td>{c['source']}</td>
            <td><a href="/admin/client/{idx}">View</a></td>
        </tr>
        """
    return f"""
    <h2>Admin Dashboard</h2>
    <a href="/admin/add-client">➕ Add New Client (Manual)</a><br><br>
    <table border="1" cellpadding="6">
        <tr><th>Name</th><th>Plan</th><th>Source</th><th>Action</th></tr>
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
        Palm Images (4):
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
        "status": "Pending",
        "ai_draft": "DUMMY AI OUTPUT – Palm + Jyotish analysis will appear here."
    })
    return RedirectResponse("/admin/dashboard", status_code=302)

# -------- CLIENT DETAIL PAGE --------
@app.get("/admin/client/{client_id}", response_class=HTMLResponse)
def client_detail(client_id: int):
    c = CLIENTS[client_id]
    return f"""
    <h2>Client Detail</h2>
    <p><b>Name:</b> {c['name']}</p>
    <p><b>Plan:</b> {c['plan']}</p>
    <p><b>Source:</b> {c['source']}</p>
    <p><b>Status:</b> {c['status']}</p>

    <h3>AI Draft (Internal)</h3>
    <form method="post" action="/admin/client/{client_id}/update">
        <textarea name="ai_draft" rows="10" cols="80">{c['ai_draft']}</textarea><br><br>
        Status:
        <select name="status">
            <option {"selected" if c['status']=="Pending" else ""}>Pending</option>
            <option {"selected" if c['status']=="Reviewed" else ""}>Reviewed</option>
            <option {"selected" if c['status']=="Completed" else ""}>Completed</option>
        </select><br><br>
        <button type="submit">Save</button>
    </form>
    <br>
    <a href="/admin/dashboard">⬅ Back to Dashboard</a>
    """

@app.post("/admin/client/{client_id}/update")
def update_client(client_id: int, ai_draft: str = Form(...), status: str = Form(...)):
    CLIENTS[client_id]["ai_draft"] = ai_draft
    CLIENTS[client_id]["status"] = status
    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)
