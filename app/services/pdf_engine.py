from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import os
import re

from app.database import get_db
from app.services.supabase_storage import upload_pdf

REPORT_DIR = "reports"


def generate_pdf_report(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT client_code,name,phone,plan,ai_draft,created_at FROM clients WHERE id=%s",
        (client_id,)
    )

    data = c.fetchone()
    # 🔥 DUPLICATE CHECK
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT pdf_url FROM clients WHERE id=%s", (client_id,))
    row = c.fetchone()

    if row and row[0]:
        return row[0]   # already generated → stop

    conn.close()

    if not data:
        return None

    client_code, name, phone, plan, ai_draft, created_at = data

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    font_config = FontConfiguration()

    # correct path for assets
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    font_path = os.path.join(base_dir, "assets", "NotoSansDevanagari-Regular.ttf")
    ganesha_path = os.path.join(base_dir, "assets", "ganesha.png")

    # split antim message
    antim_message = ""

    if "अंतिम संदेश:" in ai_draft:
        parts = ai_draft.split("अंतिम संदेश:")
        main_content = parts[0]
        antim_message = parts[1].strip()
    else:
        main_content = ai_draft

    sections = re.split(r'(Section\s+\d+\s*–.*?)\n', main_content)

    formatted_blocks = ""

    for i in range(1, len(sections), 2):

        title = sections[i].strip()
        content = sections[i + 1].strip()

        content = content.replace("वर्ष", "<br><br>वर्ष")

        formatted_blocks += f"""
        <div class="section-block">

        <div class="section-heading">{title}</div>

        <div class="section-content">
        {content.replace("\\n","<br>")}
        </div>

        </div>
        """

    # antim page
    if antim_message:

        formatted_blocks += f"""
        <div style="page-break-before:always;"></div>

        <div class="antim-section">

        <div class="antim-title">
        अंतिम संदेश
        </div>

        <div class="antim-text">
        {antim_message.replace("\\n","<br>")}
        </div>

        <div class="antim-sign">
        – आचार्य विशाल वैष्णव
        </div>

        </div>
        """

    html = f"""
<html>

<head>

<meta charset="utf-8">

<style>

@page {{
size:A4;
margin:45px;
border:2px solid #d4af37;
}}

@font-face {{
font-family:'NotoDev';
src:url('file://{font_path}') format('truetype');
}}

body {{
font-family:'NotoDev';
background:#faf6ef;
margin:0;
padding-top:10px;
}}

.watermark {{
position:fixed;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:150px;
color:rgba(139,0,0,0.05);
z-index:-1;
}}

.cover {{
padding:30px;
}}

.header {{
text-align:center;
background:linear-gradient(to right,#7b0000,#b22222);
padding:35px;
border-radius:12px;
color:white;
}}

.title {{
font-size:36px;
font-weight:bold;
margin-top:10px;
}}

.subtitle {{
font-size:18px;
}}

.client-box {{
background:linear-gradient(to right,#fff8e7,#ffe7b5);
padding:30px;
margin-top:25px;
border-left:6px solid #d4af37;
border-radius:12px;
box-shadow:0 6px 16px rgba(0,0,0,0.1);
font-size:16px;
}}

.section-title {{
text-align:center;
font-size:32px;
font-weight:bold;
margin-top:40px;
margin-bottom:35px;
color:#8b0000;
letter-spacing:1px;
}}

.section-block {{
background:linear-gradient(to bottom,#fffdf9,#ffecc7);
padding:28px;
margin:22px 32px;
border-left:6px solid #b8860b;
border-radius:12px;
box-shadow:0 4px 12px rgba(0,0,0,0.08);
page-break-inside:avoid;
}}

.section-heading {{
font-size:18px;
font-weight:bold;
color:#7b0000;
margin-bottom:10px;
}}

.section-content {{
line-height:1.8;
font-size:15px;
}}

.antim-section {{
background:#fff8e7;
margin:60px 50px;
padding:45px;
border-radius:18px;
border:2px solid #d4af37;
text-align:center;
}}

.antim-title {{
font-size:28px;
font-weight:bold;
margin-bottom:20px;
color:#8b0000;
}}

.antim-text {{
font-size:18px;
line-height:1.8;
}}

.antim-sign {{
margin-top:30px;
font-size:16px;
font-weight:bold;
}}

.footer {{
margin-top:60px;
text-align:center;
font-size:12px;
color:#777;
}}

</style>

</head>

<body>

<div class="watermark">ॐ</div>

<div class="cover">

<div class="header">

<img src="file://{ganesha_path}" style="width:100%;border-radius:10px;">

<div class="title">आचार्य विशाल वैष्णव</div>

<div class="subtitle">
हस्तरेखा विशेषज्ञ एवं वैदिक ज्योतिषज्ञ
</div>

</div>

<div class="client-box">

<b>Client Code:</b> {client_code}<br>
<b>Name:</b> {name}<br>
<b>Mobile:</b> {phone}<br>
<b>Plan:</b> {plan}<br>
<b>Date:</b> {created_at}

</div>

</div>

<div style="page-break-after:always;"></div>

<div class="section-title">
PALM READING DETAILED REPORT
</div>

{formatted_blocks}

<div class="footer">

<hr style="width:85%;margin:30px auto;opacity:0.4;">

© 2026 आचार्य विशाल वैष्णव | All Rights Reserved<br>

WhatsApp: +91-6000376976

</div>

</body>
</html>
"""

    HTML(string=html).write_pdf(file_path, font_config=font_config)

    # 🔥 SUPABASE UPLOAD START
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_url = upload_pdf(pdf_bytes, file_name)

    # 🔥 SAVE IN DB
    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE clients SET pdf_url=%s WHERE id=%s", (pdf_url, client_id))

    conn.commit()
    conn.close()

    # OPTIONAL: local file delete (recommended)
    os.remove(file_path)

    return pdf_url
