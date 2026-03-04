from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.database import get_db

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
    <form method="post" action="/admin/login">
    Username:<input name="username">
    Password:<input name="password" type="password">
    <button>Login</button>
    </form>
    """

@router.post("/admin/login")
def admin_login_post(username: str = Form(...), password: str = Form(...)):

    if username == "admin" and password == "admin123":
        return RedirectResponse("/admin/dashboard", status_code=302)

    return HTMLResponse("Invalid Login")


@router.get("/admin/dashboard")
def dashboard():

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,client_code,name,plan,status FROM clients ORDER BY id DESC")
    rows = c.fetchall()

    conn.close()

    html = "<h2>Clients</h2>"

    for r in rows:
        html += f"{r}<br>"

    return HTMLResponse(html)
