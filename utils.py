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
