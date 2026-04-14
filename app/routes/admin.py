from fastapi import APIRouter, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi import Request
from typing import List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import uuid
import os
import urllib.parse

from app.database import get_db
from app.utils.helpers import generate_client_code
from app.services.ai_engine import generate_ai_draft
from app.services.pdf_engine import generate_pdf_report
from app.services.supabase_storage import upload_palm_image
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined   # 👈 ADD THIS
from app.auth import verify_admin

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

templates.env.undefined = StrictUndefined   # 👈 ADD THIS

def render_template_safe(request: Request, template_name: str, context: dict = None):
    context = context or {}
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            **context
        }
    )
    
router = APIRouter()

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"

# 🔥 ADD THIS FUNCTION HERE
def trigger_ai_generation(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT payment_status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    if not data:
        return

    payment_status = data[0]

    # ❌ only block if NOT paid
    if payment_status != "Paid":
        return

    try:
        print(f"🔥 AI STARTED for {client_id}")

        generate_ai_draft(client_id)

        # ✅ mark success AFTER generation
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE clients SET ai_generated=1 WHERE id=%s", (client_id,))
        conn.commit()
        conn.close()

        print(f"✅ AI SUCCESS for {client_id}")

    except Exception as e:
        print("❌ AI ERROR:", e)
        
# ---------- ADMIN LOGIN ----------
@router.get("/admin")
def admin_root():
    return RedirectResponse(url="/admin/login")
    
@router.get("/admin/login")
def login_page(request: Request):
    return render_template_safe(request, "admin/login.html")


@router.post("/admin/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):

    if verify_admin(username, password):
        request.session["admin"] = True
        request.session["last_active"] = datetime.now().isoformat()
        return RedirectResponse("/admin/dashboard", status_code=302)

    return render_template_safe(request, "admin/login.html", {
        "error": "Invalid credentials"
    })
    
SESSION_TIMEOUT = 30  # minutes

def check_admin(request: Request):

    if "admin" not in request.session:
        return RedirectResponse("/admin/login")

    # 🔥 idle timeout check
    last_active = request.session.get("last_active")

    if last_active:
        last_active_time = datetime.fromisoformat(last_active)

        if datetime.now() - last_active_time > timedelta(minutes=SESSION_TIMEOUT):
            request.session.clear()
            return RedirectResponse("/admin/login")

    # 🔥 update activity time
    request.session["last_active"] = datetime.now().isoformat()

    return None
        
@router.get("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)
    
# ---------- DASHBOARD ----------
@router.get("/admin/dashboard")
def dashboard(request: Request,
q: str = Query(None),
plan: str = Query(None),
source: str = Query(None),
status: str = Query(None),
payment: str = Query(None),
start_date: str = Query(None),
end_date: str = Query(None)
):
    auth = check_admin(request)
    if auth:
        return auth
        
    conn = get_db()
    c = conn.cursor()

    sql = """
    SELECT id,client_code,name,phone,plan,source,status,created_at,payment_status,priority
    FROM clients
    WHERE 1=1
    """

    params=[]

    if q:
        sql+=" AND (name ILIKE %s OR client_code ILIKE %s OR phone ILIKE %s)"
        params.extend([f"%{q}%",f"%{q}%",f"%{q}%"])

    if plan:
        sql+=" AND plan=%s"
        params.append(plan)

    if source:
        sql+=" AND source=%s"
        params.append(source)

    if status:
        sql+=" AND status=%s"
        params.append(status)

    if payment:
        sql+=" AND payment_status=%s"
        params.append(payment)

    if start_date:
        sql+=" AND created_at >= %s"
        params.append(start_date+" 00:00:00")

    if end_date:
        sql+=" AND created_at <= %s"
        params.append(end_date+" 23:59:59")

    sql += """
    ORDER BY
    CASE
    WHEN payment_status='Paid' AND status='Reviewed' THEN 1
    WHEN payment_status='Paid' AND status='Pending' THEN 2
    WHEN payment_status='Pending' THEN 3
    WHEN status='Completed' THEN 4
    ELSE 5
    END,
    priority ASC,
    created_at DESC
    """

    c.execute(sql,params)
    rows_db=c.fetchall()
    conn.close()


    rows=""

    for r in rows_db:

        dt=datetime.strptime(str(r[7])[:19],"%Y-%m-%d %H:%M:%S")
        formatted_date=dt.strftime("%d-%m-%Y %I:%M %p")

        if r[8]=="Paid":
            payment_badge="🟢 Paid"
        else:
            payment_badge=f"""
🔴 Pending
<form method="post" action="/admin/mark-paid/{r[0]}" style="display:inline;">
<button style="background:#28a745;color:white;border:none;padding:4px 8px;border-radius:4px">
Mark Paid
</button>
</form>
"""

        rows+=f"""
<tr>
<td>{r[1]}</td>
<td>{r[2]}</td>
<td>{r[4]}</td>
<td>{r[5]}</td>
<td>{r[6]}</td>
<td>{r[3]}</td>
<td>{payment_badge}</td>
<td>{formatted_date}</td>
<td><a href="/admin/client/{r[0]}">View</a></td>
</tr>
"""

    return render_template_safe(request, "admin/dashboard.html",
        {
            "clients": rows_db,
            "total_clients": len(rows_db),
            "pending_payment": sum(1 for r in rows_db if r[8] != "Paid"),
            "completed_reports": sum(1 for r in rows_db if r[6] == "Completed"),
            "reviewed_reports": sum(1 for r in rows_db if r[6] == "Reviewed"),
            "pending_reports": sum(
                1 for r in rows_db
                if r[8] == "Paid" and r[6] == "Pending"
            ),

            "total_revenue": sum(
                501 if "501" in r[4] else
                251 if "251" in r[4] else
                151 if "151" in r[4] else
                51
                for r in rows_db if r[8] == "Paid"
            ),

            # FILTER VALUES RETURN
            "q": q,
            "plan": plan,
            "source": source,
            "status": status,
            "payment": payment,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


# ---------- MARK PAID ----------
@router.post("/admin/mark-paid/{client_id}")
def mark_paid(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth
        
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT plan FROM clients WHERE id=%s",(client_id,))
    plan=c.fetchone()[0]

    priority=4

    if "501" in plan:
        priority=1
    elif "251" in plan:
        priority=2
    elif "151" in plan:
        priority=3

    payment_date=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    UPDATE clients
    SET payment_status='Paid',payment_date=%s,priority=%s
    WHERE id=%s
    """,(payment_date,priority,client_id))

    conn.commit()
    conn.close()

    trigger_ai_generation(client_id)
    
    return RedirectResponse("/admin/dashboard",status_code=302)

# ---------- CLIENT DETAIL ----------
@router.get("/admin/client/{client_id}")
def client_detail(request: Request, client_id: int):
    auth = check_admin(request)
    if auth:
        return auth

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM clients WHERE id=%s", (client_id,))
    cdata = c.fetchone()
    conn.close()

    if not cdata:
        return HTMLResponse("Client not found")

    # ---------- SAFE IMAGES ----------
    images_list = []

    images_raw = cdata[9] if cdata[9] else ""

    if isinstance(images_raw, str):
        for img in images_raw.split(","):
            img = img.strip()
            if img:
                images_list.append(img)   # ✅ direct URL
            
    # ---------- SAFE CLIENT ----------
    client = {
        "id": int(cdata[0]),
        "client_code": str(cdata[1]),
        "name": str(cdata[2]),
        "phone": str(cdata[3]),
        "plan": str(cdata[7]),
        "status": str(cdata[11]),
        "payment_status": str(cdata[12]),
        "payment_date": str(cdata[13]) if cdata[13] else "",
        "payment_ref": str(cdata[14]) if cdata[14] else "",
        "ai_draft": str(cdata[15]) if cdata[15] else "",
        "ai_generated": int(cdata[17]) if len(cdata) > 17 and cdata[17] else 0,
        "pdf_url": str(cdata[19]).strip() if len(cdata) > 19 and cdata[19] else None,
    }

    # ---------- FLAGS ----------
    status = client["status"]

    pdf_url = client.get("pdf_url")

    if isinstance(pdf_url, str):
        pdf_url = pdf_url.strip()
    
    print("DEBUG PDF_URL RAW:", repr(client.get("pdf_url")))
    print("DEBUG PDF_URL CLEAN:", repr(pdf_url))
    
    pdf_ready = bool(pdf_url) and pdf_url.startswith("http")

    can_generate_pdf = (
        client["payment_status"] == "Paid"
        and status == "Reviewed"
        and not pdf_ready
    )
    
    context = {
        "client": client,
        "images": images_list,
        "can_generate_ai": client["payment_status"] == "Paid" and client["ai_generated"] == 0,
        "can_generate_pdf": can_generate_pdf,
        "pdf_ready": pdf_ready,
    }

    return render_template_safe(request, "admin/client_detail.html", context)
    
# ---------- UPDATE PAYMENT ----------
@router.post("/admin/client/{client_id}/payment")
def update_payment(
    client_id: int,
    payment_status: str = Form(...),
    payment_ref: str = Form(None)
):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT plan, ai_generated FROM clients WHERE id=%s",(client_id,))
    row = c.fetchone()
    plan = row[0]
    ai_generated = row[1] if row[1] is not None else 0

    payment_date = None
    priority = 99

    if payment_status == "Paid":

        payment_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

        if "501" in plan:
            priority = 1
        elif "251" in plan:
            priority = 2
        elif "151" in plan:
            priority = 3
        else:
            priority = 4

    c.execute("""
        UPDATE clients
        SET payment_status=%s,
            payment_date=%s,
            payment_ref=%s,
            priority=%s
        WHERE id=%s
    """,(payment_status,payment_date,payment_ref,priority,client_id))

    conn.commit()
    conn.close()

    # AI draft only first time
    if payment_status == "Paid":
        trigger_ai_generation(client_id)
    
    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)
    
# ---------- UPDATE CLIENT ----------
@router.post("/admin/client/{client_id}/update")
def update_client(client_id:int, ai_draft:str=Form(...), status:str=Form(...)):

    conn=get_db()
    c=conn.cursor()

    c.execute(
        "UPDATE clients SET ai_draft=%s,status=%s WHERE id=%s",
        (ai_draft,status,client_id)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(f"/admin/client/{client_id}",status_code=302)


# ---------- GENERATE AI ----------
@router.post("/admin/client/{client_id}/generate-ai")
def manual_ai_generate(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth
        
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT payment_status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    payment_status = data[0]

    if payment_status != "Paid":
        return HTMLResponse("Payment required")

    try:
        trigger_ai_generation(client_id)
    except Exception as e:
        print("MANUAL ERROR:", e)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)
    
# ---------- GENERATE PDF ----------
@router.post("/admin/client/{client_id}/generate-pdf")
def create_pdf(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth
        
    conn = get_db()
    c = conn.cursor()

    # ✅ status check
    c.execute("SELECT status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    # 🔥 NEW ADD (duplicate PDF prevent)
    c.execute("SELECT pdf_url FROM clients WHERE id=%s", (client_id,))
    existing = c.fetchone()

    if existing and existing[0]:
        conn.close()
        return RedirectResponse(f"/admin/client/{client_id}", status_code=302)

    conn.close()

    if data[0] not in ["Reviewed", "Completed"]:
        return HTMLResponse(
            "<h3 style='color:red;text-align:center;margin-top:80px;'>Review required before PDF generation</h3>"
        )

    generate_pdf_report(client_id)

    return RedirectResponse(f"/admin/client/{client_id}", status_code=302)
    
# ---------- DOWNLOAD PDF ----------
@router.get("/admin/client/{client_id}/pdf")
def download_pdf(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT pdf_url, status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    if not data or not data[0]:
        return HTMLResponse("PDF not generated yet")

    pdf_url = data[0]

    return RedirectResponse(pdf_url)

# ---------- SEND WHATSAPP ----------
@router.get("/admin/client/{client_id}/send-whatsapp")
def send_whatsapp(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth
        
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT name, phone, client_code, status FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    if not data:
        conn.close()
        return HTMLResponse("Client not found")

    name, phone_number, client_code, status = data

    # ❌ Block if not reviewed/completed
    if status not in ["Reviewed", "Completed"]:
        conn.close()
        return HTMLResponse("<h3 style='color:red;text-align:center;'>Complete review before sending</h3>")

    file_name = f"{client_code}.pdf"
    
    c.execute("SELECT pdf_url FROM clients WHERE id=%s", (client_id,))
    pdf_data = c.fetchone()

    if not pdf_data or not pdf_data[0]:
        conn.close()
        return HTMLResponse("<h3 style='color:red;text-align:center;'>Generate PDF first</h3>")

    pdf_url = pdf_data[0]

    c.execute("UPDATE clients SET status='Completed' WHERE id=%s", (client_id,))
    conn.commit()
    conn.close()

    message = f"""नमस्ते {name},

आपकी हस्तरेखा रिपोर्ट तैयार है 🙏

📄 डाउनलोड लिंक:
{pdf_url}

यह लिंक हमेशा उपलब्ध रहेगा।

– आचार्य विशाल वैष्णव
"""

    encoded = urllib.parse.quote(message)

    link = f"https://wa.me/91{phone_number}?text={encoded}"

    return RedirectResponse(link)    

# ---------- ADD CLIENT FORM ----------
@router.get("/admin/add-client")
def add_client_form(request: Request):
    auth = check_admin(request)
    if auth:
        return auth
    return render_template_safe(request, "admin/add_client.html")
    
@router.post("/admin/add-client")
async def add_client(
    name: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(...),
    tob: Optional[str] = Form(None),
    place: Optional[str] = Form(None),
    questions: str = Form(...),
    plan: str = Form(...),
    images: List[UploadFile] = File(...)
):

    conn = get_db()
    c = conn.cursor()

    # ✅ STEP 1: GENERATE CODE
    client_code = generate_client_code()

    # ✅ STEP 2: INSERT CLIENT (WITHOUT IMAGES)
    c.execute(
        """
        INSERT INTO clients
        (client_code,name,phone,dob,tob,place,questions,plan,images,source,status,payment_status,created_at,priority,ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_code,
            name,
            phone,
            dob,
            tob,
            place,
            questions,
            plan,
            "",   # 🔥 EMPTY IMAGES
            "Manual",
            "Pending",
            "Pending",
            datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            99,
            0
        )
    )

    conn.commit()

    # ✅ STEP 3: UPLOAD IMAGES (AFTER DB INSERT)
    saved_files = []

    for img in images:
        unique_name = f"{uuid.uuid4().hex}_{img.filename}"

        file_bytes = await img.read()

        file_url = upload_palm_image(file_bytes, unique_name, client_code)

        saved_files.append(file_url)

    # ✅ STEP 4: UPDATE DB WITH IMAGE URLS
    c.execute(
        "UPDATE clients SET images=%s WHERE client_code=%s",
        (",".join(saved_files), client_code)
    )

    conn.commit()
    conn.close()

    return RedirectResponse("/admin/dashboard", status_code=302)

@router.get("/admin/client/{client_id}/ai-status")
def ai_status(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT ai_draft, ai_generated FROM clients WHERE id=%s", (client_id,))
    data = c.fetchone()

    conn.close()

    return {
        "ready": bool(data[1]),
        "ai_draft": data[0] if data[0] else ""
    }

# 🔥 TEMP DEBUG ROUTE (REMOVE AFTER TEST)
@router.get("/debug/db")
def debug_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, payment_status, ai_generated FROM clients ORDER BY id DESC LIMIT 10")
    data = c.fetchall()

    conn.close()

    return {"data": data}

@router.get("/debug/reset")
def reset_ai():
    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE clients SET ai_generated=0")
    conn.commit()

    conn.close()

    return {"status": "RESET DONE"}

@router.get("/admin/client/{client_id}/send-details")
def send_details(request: Request, client_id: int):

    auth = check_admin(request)
    if auth:
        return auth

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT client_code, name, phone, plan, dob, tob, place, questions
        FROM clients WHERE id=%s
    """, (client_id,))

    data = c.fetchone()
    conn.close()

    if not data:
        return HTMLResponse("Client not found")

    client_code, name, phone, plan, dob, tob, place, question = data

    # 🔥 FINAL PREMIUM MESSAGE
    msg = f"""🙏 *जय श्री राधे* 🙏

आपकी जानकारी *Acharya Vishal Vaishnav* को सफलतापूर्वक प्राप्त हो गई है।

📌 *Client Details:*

👤 नाम: {name}  
📞 मोबाइल: {phone}  
📅 जन्म तिथि: {dob}  
⏰ जन्म समय: {tob}  
📍 जन्म स्थान: {place}  
🧾 प्लान: {plan}  

प्रश्न:
{question}

🆔 *आपका Client Code:* {client_code}

━━━━━━━━━━━━━━━

💳 *Payment Details:*

🔹 *Account 1:*  
Name: Aarti Ramawat  
A/C: 61266765065  
IFSC: SBIN0031573  
Bank: State Bank of India  

🔹 *Account 2:*  
Name: Vishal Vaishnav  
A/C: 61040532921  
IFSC: SBIN0031573  
Bank: State Bank of India  

📲 *UPI QR Code:*  
https://aacharyavishalvaishnav.pages.dev/upi-qr.png  

━━━━━━━━━━━━━━━

📩 *आगे की प्रक्रिया:*

✔ Payment करने के बाद  
✔ Screenshot इसी WhatsApp नंबर पर भेजें  
✔ साथ में *Client Code जरूर लिखें*

⏳ आपकी रिपोर्ट 12–24 घंटे में तैयार कर दी जाएगी।

━━━━━━━━━━━━━━━

✨ धन्यवाद  
*Acharya Vishal Vaishnav*"""

    encoded_msg = urllib.parse.quote(msg)

    wa_link = f"https://wa.me/91{phone}?text={encoded_msg}"
    
    return RedirectResponse(wa_link)
