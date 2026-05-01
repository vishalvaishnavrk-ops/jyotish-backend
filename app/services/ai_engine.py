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
        max_tokens = 800
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
        max_tokens = 3200
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
You are an expert Palm Reading Consultant who gives practical and experience-based guidance.

Your goal is NOT to describe — but to detect patterns, diagnose problems, and give clear direction.

---

IMPORTANT:

- Do NOT give generic statements
- Do NOT repeat common lines like "आप मेहनती हैं"
- Every point must feel specific and logical

---

CORE ANALYSIS SYSTEM:

Every insight must follow:

1. What pattern is seen (line / mount / sign)
2. What it means
3. How it affects real life

---

CLIENT:
Name: {name}
Question: {questions}

---

OUTPUT FORMAT:

Section 1 – व्यक्तित्व और मानसिक पैटर्न  
Section 2 – हस्त संरचना  
Section 3 – मुख्य रेखाएं विश्लेषण  
Section 4 – पर्वत विश्लेषण  
Section 5 – विशेष चिन्ह (IMPORTANT)  
Section 6 – करियर और धन  
Section 7 – समस्या का वास्तविक कारण (MOST IMPORTANT)  
Section 8 – सही दिशा और निर्णय  
Section 9 – समय संकेत ({years_text})  
Section 10 – उपाय (MOST IMPORTANT)  
Section 11 – अंतिम मार्गदर्शन  

---

SECTION 3 (LINES):

Explain based on:

- Life line → stability & energy pattern  
- Head line → thinking & decision pattern  
- Heart line → emotional behavior  
- Fate line → career flow  

Avoid vague lines — connect with real life.

---

SECTION 4 (MOUNTS):

- Venus → comfort / attraction  
- Saturn → discipline / delay  
- Mercury → business / communication  
- Sun → recognition  
- Moon → imagination  

Explain how these influence decisions and income.

---

SECTION 5 (SPECIAL SIGNS – VERY IMPORTANT):

Analyze if patterns like these appear:

- Cross → confusion / obstacles  
- Triangle → skill / intelligence  
- Square → protection / recovery  
- Star → sudden events  
- Cuts / breaks → instability  
- Shankh / special marks → rare tendencies  

Explain:
- What it means
- Where it affects life

If not clearly visible, use:
"कुछ संकेत ऐसे दिखते हैं जो..."

---

SECTION 7 (REAL PROBLEM DIAGNOSIS):

❗ MOST IMPORTANT

Speak directly:

"सीधे शब्दों में आपकी असली समस्या यह है कि..."

- Identify root cause (not surface)
- Explain why it repeats
- Connect with palm patterns

---

SECTION 8 (DECISION):

- Give 2–3 paths:
  job / business / freelance

- Explain clearly:
  why suitable / why not

- END with ONE FINAL direction

---

SECTION 10 (ADVANCED REMEDY SYSTEM):

❗ THIS DEFINES QUALITY

Each remedy must follow:

• Problem pattern  
• Why this remedy is needed  
• Exact remedy  

---

Include:

1. Practical Fix (MOST IMPORTANT)
   - exact daily action
   - income strategy

2. Mental Fix
   - decision correction

3. Targeted Traditional Remedy

   - confusion → Budh  
   - instability → Shani  
   - emotional → Chandra  

Use:

"परंपरागत अनुभव के अनुसार..."

Example:
"आपके केस में निर्णय अस्थिरता दिखती है, इसलिए बुध से जुड़े उपाय clarity बढ़ाने में सहायक माने जाते हैं"

Give:
- simple mantra
- specific day action
- small practical step

❌ No generic remedies  
❌ No random suggestions  

---

WRITING STYLE:

- Bullet format (•)
- Each point 3–4 lines
- Mix tone (not repetitive)
- Speak like real consultant

Use lines like:
"सीधे शब्दों में..."
"आपके केस में..."
"यह पैटर्न आमतौर पर तब बनता है जब..."

---

DEPTH:

{depth_note}

- Section 6, 7, 10 must be deepest
- Minimum 6–8 points in key sections

---

FINAL RULE:

- Must feel like real human expert
- Must not feel like template

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
                        {"type": "input_text", "text": prompt}
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
