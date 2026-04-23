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
आप एक अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिष सलाहकार हैं, जिनका अनुभव 15+ वर्षों का है।

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
→ केवल हस्तरेखा (Palm Reading) के आधार पर विश्लेषण करें  
→ हाथ की रेखाएं, पर्वत, बनावट और ऊर्जा पर पूरा focus रखें  
→ ज्योतिष का उपयोग न करें  

यदि Mode = HYBRID:
→ हस्तरेखा + वैदिक ज्योतिष दोनों का उपयोग करें  
→ palm से जो संकेत दिखते हैं उन्हें जन्म विवरण से cross-check करें  
→ कम से कम एक स्थान पर ज्योतिष आधारित समर्थन अवश्य दें  
→ अंतिम निष्कर्ष दोनों के संतुलन से दें  

---

🔷 लेखन शैली:

- भाषा एक अनुभवी गुरु या ज्योतिषाचार्य जैसी हो  
- हर लाइन में आत्मविश्वास और स्पष्टता हो  
- भविष्य को निश्चित रूप में न बताएं, बल्कि संकेत और दिशा दें  
- कोई generic या किताबी theory न लिखें  
- हर observation स्पष्ट, व्यक्तिगत और वास्तविक हो  
- हर observation के साथ उसका अर्थ (reasoning) अवश्य दें  

---

🔷 PLAN DEPTH (STRICT):

₹51 → संक्षिप्त, 1–2 बिंदु प्रति सेक्शन  
₹151 → 2–3 बिंदु + छोटा कारण  
₹251 → 3–4 बिंदु + practical guidance  
₹501 → 3–5 बिंदु + गहराई + निर्णय मार्गदर्शन  

👉 ₹501 में विशेष ध्यान:
- हर सेक्शन में स्पष्ट reasoning दें  
- जीवन की दिशा स्पष्ट करें  
- क्लाइंट को निर्णय लेने में मदद करें  
- दोनों हाथों में अंतर हो तो उसका उल्लेख करें  
- ऐसा लगे कि एक अनुभवी गुरु व्यक्तिगत मार्गदर्शन दे रहा है  

---

🔷 REPORT STRUCTURE (ALL SECTIONS MUST):

1. हस्त संरचना  
(हाथ का आकार, उंगलियों की बनावट, ऊर्जा — जो वास्तव में दिखे)

2. पर्वत विश्लेषण  
(केवल वही पर्वत जिनमें स्पष्ट उभार/कमज़ोरी दिखे + अर्थ)

3. मुख्य रेखाएं  
जीवन रेखा  
मस्तिष्क रेखा  
हृदय रेखा  
भाग्य रेखा  

👉 हर रेखा में:
- वास्तविक observation  
- उसका स्पष्ट अर्थ  

4. विशेष संकेत  
(कट, शाखाएँ, क्रॉस, टूटन — केवल जो दिखाई दे)

5. जीवन दिशा  
(कर्म, pattern, वास्तविक जीवन की दिशा + practical insight)

6. प्रश्न का उत्तर  
(क्लाइंट के प्रश्न का सीधा, स्पष्ट और actionable समाधान)

7. उपाय (सबसे महत्वपूर्ण)  

- समस्या के अनुसार सटीक और लक्षित उपाय दें  
- हर उपाय के पीछे कारण अवश्य बताएं  
- कम से कम शामिल करें:
  • 1 जप / मंत्र (वैदिक)  
  • 1 व्यवहारिक अनुशासन (daily habit)  
  • 1 दान / ऊर्जा संतुलन उपाय  
- लाल किताब / पारंपरिक उपाय उपयोग कर सकते हैं  
- उपाय सरल, सटीक और लागू करने योग्य हों  
- कोई generic उपाय न दें  
- कोई महंगे रत्न या अवास्तविक उपाय न दें  

8. भविष्य ({years_text})  

- वर्ष अनुसार प्रवृत्ति बताएं  
- हर वर्ष के साथ छोटा practical संकेत दें  
- किस दिशा में ध्यान देना है स्पष्ट करें  

9. अंतिम संदेश  

- पूरी रिपोर्ट का सार  
- जीवन के लिए स्पष्ट दिशा  
- 1 मजबूत Pro Tip (practical और impactful)  
- tone गुरु जैसा हो  

---

🔷 महत्वपूर्ण नियम:

- सभी 9 sections लिखना अनिवार्य है  
- कोई section skip नहीं करना है  
- हर section में कम से कम एक unique insight हो  
- repetition बिल्कुल न हो  
- कोई सामान्य या घिसे-पिटे वाक्य न लिखें  
- हर बात observation या विश्लेषण पर आधारित हो  

---

🔷 भाषा:

सरल, स्पष्ट, प्रभावशाली हिंदी  
ऐसी लगे जैसे किसी अनुभवी हस्तरेखा विशेषज्ञ ने स्वयं लिखी हो  

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
