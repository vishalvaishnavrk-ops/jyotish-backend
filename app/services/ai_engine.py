from openai import OpenAI
import os
from app.database import get_db, release_db

# 🔥 SWITCH
USE_REAL_AI = True   # False = dummy | True = real AI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_draft(client_id):

    # ---------- FETCH DATA ----------
    conn = get_db()
    try:
        c = conn.cursor()

        c.execute("""
        SELECT name,questions,plan,dob,tob,place,images 
        FROM clients WHERE id=%s
        """, (client_id,))
        data = c.fetchone()

        if not data:
            return "No client found"

        c.execute("SELECT ai_generated FROM clients WHERE id=%s", (client_id,))
        ai_flag = c.fetchone()[0]

        if ai_flag == 1:
            return "AI already generated"

        name, questions, plan, dob, tob, place, images = data

    finally:
        release_db(conn)

    # ---------- IMAGE PARSE ----------
    image_urls = []
    if images:
        image_urls = [img.strip() for img in images.split(",") if img.strip()]

    # ---------- MODE ----------
    mode = "PALM_ONLY"
    if dob and tob and place:
        mode = "HYBRID"

    # ---------- PLAN DEPTH ----------
    if "₹51" in plan:
        word_limit = 400
        years_text = "केवल वर्ष 1 और 2 का संक्षिप्त पूर्वानुमान दें"
        max_tokens = 500
        depth_note = "संक्षिप्त लेकिन सटीक विश्लेषण दें"
    elif "₹151" in plan:
        word_limit = 700
        years_text = "वर्ष 1 से 3 तक स्पष्ट पूर्वानुमान दें"
        max_tokens = 800
        depth_note = "थोड़ा विस्तार और कारण सहित समझाएँ"
    elif "₹251" in plan:
        word_limit = 1000
        years_text = "वर्ष 1 से 4 तक विस्तृत पूर्वानुमान दें"
        max_tokens = 1000
        depth_note = "विस्तृत विश्लेषण + practical guidance दें"
    else:
        word_limit = 1300
        years_text = "वर्ष 1 से 5 तक गहराई से प्रवृत्ति और दिशा बताएं"
        max_tokens = 1500
        depth_note = "हर section में 3–5 बिंदुओं के साथ गहराई से मार्गदर्शन दें"

    # ---------- IMAGE COUNT LOGIC ----------
    if "₹501" in plan:
        selected_images = image_urls[:4]
    else:
        selected_images = image_urls[:2]

    # ---------- FINAL MASTER PROMPT ----------
    prompt = f"""
आप एक अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिष सलाहकार हैं (15+ वर्षों का अनुभव)।

आपको क्लाइंट के हाथों की images और जन्म विवरण दिए गए हैं।  
आपका कार्य एक गहराई से की गई, वास्तविक और व्यक्तिगत विश्लेषण रिपोर्ट तैयार करना है।

---

क्लाइंट: {name}  
प्रश्न: {questions}  
Mode: {mode}  
DOB: {dob}, Time: {tob}, Place: {place}  

---

🔷 MODE के अनुसार विश्लेषण करें:

यदि Mode = PALM_ONLY:
→ केवल हस्तरेखा के आधार पर विश्लेषण करें  

यदि Mode = HYBRID:
→ हस्तरेखा + वैदिक ज्योतिष का संतुलित उपयोग करें  
→ जहाँ उपयुक्त हो, जन्म विवरण से समर्थन दें  

---

🔷 लेखन शैली:

- भाषा अनुभवी गुरु या ज्योतिषाचार्य जैसी हो  
- वाक्य स्पष्ट, आत्मविश्वासपूर्ण और सरल हों  
- भविष्य को निश्चित रूप में न बताकर संकेत और दिशा दें  
- generic या किताबी बातों से बचें  
- जहाँ संभव हो, observation के साथ उसका अर्थ भी दें  

---

🔷 PLAN DEPTH:

₹51 → संक्षिप्त और सटीक  
₹151 → थोड़ा विस्तार + कारण  
₹251 → विस्तृत विश्लेषण + मार्गदर्शन  
₹501 → गहराई से जीवन दिशा + स्पष्ट सलाह  

👉 ₹501 में:
- हर section में 3–5 meaningful points दें  
- reasoning और जीवन दिशा शामिल करें  
- निर्णय लेने में मदद करने वाला insight दें  

---

🔷 REPORT STRUCTURE:

Section 1 – हस्त संरचना  
Section 2 – पर्वत विश्लेषण  
Section 3 – मुख्य रेखाएं  
Section 4 – विशेष संकेत  
Section 5 – जीवन दिशा  
Section 6 – प्रश्न का उत्तर  
Section 7 – उपाय  
Section 8 – भविष्य ({years_text})  
Section 9 – अंतिम संदेश  

---

🔷 SECTION GUIDELINES:

1. हस्त संरचना  
→ हाथ का आकार, उंगलियाँ, ऊर्जा

2. पर्वत  
→ केवल प्रमुख पर्वत जिनमें अंतर दिखे

3. रेखाएं  
→ जीवन, मस्तिष्क, हृदय, भाग्य  
→ observation + उसका अर्थ

4. संकेत  
→ जो स्पष्ट दिखे (कट, शाखा आदि)

5. जीवन दिशा  
→ जीवन pattern और दिशा

6. प्रश्न का उत्तर  
→ सीधा और practical समाधान

7. उपाय  
→ समस्या के अनुसार practical उपाय दें  
→ इनमें शामिल हो सकते हैं:
   • जप / मंत्र  
   • दैनिक अनुशासन  
   • दान या संतुलन  
→ उपाय सरल, लागू करने योग्य और सार्थक हों  

8. भविष्य  
→ वर्ष अनुसार प्रवृत्ति और दिशा

9. अंतिम संदेश  
→ पूरी रिपोर्ट का सार + guidance + 1 practical Pro Tip  

---

🔷 महत्वपूर्ण:

- सभी sections शामिल करें  
- हर section में अलग और उपयोगी जानकारी दें  
- repetition से बचें  
- tone प्राकृतिक और मानवीय रखें  

---

🔷 भाषा:

सरल, स्पष्ट, प्रभावशाली हिंदी  
ऐसी लगे जैसे किसी अनुभवी विशेषज्ञ ने स्वयं लिखी हो  

---

🔷 लंबाई:

लगभग {word_limit} शब्द  
"""

    # ---------- DUMMY MODE ----------
    if not USE_REAL_AI:
        draft = f"""
Section 1 – हस्त संरचना
यह टेस्ट रिपोर्ट है।

Section 2 – पर्वत
संतुलन है।

Section 3 – रेखाएं
जीवन रेखा स्पष्ट है।

Section 4 – संकेत
सकारात्मक संकेत हैं।

Section 5 – जीवन दिशा
स्थिरता आएगी।

Section 6 – उत्तर
आपको focus करना होगा।

Section 7 – उपाय
सुबह सूर्य को जल दें।

Section 8 – भविष्य
वर्ष 1 सुधार

Section 9 – अंतिम संदेश
आप सही दिशा में हैं।
"""
    else:
        # ---------- REAL AI ----------
        content = [{"type": "text", "text": prompt}]

        for img in selected_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": img}
            })

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": content}
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )

            draft = response.choices[0].message.content

        except Exception as e:
            draft = f"AI Error: {str(e)}"

    # ---------- SAVE ----------
    conn = get_db()
    try:
        c = conn.cursor()

        c.execute("""
        UPDATE clients
        SET ai_draft=%s, ai_generated=1
        WHERE id=%s
        """, (draft, client_id))

        conn.commit()

    finally:
        release_db(conn)

    return draft
