# handlers.py

from config import ADMIN_ID, BOT_USERNAME
from utils import send_message, is_subscribed
from database import *

def handle_message(msg):
    text = msg.get('text', '')
    user_id = msg['from']['id']
    fullname = msg['from'].get('first_name', '')
    username = msg['from'].get('username') or 'NoUsername'
    chat_id = msg['chat']['id']

    # --- ثبت کاربر اگر جدید باشد ---
    if text.startswith('/start'):
        args = text.split()
        inviter = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None
        add_user(user_id, username, fullname, inviter)

        if is_subscribed(user_id):
            update_joined(user_id)
            send_main_panel(chat_id)
        else:
            send_force_join(chat_id)
        return

    # --- پنل ادمین ---
    if user_id == ADMIN_ID:
        if text == '/panel':
            send_admin_panel(chat_id)
        elif text.startswith('🟨'):
            global leaderboard_text
            leaderboard_text = text
            send_message(chat_id, '✅ لیست نفرات برتر به‌روزرسانی شد.')
        elif text == 'شروع ربات':
            send_message(chat_id, '✅ مسابقه آغاز شد.')
        elif text == '3 نفر برتر واقعی':
            result = ''
            top = get_top_inviters(3)
            for uid, count in top:
                u = get_user(uid)
                if u:
                    result += f'🏆 {u[2]} (@{u[1]}) → {count} دعوت\n'
            send_message(chat_id, result or 'هیچ دعوتی نشده.')
        return

    # --- دکمه‌ها ---
    if text == 'دعوت دوستان💰':
        joined, left, score = get_stats(user_id)
        link = f'https://t.me/{BOT_USERNAME}?start={user_id}'
        send_message(chat_id,
            f'🔰 تعداد کسانی که دعوت کردید = {joined}\n'
            f'🔰 کسانی که لفت دادن = {left}\n'
            f'🔰 مجموع امتیاز = {score}\n\n'
            f'کد دعوت شما 👇\n{link}',
            reply_markup=btn_back()
        )

    elif text == 'مبلغ جوایز🤑':
        send_message(chat_id, '📌 برای دیدن جوایز روی لینک زیر کلیک کن:\nhttps://t.me/YourChannelRules', reply_markup=btn_back())

    elif text == 'مشاهده نفرات برتر 📊':
        send_message(chat_id, '⏳ در حال بارگذاری ...')
        import time
        time.sleep(3)
        send_message(chat_id, leaderboard_text, reply_markup=btn_back())

    elif text == 'پروفایل من👤':
        send_message(chat_id, 'فقط 10 نفر برتر به این بخش دسترسی دارند 🏆', reply_markup=btn_back())

    elif text == 'برگشت 🔙':
        send_main_panel(chat_id)

def handle_callback(query):
    data = query['data']
    user_id = query['from']['id']
    chat_id = query['message']['chat']['id']

    if data == 'verify':
        if is_subscribed(user_id):
            update_joined(user_id)
            send_message(chat_id, '✅ عضویت شما تایید شد!', reply_markup=main_keyboard())
        else:
            send_message(chat_id, '⚠️ هنوز عضو نشدی!')

# --- رابط‌های گرافیکی ---
def send_main_panel(chat_id):
    send_message(chat_id, 'سلام! یکی از گزینه‌ها رو انتخاب کن 👇', reply_markup=main_keyboard())

def send_admin_panel(chat_id):
    send_message(chat_id, '🎛 پنل مدیریت:', reply_markup={
        'keyboard': [[{'text': 'نوشتن لیست نفرات برتر'}], [{'text': '3 نفر برتر واقعی'}, {'text': 'شروع ربات'}]], 'resize_keyboard': True
    })

def send_force_join(chat_id):
    send_message(chat_id, 'لطفاً در کانال‌های زیر عضو شو:\n👇👇👇', reply_markup={
        'inline_keyboard': [
            [{'text': '🔥HotTof🔥', 'url': 'https://t.me/hottof'}, {'text': '🛜هات اسپات🛜', 'url': 'https://t.me/Hottspots'}],
            [{'text': 'تایید عضویت✅', 'callback_data': 'verify'}]
        ]
    })

def main_keyboard():
    return {
        'keyboard': [
            [{'text': 'مبلغ جوایز🤑'}],
            [{'text': 'پروفایل من👤'}, {'text': 'مشاهده نفرات برتر 📊'}],
            [{'text': 'دعوت دوستان💰'}]
        ],
        'resize_keyboard': True
    }

def btn_back():
    return {'keyboard': [[{'text': 'برگشت 🔙'}]], 'resize_keyboard': True}

# متغیر برای نمایش لیست برتر
leaderboard_text = '🟨 هنوز لیست آپدیت نشده'
