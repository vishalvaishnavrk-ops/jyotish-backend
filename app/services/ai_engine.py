from openai import OpenAI
import os
from app.database import get_db, release_db

USE_REAL_AI = True

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ai_call(prompt, max_tokens=1200, temperature=0.7):

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
            }
        ],
        temperature=temperature,
        max_output_tokens=max_tokens
    )

    return response.output_text.strip()


def generate_ai_draft(client_id):

    # =========================================================
    # FETCH CLIENT
    # =========================================================

    conn = get_db()

    try:
        c = conn.cursor()

        c.execute("""
        SELECT name, questions, plan, dob, tob, place, images
        FROM clients
        WHERE id=%s
        """, (client_id,))

        data = c.fetchone()

        if not data:
            return "No client found"

        c.execute("""
        SELECT ai_generated
        FROM clients
        WHERE id=%s
        """, (client_id,))

        if c.fetchone()[0] == 1:
            return "AI already generated"

        name, questions, plan, dob, tob, place, images = data

    finally:
        release_db(conn)

    # =========================================================
    # IMAGE LOGIC
    # =========================================================

    image_urls = []

    if images:
        image_urls = [
            img.strip()
            for img in images.split(",")
            if img.strip()
        ]

    # =========================================================
    # MODE
    # =========================================================

    mode = "HYBRID" if dob and tob and place else "PALM_ONLY"

    # =========================================================
    # PLAN CONFIG
    # =========================================================

    if "₹51" in plan:

        observation_tokens = 500
        diagnosis_tokens = 700
        final_tokens = 1200

        years_text = "अगले 1–2 वर्ष"

        depth_note = """
- Short and direct report
- Focus only on major observations
- Simple practical guidance
"""

    elif "₹151" in plan:

        observation_tokens = 700
        diagnosis_tokens = 900
        final_tokens = 1800

        years_text = "अगले 1–3 वर्ष"

        depth_note = """
- Add reasoning with observations
- Slightly deeper practical analysis
- More personal consultation tone
"""

    elif "₹251" in plan:

        observation_tokens = 900
        diagnosis_tokens = 1200
        final_tokens = 2600

        years_text = "अगले 1–4 वर्ष"

        depth_note = """
- Deep analysis of lines and mounts
- Strong life-pattern diagnosis
- Personalized remedies and timeline
"""

    else:  # ₹501

        observation_tokens = 1200
        diagnosis_tokens = 1600
        final_tokens = 4200

        years_text = "2026 से अगले 5 वर्ष"

        depth_note = """
- Deep expert-level consultation feel
- Human-like explanation and emotional realism
- Strong behavioral diagnosis
- Detailed practical + traditional remedies
- Year-wise timeline with reasoning
- Report should feel premium and deeply personal
- Avoid generic advice or repeated lines
"""

    # =========================================================
    # STEP 1 — OBSERVATION ENGINE
    # =========================================================

    observation_prompt = f"""
You are an expert palm observation analyst.

Your ONLY task is to extract palm observations.

Focus on:

- hand structure
- fingers
- thumb
- flexibility
- major lines
- mounts
- special signs

If image details are limited:
use common palm-reading interpretation patterns naturally.

IMPORTANT:

- Do NOT give remedies
- Do NOT give future prediction
- Do NOT give motivational advice
- Do NOT generate final report

Write only structured observations.

MODE:
{mode}

CLIENT:
Name: {name}
Question: {questions}
"""

    # =========================================================
    # STEP 2 — DIAGNOSIS ENGINE
    # =========================================================

    diagnosis_prompt = f"""
You are an expert behavioral pattern analyst.

Based on these palm observations:

{OBSERVATIONS}

Analyze deeply:

- repeated life patterns
- emotional tendencies
- hidden self-sabotage
- decision-making flaws
- financial instability patterns
- career behavior patterns
- emotional pressure patterns

IMPORTANT:

Focus on:
Pattern → Behavior → Consequence

Avoid generic personality traits.

Do not sound like a textbook.

Write like an experienced consultant analyzing a real person.

Use practical and emotionally intelligent reasoning.
"""

    # =========================================================
    # STEP 3 — FINAL CONSULTATION ENGINE
    # =========================================================

    consultation_prompt = f"""
You are a highly experienced senior palm reading consultant.

You are directly consulting a real client.

Use these palm observations:

{{OBSERVATIONS}}

Use these behavioral diagnosis insights:

{{DIAGNOSIS}}

Generate a premium Hindi consultation report.

IMPORTANT:

The report should feel:
- deeply personal
- emotionally accurate
- practical
- human
- experience-based

Do NOT sound like:
- textbook
- astrology article
- AI template
- generic self-help content

Write like a real senior consultant explaining:

- recurring life patterns
- emotional loops
- hidden mistakes
- financial struggles
- behavioral contradictions
- real root causes

The reader should feel:
"यह रिपोर्ट मेरे लिए ही बनाई गई है"

Use natural conversational Hindi.

---

MODE:

- If birth details are available:
  use astrology only as supporting insight

- Palm reading should remain primary

---

OUTPUT STRUCTURE:

Section 1 – हस्त संरचना  
Section 2 – पर्वत विश्लेषण  
Section 3 – मुख्य रेखाएं  
Section 4 – विशेष संकेत  
Section 5 – जीवन और करियर पैटर्न  
Section 6 – समस्या का वास्तविक कारण  
Section 7 – सही दिशा और निर्णय  
Section 8 – समय संकेत ({years_text})  
Section 9 – उपाय और सुधार प्रणाली  
Section 10 – अंतिम मार्गदर्शन  

---

SECTION 6 SHOULD BE MOST POWERFUL.

Focus on:
- repeated mistakes
- mindset loops
- hidden emotional pressure
- why the same problems repeat

Use human-style lines like:

"असल समस्या यहीं से शुरू होती है..."
"आप मेहनती हैं, लेकिन..."
"यहीं पर बार-बार गलती हो रही है..."
"आप बाहर से मजबूत दिखते हैं, लेकिन अंदर लगातार pressure चलता रहता है..."

---

SECTION 9:

Remedies should feel:
- practical
- connected
- personalized

Avoid random remedies.

Each remedy should connect:

Problem → Correction → Expected Change

Include:
- practical discipline
- behavior correction
- traditional remedies if relevant

Use safe wording like:
"परंपरागत अनुभव के अनुसार..."

---

WRITING STYLE:

- conversational Hindi
- readable formatting
- every point separate line
- avoid repetition
- avoid generic statements

---

DEPTH:

{depth_note}

---

FINAL TONE:

The report should feel like:
a real senior consultant personally studied this case.
"""

    # =========================================================
    # AI EXECUTION
    # =========================================================

    if not USE_REAL_AI:
        final_report = "Dummy report"

    else:

        try:

            # ---------------------------------------------
            # STEP 1
            # ---------------------------------------------

            observations = ai_call(
                observation_prompt,
                max_tokens=observation_tokens,
                temperature=0.5
            )

            # ---------------------------------------------
            # STEP 2
            # ---------------------------------------------

            diagnosis = ai_call(
                diagnosis_prompt.replace(
                    {OBSERVATIONS},
                    observations
                ),
                max_tokens=diagnosis_tokens,
                temperature=0.7
            )

            # ---------------------------------------------
            # STEP 3
            # ---------------------------------------------

            final_prompt = consultation_prompt \
                .replace("{OBSERVATIONS}", observations) \
                .replace("{DIAGNOSIS}", diagnosis)

            final_report = ai_call(
                final_prompt,
                max_tokens=final_tokens,
                temperature=0.85
            )

            # ---------------------------------------------
            # FORMAT FIX
            # ---------------------------------------------

            final_report = final_report.replace("• ", "\n• ")

        except Exception as e:

            final_report = f"AI Error: {str(e)}"

    # =========================================================
    # SAVE
    # =========================================================

    conn = get_db()

    try:

        c = conn.cursor()

        c.execute("""
        UPDATE clients
        SET ai_draft=%s,
            ai_generated=1
        WHERE id=%s
        """, (final_report, client_id))

        conn.commit()

    finally:

        release_db(conn)

    return final_report
