from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import os
import re
import time
from app.database import get_db
from app.services.supabase_storage import upload_pdf

REPORT_DIR = "reports"


def generate_pdf_report(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT client_code,name,phone,plan,ai_draft,created_at,
    dob,tob,place,questions
    FROM clients WHERE id=%s
    """, (client_id,))

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

    client_code, name, phone, plan, ai_draft, created_at, dob, tob, place, question = data

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

        is_last_section = (i + 2 >= len(sections))

        if is_last_section:
            formatted_blocks += f"""
            <div class="section-block">
                <div class="section-heading">{title}</div>
                <div class="section-content">
                    {content.replace("\\n","<br>")}
                </div>
            </div>
            """
        else:
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

h1, .title {{
font-family: "Georgia", "Times New Roman", serif;
letter-spacing: 1px;
}}

.section-title {{
font-family: "Georgia", "Times New Roman", serif;
letter-spacing: 1px;
}}

@page {{
size:A4;
margin:50px;   /* 🔥 equal border spacing */
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
padding-top:10px;
padding-bottom:90px;
}}

.page-content {{
padding-top:25px;
padding-bottom:20px;
}}

.page-content > *:first-child {{
margin-top:20px;
}}

.watermark {{
position:fixed;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:120px;
color:rgba(139,0,0,0.06);
z-index:-1;
white-space:nowrap;
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
margin:15px 30px;   /* 🔥 top spacing कम */
padding:20px;
border:2px dashed #999;
border-radius:10px;
font-size:15px;
line-height:1.6;
background:#fffdf8;
}}

.section-title {{
text-align:center;
font-size:30px;
font-weight:bold;
margin-top:20px;
margin-bottom:10px;
color:#7b0000;
display:inline-block;
border-bottom:2px solid #7b0000;
padding-bottom:5px;
}}

.section-block {{
margin:25px 25px;
padding-bottom:10px;
border-bottom:2px dashed #aaa;
line-height:1.6;
}}

.section-block:last-child {{
margin-bottom:0;
padding-bottom:0;
border-bottom:none;
}}

.section-block:last-child .section-heading {{
margin-bottom:2px;
}}

.section-block:last-child .section-content {{
margin-top:-3px;
line-height:1.4;
}}

.section-heading {{
font-size:18px;
font-weight:bold;
color:#7b0000;
margin-bottom:4px;
}}

.section-content {{
line-height: 1.5;
margin-top: 2px;
orphans: 3;
widows: 3;
}}

.antim-section {{
margin:40px 20px;
padding:20px;
border:2px dashed #999;
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
position: fixed;
bottom: 25px;   /* 🔥 border से distance */
left: 0;
right: 0;
text-align: center;
font-size: 12px;
color: #777;
line-height: 1.2;   /* 🔥 line-text gap control */
}}

</style>

</head>

<body>

<div class="watermark">श्री राधे</div>

<div class="page-content">

<div class="cover">

<div class="header" style="background:none; color:#000;">

<div style="
text-align:center;
font-size:36px;
font-weight:bold;
color:#7b0000;
letter-spacing:1px;
font-family: Georgia, 'Times New Roman', serif;
">
VATS PALM REPORTS
</div>

<div style="text-align:center; font-size:14px; margin-bottom:25px;">
Created By
</div>

<div style="text-align:center; margin:30px 0;">
<img src="file://{ganesha_path}" 
style="width:220px;height:220px;border-radius:50%;border:5px solid #d4af37;">
</div>

<div style="text-align:center;">
<div style=font-size:26px; color:#8b0000; font-weight:bold;">
आचार्य विशाल वैष्णव
</div>

<div style="font-size:16px; color:#333;">
हस्तरेखा विशेषज्ञ एवं वैदिक ज्योतिषज्ञ
</div>
</div>

</div>
</div>

<div class="client-box">

<div style="font-weight:bold; font-size:18px; margin-bottom:10px; color:#8b0000;">
Client Information
</div>

<b>Client Code:</b> {client_code}<br>
<b>Name:</b> {name}<br>
<b>Mobile:</b> {phone}<br>
<b>Plan:</b> {plan}<br>

<b>Date of Birth:</b> {dob}<br>
<b>Time of Birth:</b> {tob}<br>
<b>Place:</b> {place}<br>

<b>Main Question:</b> {question}<br>

<b>Date:</b> {created_at}

</div>

</div>

<div style="page-break-after:always;"></div>

<div style="text-align:center;">
    <div class="section-title">
        PALM READING DETAILED REPORT
    </div>
</div>

{formatted_blocks}

<div class="footer">
<div style="border-top:1px solid #ccc; margin:0 40px 3px 40px;"></div>
<div>© 2026 All Rights Reserved & Powered by VATS PALM REPORTS</div>
</div>

</div>
</body>
</html>
"""

    HTML(string=html).write_pdf(file_path, font_config=font_config)

    # 🔥 SUPABASE UPLOAD START
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        pdf_url = upload_pdf(pdf_bytes, file_name)
    except Exception as e:
        print("UPLOAD ERROR:", e)
        pdf_url = None

    # 🔥 SAVE IN DB
    conn = get_db()
    c = conn.cursor()

    if pdf_url:
        c.execute("UPDATE clients SET pdf_url=%s WHERE id=%s", (pdf_url, client_id))

    conn.commit()
    conn.close()

    # OPTIONAL: local file delete (recommended)
    time.sleep(1)
    
    if os.path.exists(file_path):
        os.remove(file_path)

    return pdf_url
