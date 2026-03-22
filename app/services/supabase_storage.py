import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "palms"


def upload_palm_image(file_bytes, filename):

    path = f"client_images/{filename}"

    supabase.storage.from_(BUCKET_NAME).upload(
        path,
        file_bytes,
        {"content-type": "image/jpeg"}
    )

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"

    return public_url

def upload_pdf(file_bytes, file_name):
    path = file_name

    supabase.storage.from_("reports").upload(path, file_bytes, {"upsert": False})

    public_url = supabase.storage.from_("reports").get_public_url(path)

    return public_url
