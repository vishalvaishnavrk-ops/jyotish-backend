
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Backend running successfully"}

@app.get("/admin", response_class=HTMLResponse)
def admin_login():
    return '''
    <h2>Admin Login – Achary Vishal Vaishnav</h2>
    <p><b>Username:</b> admin</p>
    <p><b>Password:</b> admin123</p>
    <p>This is TEST MODE admin panel.</p>
    '''
