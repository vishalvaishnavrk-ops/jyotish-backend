from weasyprint import HTML
from app.database import get_db
import os

REPORT_DIR = "reports"

def generate_pdf_report(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT client_code,name,ai_draft
    FROM clients
    WHERE id=%s
    """, (client_id,))

    data = c.fetchone()
    conn.close()

    if not data:
        return None

    client_code, name, ai_draft = data

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    html = f"""
    <h1>Palm Reading Report</h1>
    <h3>{name}</h3>
    <p>{ai_draft}</p>
    """

    HTML(string=html).write_pdf(file_path)

    return file_name
