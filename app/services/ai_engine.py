from openai import OpenAI
import os
from app.database import get_db, release_db

# 🔥 SWITCH (VERY IMPORTANT)
USE_REAL_AI = True   # 👉 False = dummy | True = real AI

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
    elif "₹151" in plan:
        word_limit = 700
        years_text = "वर्ष 1 से 3 तक स्पष्ट पूर्वानुमान दें"
        max_tokens = 800
    elif "₹251" in plan:
        word_limit = 1000
        years_text = "वर्ष 1 से 4 तक विस्तृत पूर्वानुमान दें"
        max_tokens = 1000
    else:
        word_limit = 1300
        years_text = "वर्ष 1 से 5 तक अत्यंत गहराई वाला पूर्वानुमान दें"
        max_tokens = 1500   # 🔥 TOP PLAN (IMPORTANT)

    # ---------- FINAL STRICT PROMPT ----------
    prompt = f"""
आप एक अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिष सलाहकार हैं।

नीचे दिए गए विवरण और हाथ की images के आधार पर व्यक्तिगत विश्लेषण तैयार करें।

क्लाइंट: {name}  
प्रश्न: {questions}  
Mode: {mode}  
DOB: {dob}, Time: {tob}, Place: {place}  

----------------------

निर्देश:

- हाथ की images में जो स्पष्ट दिखाई देता है उसी का विश्लेषण करें  
- पारंपरिक हस्तरेखा ज्ञान के आधार पर व्याख्या दें  
- निश्चित भविष्यवाणी करने के बजाय प्रवृत्ति (tendency) बताएं  
- "अगर/यदि/हो सकता है" जैसे शब्द न लिखें  
- भाषा स्पष्ट, सीधी और आत्मविश्वासपूर्ण हो  

----------------------

PLAN GUIDELINE:

₹51 → संक्षिप्त और सटीक  
₹151 → थोड़ा विस्तार  
₹251 → detailed + guidance  
₹501 → गहराई + जीवन दिशा + स्पष्ट मार्गदर्शन  

----------------------

REPORT STRUCTURE:

1. हस्त संरचना  
2. पर्वत विश्लेषण  
3. मुख्य रेखाएं  
4. विशेष चिह्न  
5. जीवन दिशा  
6. प्रश्न का उत्तर  
7. उपाय (सरल और व्यावहारिक)  
8. भविष्य ({years_text})  

9. अंतिम संदेश:  
- पूरी रिपोर्ट का सार  
- 3–5 लाइन guidance  
- एक practical Pro Tip  

----------------------

महत्वपूर्ण:

- सभी sections शामिल करें  
- हर section में अलग और उपयोगी जानकारी दें  
- report अधूरी न छोड़ें  

----------------------

भाषा: सरल, स्पष्ट हिंदी  
लंबाई: लगभग {word_limit} शब्द  
"""

    # ---------- DUMMY MODE ----------
    if not USE_REAL_AI:
        draft = f"""
Section 1 – हस्त संरचना
यह टेस्ट रिपोर्ट है।

Section 2 – पर्वत
संतुलन दिखाई देता है।

Section 3 – रेखाएं
जीवन रेखा स्पष्ट है।

Section 4 – संकेत
सकारात्मक संकेत हैं।

Section 5 – जीवन दिशा
स्थिरता आएगी।

Section 6 – उत्तर
आपको focus बढ़ाना होगा।

Section 7 – उपाय
सुबह सूर्य को जल दें।

Section 8 – भविष्य
वर्ष 1: सुधार
वर्ष 2: स्थिरता

Section 9 – अंतिम संदेश
आप सही दिशा में हैं।
👉 Pro Tip: एक ही लक्ष्य पर लगातार काम करें।
"""
    else:
        # ---------- REAL AI ----------
        content = [{"type": "text", "text": prompt}]

        for img in image_urls[:4]:
            content.append({
                "type": "image_url",
                "image_url": {"url": img}
            })

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.6,
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
