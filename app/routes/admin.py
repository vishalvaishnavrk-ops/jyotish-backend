from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models import get_clients

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
    <form method="post" action="/admin/login">
    Username:<input name="username"><br>
    Password:<input name="password" type="password"><br>
    <button>Login</button>
    </form>
    """

@router.post("/admin/login")
def admin_login_post(username: str = Form(...), password: str = Form(...)):

    if username == "admin" and password == "admin123":
        return RedirectResponse("/admin/dashboard", status_code=302)

    return HTMLResponse("Invalid Login")

@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard():

    rows = get_clients()

    html = "<h2>Clients</h2>"

    for r in rows:
        html += f"{r}<br>"

    return html
