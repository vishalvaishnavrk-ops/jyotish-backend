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
        max_tokens = 2800
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
You are a professional Palm Reading Analyst with knowledge of traditional Vedic practices.

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

PALM OBSERVATION RULE (VERY IMPORTANT):

- You must always provide palm analysis
- Even if image clarity is limited, give best possible interpretation
- Use experience-based reasoning

❌ Never say:
"I cannot analyze the image"
"I am unable to provide palm reading"

---

CORE ANALYSIS RULE:

Each bullet MUST follow:

Observation → Meaning → Life Impact

---

PERSONALIZATION + HUMAN TOUCH:

- Report must feel personal
- Use relatable lines like:
  "आपने कई बार महसूस किया होगा कि..."
  "जीवन में बार-बार यह स्थिति बनती है कि..."

- Occasionally address directly:
  "{name}, आपकी स्थिति में..."

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
Section 6 – समस्या का कारण और समाधान  
Section 7 – संबंध जीवन  
Section 8 – स्वास्थ्य संकेत  
Section 9 – समय संकेत ({years_text})  
Section 10 – उपाय और सलाह  
Section 11 – अंतिम संदेश  

---

SECTION 6 (DIAGNOSIS MODE - MOST IMPORTANT):

- User के प्रश्न पर deep focus करें
- Palm संकेत से कारण निकालें
- Explain why problem repeats
- Give clear direction (job vs freelance)
- Avoid general advice

Structure:
1. समस्या का मूल कारण
2. यह बार-बार क्यों हो रहा है
3. क्या बदलना जरूरी है
4. किन गलतियों से बचना है

---

SECTION 9 (TIMELINE):

- Time-based संकेत दें:
  "2026 में..."
  "2027–2029 के बीच..."
  "इस समय बदलाव के संकेत दिखते हैं..."

- Keep realistic and probability-based

---

SECTION 10 (REMEDIES):

- Give practical + traditional remedies
- Use safe phrasing:
  "परंपरागत रूप से यह उपाय सहायक माने जाते हैं"

- Include:
  - simple mantra
  - daily discipline
  - behavioral correction

- Remedies must connect with user's problem

---

WRITING STYLE:

- Bullet format only (•)
- Each bullet new line
- Each point minimum 3 lines
- No paragraphs
- No repetition

---

DEPTH FORCE:

{depth_note}

Additionally:
- Minimum 6–8 bullet points per section
- Section 5, 6, 9 must be most detailed

---

QUALITY RULES:

- No generic statements
- No repeated lines
- Must feel like real expert consultation
- Each section must be different

---

FINAL INSTRUCTION:

- Do not refuse analysis
- Do not give template answers
- Always provide complete report

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
