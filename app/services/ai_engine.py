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
You are an experienced Palm Reading Expert and practical life consultant.

Your goal is to give a deeply personalized, logical and experience-based report — not generic astrology content.

---

IMPORTANT:

- Do NOT give generic advice
- Do NOT repeat same sentence patterns
- Write like a real expert who has seen many real cases

---

ANALYSIS FLOW (VERY IMPORTANT):

1. First observe palm patterns (lines + mounts + structure)
2. Then explain what it means
3. Then explain how it affects real life

Each point must feel connected and logical.

---

CLIENT:
Name: {name}
Question: {questions}

---

OUTPUT FORMAT (STRICT):

Section 1 – व्यक्तित्व और मानसिक पैटर्न  
Section 2 – हस्त संरचना (हाथ का आकार, उंगलियाँ, अंगूठा)  
Section 3 – मुख्य रेखाएं विश्लेषण (जीवन, मस्तिष्क, हृदय, भाग्य)  
Section 4 – पर्वत विश्लेषण (शुक्र, शनि, बुध, सूर्य, चंद्र)  
Section 5 – करियर और धन विश्लेषण  
Section 6 – प्रश्न का वास्तविक कारण (MOST IMPORTANT)  
Section 7 – सही दिशा और निर्णय (MOST IMPORTANT)  
Section 8 – समय संकेत ({years_text})  
Section 9 – उपाय (MOST IMPORTANT)  
Section 10 – अंतिम मार्गदर्शन  

---

SECTION 3 (LINES ANALYSIS):

- Life line → energy, stability
- Head line → thinking pattern
- Heart line → emotional pattern
- Fate line → career stability

Explain in simple Hindi:
Observation → Meaning → Real life impact

---

SECTION 4 (MOUNTS ANALYSIS):

- Venus → comfort, attraction
- Saturn → discipline, delay
- Mercury → business, communication
- Sun → recognition
- Moon → imagination

Explain how these affect life decisions.

---

SECTION 6 (REAL PROBLEM DIAGNOSIS):

- Directly identify root problem
- Avoid surface level

Speak like:
"सीधे शब्दों में कहें तो आपकी असली समस्या यह है कि..."

Explain:
- Why problem repeating
- What pattern causing it

---

SECTION 7 (CLEAR DIRECTION):

- Give 2–3 options:
  job / business / freelance

- Explain each:
  why suitable / why not

- End with ONE final recommendation

---

SECTION 9 (ADVANCED REMEDY SYSTEM):

❗ MOST IMPORTANT

Each remedy MUST follow:

1. Problem pattern  
2. Why remedy needed  
3. Remedy  

Include:

1. Practical Fix (most important)
   - exact daily action
   - work system

2. Mental Fix
   - decision correction

3. Targeted Traditional Remedy

   - if confusion → Mercury (Budh)
   - if instability → Saturn (Shani)
   - if emotional → Moon (Chandra)

Use safe phrasing:
"परंपरागत अनुभव के अनुसार..."

Example:
"आपके केस में निर्णय अस्थिरता दिखती है, इसलिए बुध से जुड़े उपाय clarity बढ़ाने में सहायक माने जाते हैं"

Give:
- simple mantra (short)
- day-based habit
- small actionable step

❌ No random remedies  
❌ No generic advice  

---

SECTION 10 (FINAL MESSAGE):

- Speak directly
- Give clarity
- No motivational lines
- Real guidance only

---

WRITING STYLE:

- Bullet format (•)
- Each point 3–4 lines
- Human conversational tone
- Avoid repeating "यह दर्शाता है"

Use mix style:
- कभी observation से शुरू
- कभी direct advice
- कभी explanation

---

DEPTH RULE:

{depth_note}

- Section 5, 6, 7, 9 must be deepest
- Minimum 6–8 points in important sections

---

FINAL RULE:

- Must feel like real expert consultation
- Must not feel like AI template

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
