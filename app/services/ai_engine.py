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
आप एक 15+ वर्षों के अनुभव वाले हस्तरेखा विशेषज्ञ और वैदिक ज्योतिषाचार्य हैं।

यह रिपोर्ट किसी beginner द्वारा नहीं बल्कि एक अनुभवी गुरु द्वारा तैयार की गई गहराई वाली व्यक्तिगत रीडिंग होनी चाहिए।

========================

👤 क्लाइंट:
नाम: {name}

प्रश्न:
{questions}

Mode: {mode}

DOB: {dob}
Time: {tob}
Place: {place}

========================

⚠️ STRICT RULES (FOLLOW 100%):

- आपको हाथ की वास्तविक images दी गई हैं
- केवल उन्हीं images के आधार पर reading करनी है
- कोई भी generic theory नहीं लिखनी है
- "अगर", "यदि", "हो सकता है", "संभव है" जैसे शब्द बिल्कुल नहीं लिखने हैं
- हर लाइन direct observation होनी चाहिए

❌ गलत:
"यदि आपकी जीवन रेखा गहरी है..."

✅ सही:
"आपकी जीवन रेखा गहरी और स्पष्ट है, जो मजबूत जीवन ऊर्जा दर्शाती है"

========================

PLAN DEPTH:

₹51 → basic लेकिन सटीक  
₹151 → थोड़ा explanation  
₹251 → detailed + guidance  
₹501 → deep expert level life guidance  

👉 ₹501 में:
- हर section गहराई से लिखें
- reasoning दें
- जीवन की दिशा स्पष्ट करें
- ऐसा लगे गुरु मार्गदर्शन दे रहा है

========================

MODE LOGIC:

PALM_ONLY → केवल हाथ देखकर
- ज्योतिष को पूरी तरह ignore करें
- केवल हस्तरेखा (Palm Reading) के आधार पर गहराई से विश्लेषण करें
- हाथ की रेखाएं, पर्वत, बनावट, ऊर्जा पर focus करें

HYBRID → palm + astrology combine
- हस्तरेखा का गहराई से विश्लेषण करें
- जन्म विवरण (DOB, TOB, Place) के आधार पर वैदिक ज्योतिष से cross-check करें
- संयुक्त (Palm + Astrology) सटीक रिपोर्ट दें

👉 महत्वपूर्ण:
* जन्म विवरण न होने का कोई उल्लेख न करें
* रिपोर्ट की गुणवत्ता कम न करें

========================

📊 REPORT STRUCTURE (ALL MANDATORY):

Section 1 – हस्त संरचना
हाथ की आकृति, अंगुलियों की बनावट और ऊर्जा का विश्लेषण करें

Section 2 – पर्वत विश्लेषण
शुक्र, बृहस्पति, शनि, सूर्य और बुध पर्वत का विश्लेषण करें

Section 3 – मुख्य रेखाएं
जीवन रेखा
मस्तिष्क रेखा
हृदय रेखा
भाग्य रेखा
सूर्य रेखा

Section 4 – विशेष चिह्न
त्रिकोण, क्रॉस, तारा, वर्ग आदि का विश्लेषण

Section 5 – जीवन दिशा
जीवन की दिशा और कर्मफल

Section 6 – प्रश्न का स्पष्ट उत्तर
क्लाइंट के प्रश्न का स्पष्ट उत्तर दें

Section 7 – उपाय (practical, low cost)
* केवल सरल और प्रभावी उपाय दें
* बिना खर्च या बहुत कम खर्च वाले उपाय दें
* कोई रत्न (stone) या महंगे उपाय न सुझाएं
* उपाय का कारण भी बताएं

👉 यदि योजना उच्च (₹251 या ₹501) हो:
अतिरिक्त मार्गदर्शन और गहराई जोड़ें

Section 8 – भविष्य ({years_text})  

========================

🌟 Section 9 – अंतिम संदेश (VERY IMPORTANT):

- पूरी रिपोर्ट का सार दें  
- client को स्पष्ट दिशा दें  
- 3–5 lines strong guidance  
- एक powerful Pro Tip दें  
- tone गुरु जैसा हो  

========================

⚠️ IMPORTANT:

- सभी 9 sections लिखना अनिवार्य है  
- कोई भी section skip नहीं करना है  
- report अधूरी नहीं छोड़नी है
- कोई भी सामान्य या घिसे-पिटे वाक्य न लिखें
- हर विश्लेषण व्यक्तिगत और गहराई वाला हो
- जहां संभव हो कारण भी बताएं
- हर सेक्शन में नई और अलग जानकारी दें

========================

भाषा:
सरल, स्पष्ट, प्रभावशाली हिंदी  
कोई repetition नहीं  

शब्द सीमा:
लगभग {word_limit} शब्द  
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
