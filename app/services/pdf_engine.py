from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import os
import re
import time
from app.database import get_db, release_db
from app.services.supabase_storage import upload_pdf

REPORT_DIR = "reports"


def format_ai_text(ai_text):

    # ---------- BULLET FORCE ----------
    ai_text = re.sub(r'•\s*', r'\n• ', ai_text)

    # ---------- NUMBERING ----------
    ai_text = re.sub(r'(\d+\.)\s*', r'\n\1 ', ai_text)

    # ---------- DASH ----------
    ai_text = re.sub(r'[-–]\s*', r'\n• ', ai_text)

    # ---------- MAIN LINES ----------
    ai_text = re.sub(
        r'(जीवन रेखा:|मस्तिष्क रेखा:|हृदय रेखा:|भाग्य रेखा:)',
        r'\n\1',
        ai_text
    )

    # ---------- MOUNTS ----------
    ai_text = re.sub(
        r'(शुक्र|बुध|शनि|सूर्य|चंद्र) पर्वत',
        r'\n\1 पर्वत',
        ai_text
    )

    return ai_text.strip()


def generate_pdf_report(client_id):

    conn = get_db()
    try:
        c = conn.cursor()

        c.execute("""
        SELECT client_code,name,phone,plan,ai_draft,created_at,
        dob,tob,place,questions
        FROM clients WHERE id=%s
        """, (client_id,))
        data = c.fetchone()

        # duplicate check
        c.execute("SELECT pdf_url FROM clients WHERE id=%s", (client_id,))
        row = c.fetchone()

        if row and row[0]:
            return row[0]

    finally:
        release_db(conn)

    if not data:
        return None

    client_code, name, phone, plan, ai_draft, created_at, dob, tob, place, question = data

    # ---------- FORMAT ----------
    ai_draft = format_ai_text(ai_draft)

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    font_config = FontConfiguration()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_path = os.path.join(base_dir, "assets", "NotoSansDevanagari-Regular.ttf")
    ganesha_path = os.path.join(base_dir, "assets", "ganesha.png")

    # ---------- SECTION SPLIT ----------
    sections = re.split(r'(Section\s*\d+\s*–[^\n]+)', ai_draft)

    formatted_blocks = ""

    for i in range(1, len(sections), 2):

        title = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""

        if not content:
            continue

        formatted_blocks += f"""
        <div class="section-block">
            <div class="section-heading">{title}</div>
            <div class="section-content">
                {content.replace("\\n","<br>")}
            </div>
        </div>
        """

    if not formatted_blocks:
        formatted_blocks = ai_draft.replace("\n", "<br>")

    # ---------- HTML ----------
    html = f"""
<html>
<head>
<meta charset="utf-8">

<style>

@page {{
    size:A4;
    margin:50px;
    border:3px double #d4af37;
}}

@font-face {{
    font-family:'NotoDev';
    src:url('file://{font_path}') format('truetype');
}}

body {{
    font-family:'NotoDev';
    background:#faf6ef;
    margin:0;
    padding-top:20px;
    padding-bottom:90px;
}}

.section-block {{
    margin:25px;
    padding-bottom:15px;
    border-bottom:2px dashed #aaa;
    page-break-inside: avoid;
}}

.section-heading {{
    font-size:18px;
    font-weight:bold;
    color:#7b0000;
    margin-bottom:8px;
}}

.section-content {{
    line-height:1.9;
    font-size:15px;
}}

.section-content br {{
    margin-bottom:6px;
}}

.header {{
    text-align:center;
    margin-bottom:20px;
}}

.title {{
    font-size:32px;
    font-weight:bold;
    color:#7b0000;
}}

.client-box {{
    margin:20px;
    padding:15px;
    border:2px dashed #999;
    border-radius:10px;
    background:#fffdf8;
}}

.footer {{
    position: fixed;
    bottom: 20px;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 12px;
    color: #777;
}}

</style>
</head>

<body>

<div class="header">
    <div class="title">VATS PALM REPORT</div>
</div>

<div class="client-box">
<b>Client Code:</b> {client_code}<br>
<b>Name:</b> {name}<br>
<b>Mobile:</b> {phone}<br>
<b>Plan:</b> {plan}<br><br>

<b>DOB:</b> {dob}<br>
<b>TOB:</b> {tob}<br>
<b>Place:</b> {place}<br><br>

<b>Question:</b> {question}<br>
<b>Date:</b> {created_at}
</div>

{formatted_blocks}

<div class="footer">
© VATS PALM REPORTS
</div>

</body>
</html>
"""

    HTML(string=html).write_pdf(
        file_path,
        font_config=font_config,
        optimize_size=('fonts', 'images')
    )

    # ---------- UPLOAD ----------
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        pdf_url = upload_pdf(pdf_bytes, file_name)
    except Exception as e:
        print("UPLOAD ERROR:", e)
        pdf_url = None

    # ---------- SAVE ----------
    conn = get_db()
    try:
        c = conn.cursor()

        if pdf_url:
            c.execute("UPDATE clients SET pdf_url=%s WHERE id=%s", (pdf_url, client_id))

        conn.commit()

    finally:
        release_db(conn)

    time.sleep(1)

    if os.path.exists(file_path):
        os.remove(file_path)

    return pdf_url
