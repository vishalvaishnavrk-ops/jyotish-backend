import urllib.parse

def generate_whatsapp_link(name, phone, pdf_url):

    message = f"""
नमस्ते {name},

आपकी हस्तरेखा रिपोर्ट तैयार है।

PDF:
{pdf_url}

– आचार्य विशाल वैष्णव
"""

    encoded = urllib.parse.quote(message)

    return f"https://wa.me/91{phone}?text={encoded}"
