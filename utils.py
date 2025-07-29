import random
import string
from database import save_file as db_save_file, get_file as db_get_file

def gen_code(length=8):
    """
    تولید یک کد تصادفی شامل حروف و اعداد (مثلاً برای لینک دعوت)
    """
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def save_file(file_id, code):
    """
    ذخیره فایل با استفاده از database.py
    """
    db_save_file(file_id, code)

def get_file(code):
    """
    دریافت فایل با استفاده از database.py
    """
    return db_get_file(code)


import requests
from config import BOT_TOKEN, PRIVATE_CHANNEL_ID
from database import save_file as db_save_file

URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def recover_file_from_channel(code):
    offset = 0
    while True:
        r = requests.get(f"{URL}/getUpdates", params={"offset": offset}).json()
        if not r.get("ok"):
            break
        updates = r.get("result", [])
        if not updates:
            break
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if msg and msg.get("chat", {}).get("id") == PRIVATE_CHANNEL_ID:
                caption = msg.get("caption", "")
                if caption and f"link:{code}" in caption:
                    file_id = None
                    if "document" in msg:
                        file_id = msg["document"]["file_id"]
                    elif "video" in msg:
                        file_id = msg["video"]["file_id"]
                    elif "photo" in msg:
                        file_id = msg["photo"][-1]["file_id"]
                    if file_id:
                        db_save_file(file_id, code)
                        return file_id
        # اگر چیزی پیدا نکرد رفت حلقه بعد
    return None
