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
- हर section में लगभग 5–7 meaningful bullet points हों (repetition से बचें)

- हर point में natural flow में ये चीजें शामिल हों:
  - Observation (क्या pattern दिखता है)
  - Reason (यह pattern आमतौर पर क्यों बनता है)
  - Life Impact (इसका वास्तविक जीवन पर क्या असर पड़ता है)

- हर point को 3–5 lines में explain करें, लेकिन unnecessary लंबा न करें

- Section 6 (problem diagnosis) में थोड़ी ज्यादा गहराई रखें:
  - कम से कम 5–7 strong points
  - हर point root cause explain करे
  - surface level explanation से बचें

- Section 9 (remedy) practical और result-oriented होना चाहिए:
  - हर remedy में WHY + HOW + DURATION (21 / 40 / 90 days) शामिल हो
  - remedy को problem से logically जोड़ें

- Section 8 (timeline) clear और structured हो:
  - 2026 → क्या और क्यों
  - 2027–2028 → transition
  - 2029–2030 → growth

- Report readable और structured रहे:
  - हर point अलग line में
  - sections clear हों

- Language simple लेकिन expert-level हो
- Report ऐसा लगे कि किसी experienced consultant ने समझाकर लिखा है
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

Your goal is to understand patterns, explain root causes, and give clear practical direction.

---

CORE THINKING APPROACH:

For most points, try to include:

1. What pattern is observed (line / mount / structure / sign)
2. Why this pattern generally forms
3. How it affects real-life decisions
4. What problem it creates over time

Keep reasoning natural and human-like.

---

MODE:

- If birth details (DOB, TOB, Place) are available:
  Use palm reading as primary and support it with basic astrology insight.

- If only palm data is available:
  Base the full analysis on palm patterns.

Do not overuse astrology — use it only as support.

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
Section 6 – समस्या का वास्तविक कारण (focus more detail here)  
Section 7 – सही दिशा और निर्णय  
Section 8 – समय संकेत ({years_text})  
Section 9 – उपाय (focus more detail here)  
Section 10 – अंतिम मार्गदर्शन  

---

SECTION 1 (HAND STRUCTURE):

- Hand type (earth / fire / air / water mix)
- Fingers, thumb, flexibility

Explain:
- what it suggests
- how it influences behavior

---

SECTION 2 (MOUNTS):

Explain clearly:

- Venus → comfort / attachment  
- Saturn → discipline / delay  
- Mercury → business / communication  
- Sun → recognition  
- Moon → imagination  

For each:
- what is seen
- why it matters
- how it affects decisions or income

---

SECTION 3 (LINES):

Analyze:

- Life line → stability pattern  
- Head line → thinking pattern  
- Heart line → emotional pattern  
- Fate line → career flow  

Explain:
- depth / breaks / direction
- how instability or consistency develops

---

SECTION 4 (SPECIAL SIGNS):

Check patterns like:

- Cross → confusion  
- Triangle → skill  
- Square → protection  
- Star → sudden change  
- Breaks → instability  

Explain:
- possible meaning
- where it may affect life

If unclear, you may say:
"कुछ संकेत ऐसे दिखते हैं जो..."

---

SECTION 5 (LIFE PATTERN):

- How the person generally operates in life
- Why growth may be slow or delayed
- Pattern of success vs struggle

---

SECTION 6 (REAL ROOT CAUSE):

Speak clearly and directly:

"सीधे शब्दों में आपकी असली समस्या यह है कि..."

Explain:

- why income instability may happen
- why confusion repeats
- why consistency breaks

Try to give 5–7 meaningful points.

You may also include:
"If this pattern continues for the next 1–2 years..."

---

SECTION 7 (DECISION SYSTEM):

Give:

- job option  
- freelance option  
- business option  

Explain:
- when each works
- when it may not

End with one clear practical direction.

---

SECTION 8 (YEAR-WISE TIMELINE):

Provide structured flow:

- 2026 → what may happen + why  
- 2027–2028 → transition phase  
- 2029–2030 → growth phase  

Include:
- reason
- possible impact
- caution

Use probability-based language (not certainty).

---

SECTION 9 (REMEDY SYSTEM):

For each remedy, try to include:

- Problem pattern  
- Why this remedy may help  
- How to do it  
- Suggested duration (21 / 40 / 90 days)  
- Expected improvement  

---

Include mix of:

1. Practical system
- daily routine
- income discipline

2. Decision improvement
- thinking pattern correction

3. Traditional remedies (optional but relevant)

- Budh → clarity  
- Shani → stability  
- Chandra → emotional balance  

Use safe phrasing:
"परंपरागत अनुभव के अनुसार..."

Avoid random or unrelated remedies.

---

WRITING STYLE:

- Bullet format preferred
- Each point explained in 3–5 lines
- Natural conversational tone
- Avoid repeating same sentence structure

You may use lines like:
"सीधे शब्दों में..."
"आपके केस में खास बात यह है कि..."
"यह पैटर्न आमतौर पर तब बनता है जब..."

---

DEPTH:

{depth_note}

- Section 6 and 9 should be more detailed
- Focus on meaningful depth instead of unnecessary repetition

---

FINAL MESSAGE:

- Give clear guidance
- Keep it practical and grounded

You may end with a strong actionable line such as:
"अगले 90 दिन आपके लिए निर्णायक हो सकते हैं..."

---

Generate a complete and structured report in Hindi.
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
