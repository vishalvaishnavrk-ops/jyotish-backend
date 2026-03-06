from app.database import get_db


def generate_ai_draft(client_id):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT name, dob, tob, place, plan, questions FROM clients WHERE id=%s",
        (client_id,)
    )

    data = c.fetchone()

    if not data:
        conn.close()
        return

    name, dob, tob, place, plan, questions = data

    # PLAN DEPTH

    if "501" in plan:
        depth_text = "अत्यंत गहन कर्मिक एवं आध्यात्मिक विश्लेषण"
        year_limit = 7

    elif "251" in plan:
        depth_text = "गहन जीवन दिशा एवं भाग्य विश्लेषण"
        year_limit = 4

    elif "151" in plan:
        depth_text = "विस्तृत व्यावहारिक विश्लेषण"
        year_limit = 2

    else:
        depth_text = "संक्षिप्त एवं स्पष्ट मार्गदर्शन"
        year_limit = 1

    yearly_prediction = ""

    for i in range(1, year_limit + 1):

        yearly_prediction += f"""

वर्ष {i}:
इस वर्ष जीवन में क्रमिक प्रगति, अनुभव से सीख और आत्मविश्वास में वृद्धि के संकेत मिलते हैं।
परिस्थितियाँ संतुलित प्रयास की अपेक्षा करेंगी।

"""

    draft = f"""

Section 1 – हस्त संरचना विश्लेषण
हथेली की संरचना व्यक्ति के स्वभाव और मानसिक संतुलन को दर्शाती है।
इस योजना के अंतर्गत {depth_text} प्रस्तुत किया जा रहा है।

Section 2 – पर्वत विश्लेषण
शुक्र पर्वत ऊर्जा और आकर्षण का प्रतीक है।
बृहस्पति पर्वत नेतृत्व क्षमता का संकेत देता है।

Section 3 – मुख्य रेखाओं का विश्लेषण
जीवन रेखा जीवन शक्ति को दर्शाती है।
मस्तिष्क रेखा सोच और निर्णय शैली को बताती है।

Section 4 – विशेष चिह्न
त्रिकोण बुद्धिमत्ता का संकेत है।
क्रॉस संघर्ष के बाद उपलब्धि दर्शाता है।

Section 5 – कर्म और भाग्य
जीवन में उन्नति कर्म और प्रयास से जुड़ी होती है।

Section 6 – प्रश्नों के उत्तर
{questions}

Section 7 – उपाय
नियमित प्रार्थना और सकारात्मक सोच लाभकारी है।

Section 8 – आगामी वर्षों का पूर्वानुमान
{yearly_prediction}

अंतिम संदेश:
श्रद्धा, सद्कर्म और सकारात्मक दृष्टिकोण से जीवन की दिशा सुदृढ़ होती है।

– आचार्य विशाल वैष्णव
"""

    c.execute(
        "UPDATE clients SET ai_draft=%s, ai_generated=1 WHERE id=%s",
        (draft.strip(), client_id)
    )

    conn.commit()
    conn.close()
