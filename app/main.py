from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .models import create_client, get_all_clients
from datetime import datetime
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_client_code():
    year = datetime.now().year
    unique = int(time.time()) % 100000
    return f"AVV-{year}-{unique}"

@app.get("/")
def root():
    return {"status": "SaaS Architecture Active"}

@app.get("/test-form", response_class=HTMLResponse)
def test_form():
    return """
    <h2>Add Test Client</h2>
    <form method="post" action="/add-client">
        Name: <input name="name"><br><br>
        Phone: <input name="phone"><br><br>
        Plan: <input name="plan"><br><br>
        <button type="submit">Submit</button>
    </form>
    """

@app.post("/add-client")
def add_client(name: str = Form(...), phone: str = Form(...), plan: str = Form(...)):
    client_code = generate_client_code()
    create_client(client_code, name, phone, plan)
    return {"message": "Client Added", "client_code": client_code}

@app.get("/clients", response_class=HTMLResponse)
def list_clients():
    rows = get_all_clients()
    html = "<h2>Clients</h2><ul>"
    for r in rows:
        html += f"<li>{r}</li>"
    html += "</ul>"
    return html

from .database import get_db

@app.get("/db-test")
def db_test():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    conn.close()
    return {"db": "connected"}
