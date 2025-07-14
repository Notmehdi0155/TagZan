from datetime import datetime, timedelta
from config import ADMIN_ID, BOT_USERNAME
from utils import send_message, is_subscribed
from database import *

# متغیرهای وضعیت
awaiting_leaderboard_text = False
awaiting_competition_days = False

leaderboard_text = '🟨 هنوز لیست آپدیت نشده'

def handle_message(msg):
    global awaiting_leaderboard_text, leaderboard_text, awaiting_competition_days

    text = msg.get('text', '')
    user_id = msg['from']['id']
    fullname = msg['from'].get('first_name', '')
    username = msg['from'].get('username') or 'NoUsername'
    chat_id = msg['chat']['id']

    # --- اگر ادمین در انتظار ارسال متن لیست برتر است ---
    if user_id == ADMIN_ID and awaiting_leaderboard_text:
        leaderboard_text = text  # ذخیره متن جدید
        awaiting_leaderboard_text = False
        send_message(chat_id, '✅ لیست نفرات برتر به‌روزرسانی شد.')
        return

    # --- اگر ادمین در انتظار ارسال تعداد روز مسابقه است ---
    if user_id == ADMIN_ID and awaiting_competition_days:
        try:
            days = int(text)
            if days <= 0:
                raise ValueError()
            start_time = datetime.utcnow()
            set_competition(start_time, days)  # ذخیره مسابقه در دیتابیس
            awaiting_competition_days = False
            send_message(chat_id, f'✅ مسابقه با مدت {days} روز شروع شد و از همین الان فعال است.')
        except:
            send_message(chat_id, '❌ لطفا فقط یک عدد صحیح بزرگتر از صفر وارد کنید.')
        return

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
            return

        elif text == 'نوشتن لیست نفرات برتر':
            awaiting_leaderboard_text = True
            send_message(chat_id, 'لطفا متن لیست نفرات برتر را ارسال کنید.')
            return

        elif text == 'شروع ربات':
            awaiting_competition_days = True
            send_message(chat_id, 'لطفا تعداد روزهای مسابقه را به عدد وارد کنید.')
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

    # --- دکمه‌ها ---
    if text == 'دعوت دوستان💰':
        joined, left, score = get_stats(user_id)
        link = f'https://t.me/{BOT_USERNAME}?start={user_id}'

        comp = get_competition()
        if comp and comp['start_time']:
            now = datetime.utcnow()
            end_time = comp['start_time'] + timedelta(days=comp['duration_days'])
            if now > end_time:
                time_left_text = "⏳ پایان مهلت مسابقه."
            else:
                remaining = end_time - now
                days_left = remaining.days
                hrs = remaining.seconds // 3600
                mins = (remaining.seconds % 3600) // 60
                time_left_text = f"⏳ پایان مهلت تا {days_left} روز و {hrs} ساعت و {mins} دقیقه"
        else:
            time_left_text = "⏳ مسابقه فعالی نیست."

        send_message(chat_id,
            f'🔰 تعداد کسانی که دعوت کردید = {joined}\n'
            f'🔰 کسانی که لفت دادن = {left}\n'
            f'🔰 مجموع امتیاز = {score}\n\n'
            f'{time_left_text}\n\n'
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
