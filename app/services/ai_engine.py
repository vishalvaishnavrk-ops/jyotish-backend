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
"""

    # ---------- IMAGE LOGIC ----------
    selected_images = image_urls[:4] if "₹501" in plan else image_urls[:2]

    # ---------- FINAL PROMPT ----------
    prompt = f"""
आप 15+ वर्षों के अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिष सलाहकार हैं।

क्लाइंट: {name}
प्रश्न: {questions}
Mode: {mode}
DOB: {dob}, Time: {tob}, Place: {place}

---

विशेष निर्देश:
{depth_note}

---

FORMAT STRICT:

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

RULES:

- रिपोर्ट सीधे Section 1 से शुरू करें
- कोई markdown न लिखें
- हर section में नई जानकारी दें
- generic बात न करें
- observation + reasoning दें

---

उपाय:

- समस्या आधारित हों
- जप + अनुशासन + दान शामिल करें
- कारण सहित दें
- सटीक और लागू करने योग्य हों

---

भाषा: सरल लेकिन विशेषज्ञ स्तर की हिंदी  
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
