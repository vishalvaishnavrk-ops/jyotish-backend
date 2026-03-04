from app.database import get_db


# ---------- CREATE TABLE ----------

def init_db():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (

        id SERIAL PRIMARY KEY,

        client_code TEXT,
        name TEXT,
        phone TEXT,

        dob TEXT,
        tob TEXT,
        place TEXT,

        plan TEXT,
        questions TEXT,
        images TEXT,

        source TEXT,
        status TEXT,

        payment_status TEXT DEFAULT 'Pending',
        payment_date TEXT,
        payment_ref TEXT,

        ai_draft TEXT,

        created_at TEXT,

        priority INTEGER DEFAULT 99,
        ai_generated INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


# ---------- CREATE CLIENT ----------

def create_client(
    client_code,
    name,
    phone,
    dob,
    tob,
    place,
    plan,
    questions,
    images,
    source,
    status,
    created_at
):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO clients
    (client_code,name,phone,dob,tob,place,plan,questions,images,source,status,created_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,(
        client_code,
        name,
        phone,
        dob,
        tob,
        place,
        plan,
        questions,
        images,
        source,
        status,
        created_at
    ))

    conn.commit()
    conn.close()
