from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import os
import re

from app.database import get_db

REPORT_DIR = "reports"


def generate_pdf_report(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT client_code,name,phone,plan,ai_draft,created_at FROM clients WHERE id=%s",
        (client_id,)
    )

    data = c.fetchone()
    conn.close()

    if not data:
        return None

    client_code, name, phone, plan, ai_draft, created_at = data

    file_name = f"{client_code}.pdf"
    file_path = os.path.join(REPORT_DIR, file_name)

    font_config = FontConfiguration()

    # -------- PATH FIX --------
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    font_path = os.path.join(base_dir, "assets", "NotoSansDevanagari-Regular.ttf")
    ganesha_path = os.path.join(base_dir, "assets", "ganesha.png")

    # -------- SPLIT ANTIM MESSAGE --------
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

        formatted_blocks += f"""
        <div class="section-block">
        <div class="section-heading">{title}</div>
        {content.replace("\\n","<br>")}
        </div>
        """

    # -------- ANTIM SANDESH PAGE --------
    if antim_message:

        clean_antim = antim_message.replace("– आचार्य विशाल वैष्णव", "")

        formatted_blocks += f"""
        <div style="page-break-before:always;"></div>

        <div class="antim-section">

        <div class="antim-title">अंतिम संदेश</div>

        <div class="antim-content">
        {clean_antim.replace("\\n","<br>")}
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
margin:40px;
border:2px solid #d4af37;
}}

@font-face {{
font-family:'NotoDev';
src:url('file://{font_path}') format('truetype');
}}

body {{
font-family:'NotoDev';
margin:0;
background:#faf6ef;
}}

.watermark {{
position:fixed;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:160px;
color:rgba(139,0,0,0.05);
z-index:-1;
}}

.cover {{
padding:40px;
}}

.header {{
text-align:center;
background:linear-gradient(to right,#7b0000,#b22222);
color:white;
padding:35px;
border-radius:12px;
margin-bottom:35px;
}}

.title {{
font-size:36px;
font-weight:bold;
margin-top:15px;
}}

.subtitle {{
font-size:18px;
}}

.client-box {{
background:#fff8e7;
padding:22px;
border-left:6px solid #d4af37;
border-radius:12px;
box-shadow:0 4px 10px rgba(0,0,0,0.08);
}}

.section-title {{
font-size:26px;
font-weight:bold;
color:#8b0000;
margin-top:20px;
margin-bottom:25px;
border-bottom:3px solid #d4af37;
}}

.section-block {{
background:#fffdf9;
padding:22px;
margin-bottom:25px;
border-left:6px solid #b8860b;
border-radius:10px;
}}

.section-heading {{
font-weight:bold;
font-size:18px;
margin-bottom:8px;
color:#7b0000;
}}

.antim-section {{
background:#fff8e7;
margin:60px 40px;
padding:40px;
border-radius:18px;
text-align:center;
border:2px solid #d4af37;
}}

.antim-title {{
font-size:28px;
font-weight:bold;
color:#8b0000;
margin-bottom:20px;
}}

.antim-content {{
font-size:18px;
line-height:1.8;
}}

.antim-sign {{
margin-top:30px;
font-size:16px;
font-weight:bold;
color:#7b0000;
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

<img src="file://{ganesha_path}" style="width:100%;border-radius:8px;">

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
Palm Reading Detailed Report
</div>

{formatted_blocks}

<div class="footer">

<hr>

© 2026 आचार्य विशाल वैष्णव | All Rights Reserved<br>
WhatsApp: +91-6000376976

</div>

</body>
</html>
"""

    HTML(string=html, base_url="/").write_pdf(
        file_path,
        font_config=font_config
    )

    return file_name
