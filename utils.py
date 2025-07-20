
import random
import string
from database import save_files as db_save_files, get_files as db_get_files

def gen_code(length=8):
    """
    تولید یک کد تصادفی شامل حروف و اعداد (مثلاً برای لینک دعوت)
    """
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def save_files(file_list, code):
    """
    ذخیره چند فایل با استفاده از database.py
    """
    db_save_files(file_list, code)

def get_files(code):
    """
    دریافت همه فایل‌ها با استفاده از database.py
    """
    return db_get_files(code)
