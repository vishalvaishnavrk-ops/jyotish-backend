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

Write like a real experienced consultant, not like a textbook.

- Avoid repeating "यह दर्शाता है" in every point
- Use natural explanation style
- Mix observation with reasoning naturally

Example style:
"यह संकेत इस बात की ओर इशारा करता है कि..."
"यहां जो पैटर्न दिखता है, वह आमतौर पर तब बनता है जब..."
---

PERSONALIZATION + HUMAN TOUCH:

- Report must feel personal
- Use relatable lines like:
  "आपने कई बार महसूस किया होगा कि..."
  "जीवन में बार-बार यह स्थिति बनती है कि..."

- Occasionally address directly:
  "{name}, आपकी स्थिति में..."

Write like you are directly advising the person sitting in front of you.

Use lines like:
"सीधे शब्दों में कहें तो..."
"अगर आपको एक स्पष्ट दिशा चुननी हो तो..."
"आपके केस में सबसे बड़ी गलती यह हो रही है कि..."

Make it feel like real conversation, not report writing.
---

In important sections (especially Section 6 and 11), speak directly like a mentor.

Example:
"आपके केस में सबसे बड़ी समस्या यह दिखती है कि..."
"अगर आप यही pattern continue रखते हैं तो..."

Make it feel like direct guidance, not a report.

Section 11 – अंतिम संदेश:

Make final message impactful:

- Problem acknowledge करो
- Confidence दो
- Clear direction reinforce करो

Avoid generic positivity.
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

SECTION 6 (ADVANCED DIAGNOSIS MODE - MOST IMPORTANT):

- Surface level explanation नहीं, root pattern identify करें
- Palm संकेत से समझाएं कि समस्या बार-बार क्यों बन रही है

Think deeply:
- क्यों income stable नहीं हो रही?
- क्यों सही काम decide नहीं हो पा रहा?

Then give:

- Clear direction (job vs freelance vs business)
- 2–3 practical options
- हर option का reason explain करें (क्यों suitable है)

This section must feel like real paid consultation, not general advice.

End Section 6 with a strong conclusion:

- Clear final recommendation
- One path choose करके बताओ

Example:
"आपके केस में सबसे practical और stable रास्ता यह रहेगा कि..."
---

Add deeper reasoning:

- If financial instability is seen, link it with possible weak Mercury (Budh) or Saturn (Shani) tendencies
- If confusion is seen, link it with mental pattern (Budh/Chandra influence)
- If inconsistency is seen, link it with discipline pattern (Shani)

Explain in simple language (no heavy astrology terms)

Example:
"यह पैटर्न अक्सर तब बनता है जब व्यक्ति निर्णय लेने में स्थिर नहीं रहता..."
 ---   
    
SECTION 9 (TIMELINE):

- Time-based संकेत दें:
  "2026 में..."
  "2027–2029 के बीच..."
  "इस समय बदलाव के संकेत दिखते हैं..."

- Keep realistic and probability-based
---

SECTION 10 (ADVANCED PERSONALIZED REMEDIES):

Remedies must feel specific to the person, not general.

For each remedy:
- First explain WHY this remedy is given
- Then give remedy

Include:

1. Practical Fix (MOST IMPORTANT)
   - work pattern change
   - income strategy

2. Mental Correction
   - decision making habit

3. Targeted Traditional Remedy (IMPORTANT)

   - Link with pattern:
     if confusion → Budh support
     if instability → Shani discipline
     if emotional disturbance → Chandra balance

Use safe phrasing:
"परंपरागत अनुभव के आधार पर..."

Example style:
"आपके केस में निर्णय अस्थिरता दिखती है, इसलिए बुध से जुड़े उपाय सहायक हो सकते हैं..."

Give:
- simple mantra (short)
- day-based routine (e.g., बुधवार, शनिवार)
- small actionable step

Avoid random remedies.
---
         
WRITING STYLE:

- Bullet format only (•)
- Each bullet new line
- Each point minimum 3 lines
- No paragraphs
- No repetition
---

Tone Enhancement:

- हर point में थोड़ा variation रखें
- हर line same pattern में शुरू न करें

Use mix style:
- कभी सीधे observation से शुरू करें
- कभी explanation से
- कभी direct guidance से

Make it feel like a real human explaining, not listing.
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

Avoid common advice like:
"खर्च कम करें"
"मेहनत करें"

Instead explain:
WHY problem is happening + WHAT exactly needs to change

Every suggestion must feel specific to the person, not general.
---

Avoid repeating same explanation pattern in every section.

- Personality = descriptive
- Career = analytical
- Question = diagnostic
- Remedies = actionable

Each section must feel unique and different.
---

FINAL INSTRUCTION:

- Do not refuse analysis
- Do not give template answers
- Always provide complete report
---

Ensure the response is complete and does not cut off mid-section.

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
