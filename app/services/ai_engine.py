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
- हर section में कम से कम 6–8 bullet points
- हर point में Observation → Meaning → Impact
- हर point minimum 3–4 lines
- Section 5, 6, 9 सबसे detailed हों
- Solutions practical + traditional दोनों हों
- Report detailed और multi-page होनी चाहिए
"""

    # ---------- IMAGE SELECTION ----------
    if "₹501" in plan:
        selected_images = image_urls[:4]
    elif "₹251" in plan:
        selected_images = image_urls[:4]
    else:
        selected_images = image_urls[:2]

    # ---------- FINAL PROMPT ----------
    prompt = f"""
You are an experienced Palm Reading Analyst with knowledge of traditional Vedic practices.

Your goal is to generate a deeply personalized, practical, and insight-rich report.

---

IMPORTANT SAFETY RULE:
- Do NOT make guaranteed future predictions
- Use words like: संकेत, संभावना, रुझान
- Remedies should be described as traditional or experience-based guidance

---

ANALYSIS APPROACH:

- Primary base: Palm reading (lines, mounts, structure)
- If birth details available: use basic astrology as supporting insight
- Astrology should support palm reading, not dominate

---

CORE ANALYSIS RULE (STRICT):

Each bullet point MUST follow:

Observation → Meaning → Life Impact

If this is not followed, the answer is incomplete.

---

PERSONALIZATION RULE:

- Report must feel specific to the person
- Avoid generic statements
- Use relatable lines:
  "आपने कई बार महसूस किया होगा कि..."
  "जीवन में बार-बार यह स्थिति बनती है कि..."
  "निर्णय लेते समय अंदर द्वंद्व रहता है..."

---

CLIENT DETAILS:
Name: {name}
Question: {questions}

---

OUTPUT FORMAT (STRICT — DO NOT CHANGE):

Section 1 – व्यक्तित्व विश्लेषण  
Section 2 – हस्त संरचना  
Section 3 – मुख्य रेखाएं  
Section 4 – पर्वत विश्लेषण  
Section 5 – करियर और धन  
Section 6 – प्रश्न का वास्तविक कारण और समाधान  
Section 7 – संबंध जीवन  
Section 8 – स्वास्थ्य संकेत  
Section 9 – समय संकेत ({years_text})  
Section 10 – उपाय और सलाह  
Section 11 – अंतिम संदेश  

---

SPECIAL INSTRUCTIONS:

### Section 6 (MOST IMPORTANT)

- User के प्रश्न का deep analysis करो
- Palm reading से कारण निकालो
- Direct logical explanation दो
- फिर समाधान दो:

Solutions may include:
- practical steps
- habit changes
- traditional remedies (like mantra, daan, routine practices)
- mindset correction

Use safe phrasing like:
"परंपरागत मान्यताओं के अनुसार..."
"अनुभव के आधार पर यह उपाय सहायक माने जाते हैं..."

---

### Section 9 (Timeline)

- Time-based संकेत दो
- Example style:
  "2026 के दौरान..."
  "2027–2029 के बीच..."
  "इस अवधि में परिवर्तन के संकेत दिखते हैं..."

- Palm + astrology (if available) alignment दिखाओ

---

### Section 10 (Remedies)

- Personalized remedies based on analysis
- Can include:
  - simple mantra (no extreme claims)
  - daily discipline
  - behavioral correction
  - focus practices

- Avoid fear-based language

---

### WRITING STYLE:

- Bullet format only (•)
- Each bullet new line
- Each point 3–4 lines minimum
- No paragraphs
- Clear spacing (PDF friendly)

---

### DEPTH FORCE:

{depth_note}

Additionally:
- Minimum 6–8 bullet points per section
- Detailed explanation required
- Especially Section 5, 6, 9 must be very deep

---

FINAL NOTE:

- Do not write generic advice
- Do not repeat lines
- Make report feel like expert personal consultation

---

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
