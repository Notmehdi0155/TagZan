import random
import string
from database import save_collection, get_collection

def gen_code(length=8):
    """
    تولید یک کد تصادفی شامل حروف و اعداد (مثلاً برای لینک دعوت)
    """
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def save_files(file_ids, code, cover=None, caption=None):
    """
    ذخیره مجموعه فایل‌ها با کاور و کپشن
    """
    save_collection(code, file_ids, cover, caption)

def get_files(code):
    """
    دریافت مجموعه فایل‌ها با استفاده از کد یکتا
    """
    return get_collection(code)  # returns: (files, cover, caption)
