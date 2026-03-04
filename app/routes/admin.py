from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models import get_clients
from app.database import get_db
from app.services.ai_engine import generate_ai_draft
from app.services.pdf_engine import generate_pdf_report
from app.services.whatsapp_service import generate_whatsapp_link
from fastapi.responses import FileResponse

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

    html = """
    <h2>Clients Dashboard</h2>
    <table border=1>
    <tr>
    <th>Client Code</th>
    <th>Name</th>
    <th>Plan</th>
    <th>Status</th>
    <th>Phone</th>
    </tr>
    """

    for r in rows:

        html += f"""
        <tr>
        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[4]}</td>
        <td>{r[6]}</td>
        <td>{r[3]}</td>
        </tr>
        """

    html += "</table>"

    return HTMLResponse(html)
    
@router.get("/admin/client/{client_id}")
def client_detail(client_id:int):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,client_code,name,phone,ai_draft,status FROM clients WHERE id=%s",(client_id,))
    data = c.fetchone()

    conn.close()

    return data

@router.post("/admin/client/{client_id}/generate-ai")
def ai_generate(client_id:int):

    generate_ai_draft(client_id)

    return {"status":"AI generated"}

@router.post("/admin/client/{client_id}/generate-pdf")
def pdf_generate(client_id:int):

    file = generate_pdf_report(client_id)

    return {"pdf":file}

@router.get("/admin/client/{client_id}/pdf")
def download_pdf(client_id:int):

    conn=get_db()
    c=conn.cursor()

    c.execute("SELECT client_code FROM clients WHERE id=%s",(client_id,))
    code=c.fetchone()[0]

    conn.close()

    path=f"reports/{code}.pdf"

    return FileResponse(path, media_type="application/pdf")
