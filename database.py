from config import ADMIN_ID, BOT_USERNAME
from utils import send_message, is_subscribed, delete_message
from database import *

awaiting_leaderboard_text = False
leaderboard_text = '🟨 هنوز لیست آپدیت نشده'

# نگهداری آی‌دی پیام عضویت اجباری برای حذف
user_force_join_message = {}

def handle_message(msg):
    global awaiting_leaderboard_text, leaderboard_text

    text = msg.get('text', '')
    user_id = msg['from']['id']
    fullname = msg['from'].get('first_name', '')
    username = msg['from'].get('username') or 'NoUsername'
    chat_id = msg['chat']['id']

    if user_id == ADMIN_ID and awaiting_leaderboard_text:
        leaderboard_text = text
        awaiting_leaderboard_text = False
        send_message(chat_id, '✅ لیست نفرات برتر به‌روزرسانی شد.')
        return

    if text.startswith('/start'):
        args = text.split()
        inviter = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None
        add_user(user_id, username, fullname, inviter)

        if is_subscribed(user_id):
            update_joined(user_id)
            send_main_panel(chat_id)
        else:
            msg_res = send_force_join(chat_id)
            user_force_join_message[user_id] = msg_res['result']['message_id']  # ذخیره پیام برای حذف بعدا
        return

    if user_id == ADMIN_ID:
        if text == '/panel':
            send_admin_panel(chat_id)
            return
        elif text == 'نوشتن لیست نفرات برتر':
            awaiting_leaderboard_text = True
            send_message(chat_id, 'لطفا متن لیست نفرات برتر را ارسال کنید.')
            return
        elif text == 'شروع ربات':
            send_message(chat_id, '✅ مسابقه آغاز شد.')
            return
        elif text == '3 نفر برتر واقعی':
            result = ''
            top = get_top_inviters(3)
            for uid, count in top:
                u = get_user(uid)
                if u:
                    result += f'🏆 {u[2]} (@{u[1]}) → {count} دعوت\n'
            send_message(chat_id, result or 'هیچ دعوتی نشده.')
            return

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
        return

    elif text == 'مبلغ جوایز🤑':
        send_message(chat_id, '📌 برای دیدن جوایز روی لینک زیر کلیک کن:\nhttps://t.me/YourChannelRules', reply_markup=btn_back())
        return

    elif text == 'مشاهده نفرات برتر 📊':
        send_message(chat_id, '⏳ در حال بارگذاری ...')
        import time
        time.sleep(3)
        send_message(chat_id, leaderboard_text, reply_markup=btn_back())
        return

    elif text == 'پروفایل من👤':
        send_message(chat_id, 'فقط 10 نفر برتر به این بخش دسترسی دارند 🏆', reply_markup=btn_back())
        return

    elif text == 'برگشت 🔙':
        send_main_panel(chat_id)
        return

def handle_callback(query):
    data = query['data']
    user_id = query['from']['id']
    chat_id = query['message']['chat']['id']

    if data == 'verify':
        if is_subscribed(user_id):
            update_joined(user_id)
            # حذف پیام عضویت اجباری قبلی
            msg_id = user_force_join_message.get(user_id)
            if msg_id:
                delete_message(chat_id, msg_id)
                user_force_join_message.pop(user_id, None)
            send_message(chat_id, '✅ عضویت شما تایید شد!', reply_markup=main_keyboard())
        else:
            # نمایش پیام هشدار با دکمه اوکی (پیام آلرت)
            send_alert_message(chat_id, user_id)

# ارسال پیام عضویت اجباری و گرفتن آی‌دی پیام
def send_force_join(chat_id):
    payload = {
        'chat_id': chat_id,
        'text': 'لطفاً در کانال‌های زیر عضو شوید👇',
        'reply_markup': {
            'inline_keyboard': [
                [{'text': '🔥HotTof🔥', 'url': 'https://t.me/hottof'}],
                [{'text': '🛜هات اسپات🛜', 'url': 'https://t.me/Hottspots'}],
                [{'text': 'تایید عضویت✅', 'callback_data': 'verify'}]
            ]
        }
    }
    res = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json=payload).json()
    return res

# پیام هشدار عضو نشدن با دکمه اوکی (پیام آلرت)
def send_alert_message(chat_id, user_id):
    payload = {
        'chat_id': chat_id,
        'text': '⚠️ شما هنوز عضو کانال‌های ربات نشده‌اید.',
        'reply_markup': {
            'inline_keyboard': [[{'text': 'اوکی', 'callback_data': 'alert_ok'}]]
        }
    }
    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json=payload)

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

def send_main_panel(chat_id):
    send_message(chat_id, 'سلام! یکی از گزینه‌ها رو انتخاب کن 👇', reply_markup=main_keyboard())

def send_admin_panel(chat_id):
    send_message(chat_id, '🎛 پنل مدیریت:', reply_markup={
        'keyboard': [[{'text': 'نوشتن لیست نفرات برتر'}], [{'text': '3 نفر برتر واقعی'}, {'text': 'شروع ربات'}]], 'resize_keyboard': True
    })
