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
- और सेक्शन के हिसाब से हथेली को पहले पढ़ के प्रॉपर ऑब्जरवेशन कर के फिर फाइनल जानकारी प्रेषित करे
  ताकि रिपोर्ट पढ़ने वाले को लगे की रिपोर्ट किसी ज्योतिषाचार्य ने या हस्त विशेषज्ञ ने बनायीं है

Section 6 – प्रश्न का उत्तर (VERY IMPORTANT):
- क्लाइंट के प्रश्न को ध्यान से पढ़कर सीधे उसी पर जवाब दें  
- उत्तर स्पष्ट, practical और actionable होना चाहिए  
- palm observation और (यदि HYBRID) ज्योतिष से support दें  
- vague/general सलाह न दें  
- जहाँ संभव हो, step-by-step दिशा दें  
- यदि प्रश्न आर्थिक/रिश्ते/करियर से जुड़ा है तो उसी context में विश्लेषण करें

Section 9 – अंतिम संदेश (HIGH IMPACT):

- यह पूरी रिपोर्ट का सार होना चाहिए  
- क्लाइंट को स्पष्ट जीवन दिशा दें  
- tone अनुभवी गुरु जैसा हो, आत्मविश्वासी और मार्गदर्शक  

- कम से कम 5–6 पंक्तियों में गहराई से समझाएं  
- सामान्य motivational बातें न लिखें  
- client की वास्तविक स्थिति के अनुसार सार दें  

- अंतिम संदेश पढ़कर क्लाइंट को लगे कि उसे सही दिशा मिल गई है  

👉 Pro Tip:
- Pro Tip नई लाइन में लिखें  
- यह अत्यंत practical और प्रभावशाली हो  
- सीधे जीवन में लागू किया जा सके  
---

DEPTH EXPANSION (₹501 ONLY):

- रिपोर्ट इतनी विस्तृत हो कि 7–10 पृष्ठ तक जाए  
- किसी भी section को 2–3 लाइन में समाप्त न करें  
- हर section में कम से कम 3–5 बिंदु लिखें  
- हर बिंदु को 2–3 पंक्तियों में विस्तार से समझाएं  
- हर observation के साथ उसका कारण और प्रभाव अवश्य लिखें
---

SECTION-WISE DEPTH CONTROL:

Section 2 और 3 (पर्वत और रेखाएं):

- प्रत्येक पर्वत/रेखा के लिए:
  1. उसकी वर्तमान स्थिति  
  2. उसका कारण  
  3. जीवन पर प्रभाव  
  4. भविष्य पर प्रभाव  

Section 5 (जीवन दिशा):

- जीवन के pattern, संघर्ष और अवसर को विस्तार से लिखें  
- practical जीवन दिशा दें  

Section 7 (उपाय):

- हर उपाय 2–3 पंक्तियों में explain करें  
- उपाय क्यों काम करेगा यह अवश्य लिखें  

Section 8 (भविष्य):

- हर वर्ष अलग paragraph में लिखें  
- हर वर्ष में कारण + परिणाम + सावधानी दें  
---

लेखन शैली:

- रिपोर्ट conversational और flow में हो  
- ऐसा लगे कि गुरु सीधे समझा रहे हैं  
- हर section पिछले से जुड़ा हुआ लगे  
- अचानक topic change न हो
---

EXPERT REASONING / THINKING / DEPTH BLOCK:

रिपोर्ट लिखने से पहले:
- पहले हाथ की images को ध्यान से देखकर मुख्य संकेत पहचानें  
- हर रेखा और पर्वत की स्थिति को internally समझें  
- फिर उसी आधार पर structured report लिखें  

लिखते समय:
- हर observation को विस्तार से समझाएं (कम से कम 2–3 पंक्तियाँ)  
- केवल नाम न लिखें, उसका प्रभाव और कारण बताएं  
- हर section में कम से कम 3–5 बिंदु दें  
- हर बिंदु अलग लाइन में हो  

महत्वपूर्ण:
- रिपोर्ट पढ़ते समय ऐसा लगे कि विशेषज्ञ ने पहले पूरा हाथ अध्ययन किया, फिर समझाकर लिखा  
- हर section में depth और विस्तार होना अनिवार्य है  
---

उपाय:
- समस्या आधारित हों
- जप + अनुशासन + दान शामिल करें
- कारण सहित दें
- सटीक और लागू करने योग्य हों
- उपाय वैदिक या तांत्रिक परन्तु सात्विक जैसे पीपल के पेड़ में दीपक करना या लाल किताब उपाय या 
स्विच वर्ड्स या हथेली में पर्वत और रेखाओ के मजबूती या कमजोरी के हिसाब उसी गृह को मजबूत करने के लिए उसके सबंधित मंत्र जाप 
या दान या फिर आज के मॉडर्न साइंस और ज्योतिष की और भी शाखाओ के हिसाब से ऐसे उपाय दो 
जो उसकी हथेली की रीडिंग के हिसाब से उसे अपने जीवन को सरल बनाने में सहायता करे!
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
