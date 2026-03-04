import time
from datetime import datetime
from zoneinfo import ZoneInfo

def generate_client_code():
    year = datetime.now(ZoneInfo("Asia/Kolkata")).year
    short_unique = int(time.time()) % 100000
    return f"AVV-{year}-{short_unique}"
