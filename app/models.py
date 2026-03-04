from app.database import get_db

def create_client(data):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO clients
    (client_code,name,phone,dob,tob,place,plan,questions,images,
     source,status,payment_status,created_at,priority,ai_generated)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, data)

    conn.commit()
    conn.close()


def get_clients():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT id,client_code,name,phone,plan,status
    FROM clients
    ORDER BY id DESC
    """)

    rows = c.fetchall()
    conn.close()

    return rows
