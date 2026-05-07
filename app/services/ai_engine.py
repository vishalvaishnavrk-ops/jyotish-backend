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

CASE STUDY MODE:

Treat this like a real consultation case, not a generic personality reading.

Focus more on:
- recurring life patterns
- behavioral contradictions
- decision mistakes
- hidden causes behind financial or emotional instability

Avoid broad traits that can apply to everyone.

---

CONSULTATION SIMULATION:

Imagine you are speaking directly to a real person sitting in front of you.

Do not sound like a report generator or educational article.

While explaining patterns:
- speak like an experienced consultant
- connect observations with real-life struggles
- explain things in a practical and emotionally aware way

The tone should feel:
- personal
- observant
- direct
- grounded

Use occasional natural human lines such as:

"असल समस्या यहीं से शुरू होती है..."
"यहीं पर बार-बार गलती हो रही है..."
"आप मेहनती हैं, लेकिन direction टूट जाती है..."
"यह चीज़ बाहर से छोटी लगती है, लेकिन लंबे समय में बड़ा असर डालती है..."

---

Interpretation Note:

- Even if exact palm image details are not available, you can infer patterns based on common palm reading principles and the user's situation.
- Provide analysis in a confident and experience-based manner.
- Do not say that analysis is not possible.
- Avoid refusing the request.

If visual details are limited, use phrases like:
"सामान्य हस्तरेखा पैटर्न के आधार पर..."
"जो संकेत आमतौर पर ऐसे मामलों में देखे जाते हैं..."

Continue analysis instead of stopping.

---

Focus on uniqueness:

- Try to highlight what is specific or different in this case
- Avoid general traits that can apply to most people
- Emphasize patterns that feel personal and situation-based

---

THINKING DEPTH ENGINE:

Add deeper reasoning when explaining:

- Do not stop at surface meaning
- Briefly explain why this pattern forms in real life
- Link pattern with behavior and decisions

Example style:
"यह पैटर्न आमतौर पर तब बनता है जब व्यक्ति..."
"इसी कारण यह समस्या बार-बार देखने को मिलती है..."

---

INTERNAL REASONING FLOW:

Before writing the final explanation, internally think in this order:

1. What palm pattern is visible
2. What behavior this usually creates
3. What repeated life situation this behavior creates
4. What emotional or financial consequence follows
5. Then explain practical guidance

Do not jump directly from palm sign to advice.

---

For deeper insights:

Do not stop at describing the sign or line.

Always continue with:
- what behavior this creates
- how this affects real decisions
- what long-term consequence it causes

Example:
"This pattern usually creates hesitation in high-risk decisions, which slowly affects financial growth over time."

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
- Also explain how this mount influences daily decisions, habits, or income patterns.

---

SECTION 3 (LINES):

Analyze:

- Life line → stability pattern  
- Head line → thinking pattern  
- Heart line → emotional pattern  
- Fate line → career flow  

Explain with depth:

- Describe pattern (clear / broken / curved / faint)
- Then explain why such pattern forms
- Then connect with real-life behavior

Avoid single-line interpretation.

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

Start with:

"सीधे शब्दों में आपकी असली समस्या यह है कि..."

Then go deeper:

- Do not list problems — explain patterns

Each point should try to include:

• What exactly is happening  
• Why it is happening (pattern explanation)  
• How it is affecting real decisions  

(Explain naturally, avoid making it feel forced or repetitive)

You may also include:

- One “hidden pattern” that is not obvious  
- One “mistake pattern” that repeats  

End with:

"If this pattern continues for next 1–2 years, then..."

Focus less on motivation and more on behavioral diagnosis.

Explain:
- what exact mindset loop is repeating
- what hidden habit is damaging progress
- why the person keeps returning to the same problem

Also include 1–2 emotionally accurate observations where the reader feels deeply understood.

Example style:
"आप बाहर से मजबूत दिखने की कोशिश करते हैं, लेकिन अंदर लगातार pressure चलता रहता है..."

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

Try to avoid giving remedies as a plain list.

For each remedy, you can explain:

• Start with problem link  
• Explain why this remedy fits this case  
• Then suggest simple steps  
• Then mention expected improvement  

Example flow:

"आपके केस में निर्णय अस्थिरता दिखती है, इसलिए बुध से जुड़े उपाय clarity बढ़ाने में सहायक माने जाते हैं..."

Then:
- क्या करना है  
- कितने दिन  
- क्या फर्क आएगा  

Make each remedy feel personalized, not general.  

Keep remedies practical, simple, and based on commonly known traditional practices.
Avoid making extreme or guaranteed claims.

Remedies should feel like a correction system, not just spiritual suggestions.

Each remedy should connect:
Pattern → Correction → Expected shift

Focus more on behavior correction and disciplined routine than ritual alone.

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

Generate a structured and detailed report in Hindi, keeping the tone practical, balanced, and experience-based.
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
