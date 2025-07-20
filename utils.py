import random
import string
from database import save_file, get_file, save_collection, get_collection

def gen_code(length=8):
    """
    تولید یک کد تصادفی شامل حروف و اعداد (مثلاً برای لینک دعوت)
    """
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def save_files(file_ids, code, cover_id=None, caption=None):
    """
    ذخیره چند فایل با کاور و کپشن اختیاری
    """
    save_collection(code, file_ids, cover_id, caption)

def get_files(code):
    """
    دریافت اطلاعات یک مجموعه فایل
    """
    return get_collection(code)