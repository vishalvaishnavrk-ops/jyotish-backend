from app.database import get_db

def generate_ai_draft(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT name, plan, questions
    FROM clients
    WHERE id=%s
    """, (client_id,))

    data = c.fetchone()

    if not data:
        conn.close()
        return

    name, plan, questions = data

    draft = f"""
Section 1 – हस्त संरचना विश्लेषण
{name} की हथेली में संतुलित ऊर्जा दिखाई देती है।

Section 2 – पर्वत विश्लेषण
शुक्र पर्वत आकर्षण का प्रतीक है।

Section 3 – रेखा विश्लेषण
जीवन रेखा स्थिरता दर्शाती है।

Section 4 – प्रश्न उत्तर
आपका प्रश्न:
{questions}

अंतिम संदेश:
सकारात्मक कर्म करते रहें।
– आचार्य विशाल वैष्णव
"""

    c.execute("""
    UPDATE clients
    SET ai_draft=%s, ai_generated=1
    WHERE id=%s
    """, (draft, client_id))

    conn.commit()
    conn.close()
