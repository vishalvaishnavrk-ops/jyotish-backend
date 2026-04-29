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
        max_tokens = 700
        years_text = "अगले 1–2 वर्ष"
        depth_note = """
- केवल मुख्य रेखाओं पर फोकस करें
- कम depth, direct insights
- हर section छोटा रखें
"""

    elif "₹151" in plan:
        max_tokens = 1000
        years_text = "अगले 1–3 वर्ष"
        depth_note = """
- हर observation के साथ छोटा कारण दें
- practical insights जोड़ें
"""

    elif "₹251" in plan:
        max_tokens = 1400
        years_text = "अगले 1–4 वर्ष"
        depth_note = """
- सभी मुख्य रेखाएं और पर्वत cover करें
- reasoning clearly explain करें
- career और finance पर depth दें
"""

    else:  # ₹501
        max_tokens = 2200
        years_text = "2026 से अगले 5 वर्ष"
        depth_note = """
- हर section में कम से कम 5–7 bullet points लिखें
- हर point 3–4 lines का हो
- Timeline, Career और Question section सबसे detailed हों
- Palm + Jyotish cross analysis करें
- Final सलाह powerful और impactful हो
"""

    # ---------- IMAGE SELECTION ----------
    if "₹501" in plan:
        selected_images = image_urls[:4]
    elif "₹251" in plan:
        selected_images = image_urls[:3]
    else:
        selected_images = image_urls[:2]

    # ---------- FINAL PROMPT ----------
    prompt = f"""
You are a professional Palm Reading Expert with strong knowledge of traditional Vedic Astrology principles.

Your analysis should be practical, experience-based, and grounded.

---

ANALYSIS APPROACH:

- Primary analysis MUST be based on palm observations (lines, mounts, structure).
- If birth details are available, you may optionally use basic astrological reasoning to SUPPORT or CROSS-CHECK the palm indications.
- Astrology should be used only as supportive insight, not as absolute prediction.

IMPORTANT SAFETY RULE:
- Do NOT claim guaranteed future events
- Use words like: संकेत, संभावना, रुझान
- Keep insights realistic and experience-based

---

MODE:
{mode}

IF MODE = PALM_ONLY:
- Only palm-based analysis करें
- Astrology का उपयोग न करें

IF MODE = HYBRID:
- Palm reading को primary रखें
- Astrology को supporting logic की तरह use करें
- जहां दोनों match करें वहां confidence बढ़ाकर बताएं

---

ANALYSIS STRUCTURE (VERY IMPORTANT):

हर point में यह 3 चीजें होनी चाहिए:
1. Observation (क्या दिखा)
2. Interpretation (उसका अर्थ)
3. Life Impact (जीवन पर असर)

---

Client Details:
Name: {name}
Question: {questions}

---

OUTPUT FORMAT (STRICT — DO NOT CHANGE):

Section 1 – व्यक्तित्व विश्लेषण
Section 2 – हस्त संरचना
Section 3 – मुख्य रेखाएं
Section 4 – पर्वत विश्लेषण
Section 5 – करियर और धन
Section 6 – प्रश्न का उत्तर
Section 7 – संबंध जीवन
Section 8 – स्वास्थ्य संकेत
Section 9 – समय संकेत ({years_text})
Section 10 – उपाय और सलाह
Section 11 – अंतिम संदेश

---

WRITING STYLE:

- हर section में bullet points लिखें (•)
- हर point नई लाइन में हो
- हर point 2–4 लाइन का हो
- paragraphs बिल्कुल न बनाएं
- भाषा सरल लेकिन expert-level हो

---

PLAN DEPTH:
{depth_note}

---

If palm and astrology indications differ, clearly explain the difference instead of forcing a conclusion.

---

Before generating final answer, think step-by-step like an expert analyst.
Only output final report.
"""

    # ---------- AI CALL ----------
    if not USE_REAL_AI:
        draft = "Dummy report"
    else:
        try:
            response = client.responses.create(
                model="gpt-4o",
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        *[
                            {"type": "input_image", "image_url": img}
                            for img in selected_images
                        ]
                    ]
                }],
                temperature=0.75,
                max_output_tokens=max_tokens
            )

            draft = response.output_text.strip()

            # ---------- FORMAT FIX ----------
            draft = draft.replace("• ", "\n• ")

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
