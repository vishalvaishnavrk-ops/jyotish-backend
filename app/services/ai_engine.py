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
आप एक अनुभवी हस्तरेखा विश्लेषक (Palm Analyst) और जीवन मार्गदर्शक हैं, जिनका अनुभव 15+ वर्षों का है।

आपको क्लाइंट के हाथों की images और व्यक्तिगत विवरण दिए गए हैं।

आपका कार्य:
हाथ की रेखाओं, पर्वतों, बनावट और संरचना के आधार पर व्यक्ति के स्वभाव, निर्णय शैली, जीवन पैटर्न और संभावित दिशा का गहराई से विश्लेषण करना।

⚠️ महत्वपूर्ण:
- आप निश्चित भविष्यवाणी न करें  
- आप केवल संकेत, प्रवृत्ति और संभावित दिशा के आधार पर विश्लेषण करें  
- रिपोर्ट मार्गदर्शन आधारित हो, अंधविश्वासी भविष्यवाणी नहीं  

---

क्लाइंट विवरण:

नाम: {name}  
प्रश्न: {questions}  
Mode: {mode}  
DOB: {dob}  
Time: {tob}  
Place: {place}  

---

📊 रिपोर्ट Structure (strict):

Section 1 – हस्त संरचना  
Section 2 – पर्वत विश्लेषण  
Section 3 – मुख्य रेखाएं  
Section 4 – विशेष संकेत  
Section 5 – जीवन दिशा  
Section 6 – प्रश्न का उत्तर  
Section 7 – उपाय  
Section 8 – संभावित दिशा ({years_text})  
Section 9 – अंतिम संदेश  

---

🧠 लेखन निर्देश:

- रिपोर्ट सीधे Section 1 से शुरू करें  
- भाषा सरल लेकिन विशेषज्ञ स्तर की हिंदी में हो  
- हर section में 3–5 बिंदु दें  
- हर बिंदु 2–3 पंक्तियों में समझाया जाए  
- हर observation के साथ उसका प्रभाव (impact) बताएं  
- generic या किताबी भाषा का उपयोग न करें  

---

🔍 विश्लेषण गहराई (₹501 के लिए विशेष ध्यान):

- हाथ की रेखाओं और पर्वतों का विस्तार से विश्लेषण करें  
- हर मुख्य रेखा (जीवन, मस्तिष्क, हृदय, भाग्य) अलग-अलग समझाएं  
- पर्वतों की मजबूती/कमजोरी का अर्थ बताएं  
- observations को वास्तविक जीवन से जोड़ें  
- रिपोर्ट पढ़ते समय expert guidance का अनुभव होना चाहिए  

---

❓ Section 6 – प्रश्न का उत्तर:

- क्लाइंट के प्रश्न का सीधा और स्पष्ट उत्तर दें  
- उत्तर practical और actionable होना चाहिए  
- analysis के आधार पर दिशा दें  
- vague या general जवाब न दें  

---

🪔 Section 7 – उपाय:

- 3–4 practical और लागू करने योग्य उपाय दें  
- उपाय सरल, सटीक और वास्तविक जीवन में उपयोगी हों  
- जप, अनुशासन, व्यवहार सुधार या ऊर्जा संतुलन आधारित सुझाव दें  
- हर उपाय के साथ उसका उद्देश्य (क्यों) बताएं  

---

📅 Section 8 – संभावित दिशा:

- हर वर्ष अलग paragraph में लिखें  
- क्या संभावित परिवर्तन हो सकते हैं  
- किस क्षेत्र में ध्यान देना चाहिए  
- इसे निश्चित भविष्य नहीं, बल्कि दिशा के रूप में लिखें  

---

🌟 Section 9 – अंतिम संदेश:

- पूरी रिपोर्ट का सार दें  
- जीवन के लिए स्पष्ट दिशा दें  
- tone अनुभवी मार्गदर्शक जैसा हो  
- अंत में एक मजबूत और practical Pro Tip दें (नई लाइन में)  

---

✍️ लेखन शैली:

- flow natural और conversational हो  
- ऐसा लगे कि विशेषज्ञ सीधे समझा रहा है  
- हर section आपस में जुड़ा हुआ लगे  

---

भाषा: स्पष्ट, प्रभावशाली और मार्गदर्शक हिंदी  
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
            response = client.responses.create(
                model="gpt-4o",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            *[
                                {"type": "input_image", "image_url": img}
                                for img in selected_images
                            ]
                        ]
                    }
                ],
                temperature=0.7,
                max_output_tokens=max_tokens
            )

            draft = response.output_text
            
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
