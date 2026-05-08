from openai import OpenAI
import os
from app.database import get_db, release_db

USE_REAL_AI = True

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================================================
# UNIVERSAL AI CALL
# =========================================================

def ai_call(prompt, max_tokens=1200, temperature=0.7, images=None):

    content = [
        {
            "type": "input_text",
            "text": prompt
        }
    ]

    # ============================================
    # ADD IMAGES IF AVAILABLE
    # ============================================

    if images:

        for img in images:

            content.append({
                "type": "input_image",
                "image_url": img
            })

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=temperature,
        max_output_tokens=max_tokens
    )

    return response.output_text.strip()


# =========================================================
# MAIN ENGINE
# =========================================================

def generate_ai_draft(client_id):

    # =====================================================
    # FETCH CLIENT
    # =====================================================

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

    # =====================================================
    # IMAGE LOGIC
    # =====================================================

    image_urls = []

    if images:
        image_urls = [
            img.strip()
            for img in images.split(",")
            if img.strip()
        ]

    # =====================================================
    # MODE
    # =====================================================

    mode = "HYBRID" if dob and tob and place else "PALM_ONLY"

    # =====================================================
    # PLAN CONFIG
    # =====================================================

    if "₹51" in plan:

        observation_tokens = 500
        diagnosis_tokens = 700
        astrology_tokens = 500
        remedy_tokens = 700
        timeline_tokens = 600

    elif "₹151" in plan:

        observation_tokens = 800
        diagnosis_tokens = 1000
        astrology_tokens = 700
        remedy_tokens = 1000
        timeline_tokens = 900

    elif "₹251" in plan:

        observation_tokens = 1200
        diagnosis_tokens = 1400
        astrology_tokens = 900
        remedy_tokens = 1500
        timeline_tokens = 1200

    else:  # ₹501

        observation_tokens = 1800
        diagnosis_tokens = 2200
        astrology_tokens = 1400
        remedy_tokens = 2200
        timeline_tokens = 1600

    # =====================================================
    # AI EXECUTION
    # =====================================================

    if not USE_REAL_AI:

        final_report = "Dummy report"

    else:

        try:

            # =================================================
            # STEP 1 — PALM OBSERVATION ENGINE
            # =================================================

            observation_prompt = f"""
You are a highly experienced palm observation expert.

Your task is to deeply observe palm structure and extract practical life-related patterns.

IMPORTANT:

Do NOT write generic palmistry theory.

Act like you are observing a real person's hand and extracting meaningful patterns.

Focus deeply on:

1. Hand Structure
- earth / fire / air / water tendencies
- palm texture
- flexibility
- hardness / softness

2. Fingers & Thumb
- finger balance
- thumb strength
- flexibility
- control tendency
- stubbornness vs adaptability

3. Major Lines
- life line
- head line
- heart line
- fate line
- sun line
- mercury line

Observe:
- breaks
- chains
- forks
- islands
- depth
- curve
- direction
- overlaps

4. Mount Analysis
- Jupiter
- Saturn
- Sun
- Mercury
- Venus
- Moon
- Mars

Explain:
- emotional impact
- decision impact
- financial behavior impact
- career impact

Do not describe palm features separately like a textbook.

Always connect observations with:
- real-life behavior
- emotional reactions
- financial tendencies
- relationship patterns
- career struggles

Every observation must feel connected to life experience.

Do not stop at visual observation.

For every major line or sign:
explain the hidden behavioral consequence behind it.

Connect:
- palm pattern
- emotional behavior
- decision style
- life consequence

This should feel like:
real hidden pattern interpretation,
not visual description.

Do not explain palm lines like fixed palmistry meanings.

Instead explain:
how that palm pattern practically manifests in real life.

Focus on:
- repeated behavior cycles
- emotional triggers
- career mistakes
- money instability loops
- relationship reactions

Interpret like:
a senior palm expert decoding hidden life mechanisms.

5. Special Signs
Check deeply for:
- cross
- star
- triangle
- square
- grill
- fish
- trident
- cuts
- chained patterns

IMPORTANT:

Do NOT use:
- maybe
- if
- possible

Write confident observations directly.

Good style:
"Fate line shows repeated breaks near the center, indicating instability in long-term direction and repeated restart patterns."

Avoid:
generic textbook explanations.

Do NOT give:
- remedies
- predictions
- motivational advice
- final consultation

CLIENT:
{name}

QUESTION:
{questions}

MODE:
{mode}

If MODE is HYBRID:
subtly align observations with possible astrology-supported behavioral tendencies.

IMPORTANT LANGUAGE RULE:

Write entirely in natural Hindi.

Tone should feel like:
an experienced Indian palm reader and spiritual consultant personally explaining the person's life patterns.

Avoid:
- English analytical tone
- textbook explanations
- robotic wording
- corporate language

Writing style should feel:
- human
- emotionally observant
- practical
- spiritually grounded
- conversational but expert-level

Use natural human consultation expressions occasionally.

Examples:
- "आपके हाथ में जो संकेत दिखते हैं..."
- "आपके केस में खास बात यह है कि..."
- "यह पैटर्न जीवन में बार-बार प्रभाव डालता है..."

Do NOT write like:
an AI analyst or psychology article.
"""

            observations = ai_call(
                observation_prompt,
                max_tokens=observation_tokens,
                temperature=0.5,
                images=image_urls
            )

            # =================================================
            # STEP 2 — BEHAVIORAL DIAGNOSIS ENGINE
            # =================================================

            diagnosis_prompt = f"""
You are an expert behavioral diagnosis consultant.

Based on these palm observations:

{observations}

Identify:

- repeated life mistakes
- emotional contradictions
- self-sabotage patterns
- stress-response patterns
- financial instability patterns
- hidden behavioral loops
- why stability repeatedly breaks

IMPORTANT:

Avoid generic personality descriptions.

Do NOT say:
- hardworking
- emotional
- good person

Instead explain:
- what exact pattern repeats
- why it repeats
- how it damages progress

Write like a senior consultant privately analyzing a real person.

Avoid repeating the same emotional phrases multiple times.

Use varied natural consultation language.

Do not repeatedly use:
- "असल समस्या यहीं से शुरू होती है"
- "बार-बार यही पैटर्न बनता है"
- "आपके हाथ में जो संकेत दिखते हैं"

Use emotionally varied expressions naturally.

Do not force emotional phrases in every paragraph.

Use emotional observations naturally and only where meaningful.

For every important pattern:

Go 3 layers deep:

1. visible behavior
2. hidden emotional reason
3. practical life consequence

Do not stop at surface-level interpretation.

Every major insight should unfold gradually.

Pattern flow should feel like:

hidden cause
→ emotional reaction
→ repeated behavior
→ life consequence
→ future risk

This unfolding style is extremely important.

Do not give remedies.

IMPORTANT LANGUAGE RULE:

Write entirely in natural Hindi.

Tone should feel like:
an experienced Indian palm reader and spiritual consultant personally explaining the person's life patterns.

Avoid:
- English analytical tone
- textbook explanations
- robotic wording
- corporate language

Writing style should feel:
- human
- emotionally observant
- practical
- spiritually grounded
- conversational but expert-level

Use phrases naturally like:

- "आपके हाथ में जो संकेत दिखते हैं..."
- "असल समस्या यहीं से शुरू होती है..."
- "बार-बार यही पैटर्न बनता है कि..."
- "आप बाहर से मजबूत दिखते हैं लेकिन..."
- "आपके केस में खास बात यह है कि..."
- "यहीं पर जीवन बार-बार अटकता है..."

Do NOT write like:
an AI analyst or psychology article.
"""

            diagnosis = ai_call(
                diagnosis_prompt,
                max_tokens=diagnosis_tokens,
                temperature=0.7
            )

            # =================================================
            # STEP 3 — ASTROLOGY SUPPORT ENGINE
            # =================================================

            astrology_data = ""

            if mode == "HYBRID":

                astrology_prompt = f"""
You are a Vedic astrology insight analyst.

Client Details:

DOB: {dob}
TOB: {tob}
POB: {place}

Analyze only:

- career tendencies
- financial pressure patterns
- emotional instability tendencies
- mental patterns
- timing tendencies

IMPORTANT:

Do NOT generate full kundli explanation.

Do NOT use difficult astrology jargon.

Write practical insights only.

Palm reading remains primary.
Astrology should only support the diagnosis.

If birth details are available:

Use:
- current planetary periods
- major grah influence
- current transit tendencies
- emotional pressure combinations
- financial instability combinations
- upcoming growth/support periods

Do NOT generate generic astrology descriptions.

Astrology should:
strengthen the palm interpretation,
especially:
- timeline
- emotional patterns
- career instability
- money cycles
- remedies

Write in natural human Hindi consultation style.
Avoid robotic astrology explanation.

"""

                astrology_data = ai_call(
                    astrology_prompt,
                    max_tokens=astrology_tokens,
                    temperature=0.6
                )

            # =================================================
            # STEP 4 — REMEDY ENGINE
            # =================================================

            remedy_prompt = f"""
You are an experienced Indian spiritual consultant.

Palm Diagnosis:
{diagnosis}

Astrology Support:
{astrology_data}

Generate highly personalized remedies.

IMPORTANT:

Avoid generic advice.

Every remedy must connect with:
- emotional imbalance
- behavioral instability
- financial pressure
- planetary weakness tendencies

Allowed:
- mantra
- daan
- discipline
- vrat
- satvik routines
- speech discipline
- focus correction
- behavioral correction

Avoid:
- magical promises
- fear-based advice
- unrealistic tantra claims

Write remedies like a real Indian spiritual consultant personally guiding the client.

Do not use structured labels like:
- remedy
- duration
- expected improvement

Instead naturally explain:
- why this issue repeats
- what correction is needed
- which traditional practices may help
- how discipline and spiritual correction together improve the pattern

Remedies should feel:
deeply personal
emotionally believable
practical
traditional
human

Avoid repeating the same emotional phrases multiple times.

Use varied natural consultation language.

Do not repeatedly use:
- "असल समस्या यहीं से शुरू होती है"
- "बार-बार यही पैटर्न बनता है"
- "आपके हाथ में जो संकेत दिखते हैं"

Use emotionally varied expressions naturally.

Remedies must feel specifically connected to:
- palm signs
- behavioral instability
- emotional imbalance
- financial patterns
- possible planetary weaknesses

Do not give general spiritual advice.

Every remedy should feel:
person-specific
problem-specific
behavior-specific

Advanced remedies should combine:
- palm indication
- planetary weakness
- behavioral correction
- spiritual balancing
- discipline correction

Include occasionally:
- mantra
- daan
- vrat
- energy correction
- behavioral discipline
- timing correction
- decision restrictions
- spiritual routines

Remedies should feel rare,
deep,
specific,
and surprisingly accurate.

Write remedies in deeply personal Hindi consultation tone.
Avoid robotic spiritual explanation.
"""

            remedies = ai_call(
                remedy_prompt,
                max_tokens=remedy_tokens,
                temperature=0.7
            )

            # =================================================
            # STEP 5 — TIMELINE ENGINE
            # =================================================

            timeline_prompt = f"""
You are a life-pattern timeline analyst.

Palm Diagnosis:
{diagnosis}

Astrology Support:
{astrology_data}

Generate realistic year-wise insights.

Focus on:
- career direction
- financial stability
- emotional growth
- pressure periods
- transition phases

Use realistic language.

Structure:

2026:
2027–2028:
2029–2030:

Avoid generic positivity.

Write in realistic human Hindi consultation style.
Do not sound like prediction article.
"""

            timeline = ai_call(
                timeline_prompt,
                max_tokens=timeline_tokens,
                temperature=0.7
            )

            # =================================================
            # STEP 6 — CLOSING SUMMARY ENGINE
            # =================================================

            closing_prompt = f"""
You are a senior spiritual and behavioral consultant.

Based on:

Palm Observations:
{observations}

Diagnosis:
{diagnosis}

Astrology Support:
{astrology_data}

Generate a powerful final guidance summary.

This should feel like:
the final words of a deeply experienced spiritual consultant
after studying the person's hidden struggles carefully.

The tone should feel:
calm
wise
observant
emotionally piercing
grounded

Not motivational.
Not generic.
Not summary-like.

IMPORTANT:

This should feel like:
a real consultant giving final personal advice after deeply studying the case.

Focus on:
- biggest hidden challenge
- biggest strength
- what must change
- what should be avoided
- what can improve life direction

Avoid:
- generic motivation
- repeated lines
- fake positivity

Tone should feel:
calm
deep
human
emotionally observant

Length:
5–10 meaningful lines.

Avoid repeating the same emotional phrases multiple times.

Use varied natural consultation language.

Do not repeatedly use:
- "असल समस्या यहीं से शुरू होती है"
- "बार-बार यही पैटर्न बनता है"
- "आपके हाथ में जो संकेत दिखते हैं"

Use emotionally varied expressions naturally.

Write like a real senior Indian consultant giving final personal guidance.
"""

            closing_summary = ai_call(
                closing_prompt,
                max_tokens=900,
                temperature=0.75
            )
            
            # =================================================
            # STEP 6 — FINAL REPORT COMPOSER
            # =================================================

            final_report = f"""
Section 1 – हस्त संरचना और मुख्य संकेत

{observations}

--------------------------------------------------

Section 2 – जीवन और व्यवहार पैटर्न

{diagnosis}
"""

            if astrology_data:

                final_report += f"""

--------------------------------------------------

Section 3 – ज्योतिषीय समर्थन संकेत

{astrology_data}
"""

            final_report += f"""

--------------------------------------------------

Section 4 – समय संकेत

{timeline}

--------------------------------------------------

Section 5 – उपाय और सुधार प्रणाली

{remedies}

--------------------------------------------------

Section 6 – अंतिम मार्गदर्शन

{closing_summary}
"""
            
            # =================================================
            # FORMAT FIX
            # =================================================

            final_report = final_report.replace("• ", "\n• ")

        except Exception as e:

            final_report = f"AI Error: {str(e)}"

    # =====================================================
    # SAVE
    # =====================================================

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
