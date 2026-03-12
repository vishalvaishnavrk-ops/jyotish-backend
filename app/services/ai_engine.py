from openai import OpenAI
import os
from app.database import get_db


def generate_ai_draft(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT name,questions,plan FROM clients WHERE id=%s
    """,(client_id,))

    data = c.fetchone()

    name,questions,plan = data

    # ---------- PLAN BASED LENGTH ----------

    if "₹51" in plan:
        word_limit = 400

    elif "₹151" in plan:
        word_limit = 700

    elif "₹251" in plan:
        word_limit = 1000

    else:
        word_limit = 1500


    prompt = f"""

आप एक अनुभवी हस्तरेखा विशेषज्ञ और वैदिक ज्योतिषाचार्य हैं।

क्लाइंट का नाम: {name}

क्लाइंट का प्रश्न:
{questions}

नीचे दिए गए sections के अनुसार एक विस्तृत हस्तरेखा विश्लेषण रिपोर्ट लिखें।

रिपोर्ट लगभग {word_limit} शब्दों की होनी चाहिए।

Sections structure:

Section 1 – हस्त संरचना विश्लेषण
हाथ की आकृति, अंगुलियों की बनावट, हथेली की ऊर्जा

Section 2 – पर्वत विश्लेषण
शुक्र, बृहस्पति, शनि, सूर्य, बुध पर्वत

Section 3 – मुख्य रेखाओं का विश्लेषण
जीवन रेखा
मस्तिष्क रेखा
हृदय रेखा
भाग्य रेखा
सूर्य रेखा

Section 4 – विशेष चिह्न
त्रिकोण, क्रॉस, तारा, वर्ग

Section 5 – कर्म और भाग्य
जीवन की दिशा और कर्मफल

Section 6 – प्रश्नों के उत्तर
क्लाइंट के प्रश्न का विश्लेषण

Section 7 – उपाय
सरल और व्यावहारिक उपाय

Section 8 – आगामी वर्षों का पूर्वानुमान

वर्ष 1
वर्ष 2
वर्ष 3
वर्ष 4

अंतिम संदेश:
आध्यात्मिक मार्गदर्शन

रिपोर्ट स्पष्ट हिंदी में होनी चाहिए।

"""


    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=[
            {"role": "system", "content": "आप एक अनुभवी हस्तरेखा विशेषज्ञ हैं"},
            {"role": "user", "content": prompt}
        ],

        temperature=0.7
    )


    draft = response.choices[0].message.content


    c.execute("""
    UPDATE clients
    SET ai_draft=%s,
    ai_generated=1
    WHERE id=%s
    """,(draft,client_id))


    conn.commit()
    conn.close()

    return draft
