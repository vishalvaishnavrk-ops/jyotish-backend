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
- हर section में 5–7 high quality bullet points हों (बेकार repetition न हो)
- हर point में 3 layer होनी चाहिए:
  1. Observation (क्या pattern दिखता है)
  2. Reason (यह pattern क्यों बनता है)
  3. Life Impact (इसका असली जीवन पर असर क्या है)

- हर point minimum 3–5 lines में explain हो (जल्दी-जल्दी summary न हो)

- Section 6 (problem diagnosis) में कम से कम 6–8 deep points हों
  - हर point root cause explain करे
  - surface level explanation न हो

- Section 9 (remedy) सबसे practical और powerful होना चाहिए
  - हर remedy में WHY + HOW + DURATION (21/40/90 days) शामिल हो
  - remedy problem से directly जुड़ा हो

- Section 8 (timeline) में year-wise clear explanation हो:
  - 2026 → क्या और क्यों
  - 2027–2028 → transition
  - 2029–2030 → growth

- Report structured और readable हो:
  - हर point अलग line में
  - sections clear हों
  - unnecessary repetition न हो

- Language simple लेकिन expert-level हो
- Report ऐसा लगे कि किसी experienced consultant ने बनाया है, ना कि AI ने
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
You are an expert Palm Reading Consultant who analyzes patterns deeply and gives real-life guidance.

Your goal is NOT to describe personality — but to detect patterns, explain root causes, and give clear direction.

---

CORE THINKING PROCESS (VERY IMPORTANT):

For every point follow:

1. What pattern is seen (line / mount / structure / sign)
2. Why this pattern forms
3. How it affects real life decisions
4. What problem it creates

Do not skip reasoning.

---

CLIENT:
Name: {name}
Question: {questions}

---

OUTPUT STRUCTURE:

Section 1 – हस्त संरचना  
Section 2 – पर्वत विश्लेषण  
Section 3 – मुख्य रेखाएं  
Section 4 – विशेष संकेत  
Section 5 – जीवन और करियर पैटर्न  
Section 6 – समस्या का वास्तविक कारण (MOST IMPORTANT)  
Section 7 – सही दिशा और निर्णय  
Section 8 – समय संकेत ({years_text})  
Section 9 – उपाय (MOST IMPORTANT)  
Section 10 – अंतिम मार्गदर्शन  

---

SECTION 1 (HAND STRUCTURE):

- Hand type (earth / fire / air / water mix)
- Fingers, thumb, flexibility

Explain:
- why this structure formed
- how it affects behavior

---

SECTION 2 (MOUNTS):

Explain clearly:

- Venus → attachment / comfort  
- Saturn → discipline / delay  
- Mercury → business / communication  
- Sun → recognition  
- Moon → imagination  

For each:
- what is seen
- why it matters
- how it affects income or decisions

---

SECTION 3 (LINES):

Analyze:

- Life line → stability pattern  
- Head line → thinking pattern  
- Heart line → emotional pattern  
- Fate line → career flow  

Explain deeply:
- breaks / depth / direction
- why instability happens

---

SECTION 4 (SPECIAL SIGNS):

Check patterns:

- Cross → confusion  
- Triangle → skill  
- Square → protection  
- Star → sudden change  
- Breaks → instability  

Explain:
- what it indicates
- where it impacts life

If unclear, say:
"कुछ संकेत ऐसे दिखते हैं जो..."

---

SECTION 5 (LIFE PATTERN):

- How person operates in life
- Why growth is stuck or delayed
- Pattern of success / failure

---

SECTION 6 (REAL ROOT CAUSE — MOST IMPORTANT):

Speak directly:

"सीधे शब्दों में आपकी असली समस्या यह है कि..."

Explain deeply:

- why income unstable
- why confusion repeats
- why consistency breaks

Add 5–7 points minimum

Also include:

"If this continues for next 1–2 years..."

---

SECTION 7 (CLEAR DECISION SYSTEM):

Give:

- job option  
- freelance option  
- business option  

Explain:
- why suitable / why not

End with ONE clear final direction

---

SECTION 8 (YEAR-WISE TIMELINE):

Give structured timeline:

- 2026 → what will happen + why  
- 2027–2028 → transition phase  
- 2029–2030 → growth phase  

Include:
- reason
- impact
- caution

---

SECTION 9 (ADVANCED REMEDY SYSTEM):

Each remedy must follow:

1. Problem pattern  
2. Why remedy works  
3. Exact steps  
4. Duration (21 / 40 / 90 days)  
5. Expected result  

---

Include:

1. Practical System
- daily routine
- income discipline

2. Decision System
- thinking correction

3. Targeted Traditional Remedy

- Budh → clarity  
- Shani → stability  
- Chandra → emotional balance  

Use:
"परंपरागत अनुभव के अनुसार..."

---

IMPORTANT:

- No random mantra
- No generic advice
- Each remedy must connect with problem

---

WRITING STYLE:

- Bullet format
- Each point 3–5 lines
- Mix tone (not repetitive)

Use lines like:
"सीधे शब्दों में..."
"यह सिर्फ एक संकेत नहीं है..."
"आपके केस में खास बात यह है कि..."

---

DEPTH:

{depth_note}

- Section 6 and 9 must be longest
- Minimum 6–8 deep points

---

FINAL MESSAGE:

- Strong guidance
- No motivation talk
- Clear actionable direction

End with:

"अगले 90 दिन आपके लिए निर्णायक हैं..."

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
