from datetime import datetime
from zoneinfo import ZoneInfo
from .database import get_db

def create_client(client_code, name, phone, plan):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO clients
        (client_code, name, phone, plan, source, status, payment_status, created_at, priority, ai_generated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        client_code,
        name,
        phone,
        plan,
        "Manual",
        "Pending",
        "Pending",
        datetime.now(ZoneInfo("Asia/Kolkata")),
        99,
        0
    ))

    conn.commit()
    conn.close()

def get_all_clients():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, client_code, name, phone, plan, status FROM clients ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows
