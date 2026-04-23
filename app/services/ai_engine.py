from openai import OpenAI
import os
from app.database import get_db, release_db

USE_REAL_AI = True

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_draft(client_id):

    # ---------- FETCH ----------
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
        if c.fetchone()[0] == 1:
            return "AI already generated"

        name, questions, plan, dob, tob, place, images = data

    finally:
        release_db(conn)

    # ---------- IMAGES ----------
    image_urls = []
    if images:
        image_urls = [img.strip() for img in images.split(",") if img.strip()]

    # ---------- MODE ----------
    mode = "HYBRID" if dob and tob and place else "PALM_ONLY"

    # ---------- PLAN CONFIG ----------
    if "₹51" in plan:
        word_limit = 400
        max_tokens = 500
        years_text = "केवल वर्ष 1–2"
        depth_note = "केवल मुख्य संकेत दें, ज्यादा विस्तार न करें"

    elif "₹151" in plan:
        word_limit = 700
        max_tokens = 800
        years_text = "वर्ष 1–3"
        depth_note = "हर observation के साथ छोटा कारण दें"

    elif "₹251" in plan:
        word_limit = 1000
        max_tokens = 1100
        years_text = "वर्ष 1–4"
        depth_note = "हर रेखा और पर्वत का कारण सहित विश्लेषण करें"

    else:  # ₹501
        word_limit = 1400
        max_tokens = 1800
        years_text = "वर्ष 2026 से अगले 5 वर्षों तक"
        depth_note = """
हर मुख्य रेखा और पर्वत के लिए:
- स्पष्ट observation दें
- उसका कारण (क्यों) बताएं
- जीवन पर प्रभाव बताएं
- palm + jyotish cross analysis दें
- generic बात बिल्कुल न करें
- Section 6 और Section 9 पर विशेष ध्यान दें  
- प्रश्न का उत्तर detailed और सटीक हो  
- अंतिम संदेश impactful और याद रहने वाला हो
"""

    # ---------- IMAGE LOGIC ----------
    selected_images = image_urls[:4] if "₹501" in plan else image_urls[:2]

    # ---------- FINAL PROMPT ----------
    prompt = f"""
आप एक अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिष सलाहकार हैं, जिनका अनुभव 15+ वर्षों का है।

आपको क्लाइंट के हाथों की images और जन्म विवरण दिए गए हैं।  
आपका कार्य एक गहराई से की गई, वास्तविक और व्यक्तिगत विश्लेषण रिपोर्ट तैयार करना है।

क्लाइंट: {name}
प्रश्न: {questions}
Mode: {mode}
DOB: {dob}, Time: {tob}, Place: {place}

---

विशेष निर्देश:
{depth_note}

---

रिपोर्ट Structure:

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

लेखन निर्देश:

- रिपोर्ट सीधे Section 1 से शुरू करें  
- भाषा विशेषज्ञ और सरल हिंदी में हो  
- हर observation के साथ उसका कारण और प्रभाव बताएं  
- generic या किताबी बातें न लिखें  
- हर section में 3–5 बिंदु दें  
- हर बिंदु 2–3 पंक्तियों में समझाएं  

---

विशेष ध्यान (₹501 के लिए):

- रिपोर्ट विस्तृत और गहराई वाली हो  
- हर रेखा और पर्वत का विस्तार से विश्लेषण करें  
- palm और (यदि HYBRID) ज्योतिष दोनों का उपयोग करें  
- रिपोर्ट पढ़ते समय expert guidance का अनुभव हो  

---

Section 6 – प्रश्न का उत्तर:

- क्लाइंट के प्रश्न का सीधा और स्पष्ट उत्तर दें  
- practical और actionable दिशा दें  
- palm/jyotish के आधार पर reasoning दें  

---

Section 7 – उपाय:

- समस्या के अनुसार 3–4 सटीक उपाय दें  
- हर उपाय के साथ कारण बताएं  
- उपाय practical और लागू करने योग्य हों  
- जप, दान, अनुशासन शामिल करें  

---

Section 8 – भविष्य:

- प्रत्येक वर्ष अलग paragraph में लिखें  
- क्या होगा + क्यों होगा + क्या ध्यान रखें  

---

Section 9 – अंतिम संदेश:

- पूरी रिपोर्ट का सार दें  
- जीवन की स्पष्ट दिशा दें  
- tone अनुभवी गुरु जैसा हो  
- अंत में एक strong practical Pro Tip दें  

---

भाषा: प्रभावशाली, स्पष्ट, और मार्गदर्शक हिंदी  
लंबाई: लगभग {word_limit} शब्द
"""

    # ---------- DUMMY ----------
    if not USE_REAL_AI:
        draft = "Dummy report"
    else:

        content = [{"type": "text", "text": prompt}]

        for img in selected_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": img}
            })

        try:
            response = client.chat.completions.create(
                model="gpt-4o",   # 🔥 FINAL MODEL
                messages=[{"role": "user", "content": content}],
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
