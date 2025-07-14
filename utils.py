import requests
from config import BOT_TOKEN, REQUIRED_CHANNELS, PING_URL, PING_INTERVAL
from database import update_left, update_joined, get_left_warned, set_left_warned
import time

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

def send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    requests.post(f'{API_URL}/sendMessage', json=payload)

def delete_message(chat_id, message_id):
    requests.post(f'{API_URL}/deleteMessage', json={'chat_id': chat_id, 'message_id': message_id})

def is_subscribed(user_id):
    for ch in REQUIRED_CHANNELS:
        res = requests.get(f'{API_URL}/getChatMember', params={'chat_id': ch, 'user_id': user_id}).json()
        status = res.get('result', {}).get('status') if res.get('result') else None
        if status in ['left', 'kicked', None]:
            return False
    return True

def ping_loop():
    from database import get_all_joined_users
    while True:
        try:
            requests.get(PING_URL)
        except:
            pass

        for (uid,) in get_all_joined_users():
            if not is_subscribed(uid):
                if get_left_warned(uid) == 0:
                    update_left(uid)
                    send_message(uid,
                        '⚠️ شما از کانال رفت دادید.\n'
                        'اگر قصد دارید در فرآیند قرعه‌کشی حضور داشته باشید لطفاً در کانال‌ها عضو بمانید👇💯',
                        reply_markup={
                            'inline_keyboard': [
                                [{'text': 'عضویت مجدد در HotTof', 'url': 'https://t.me/hottof'}],
                                [{'text': 'عضویت مجدد در هات اسپات', 'url': 'https://t.me/Hottspots'}]
                            ]
                        }
                    )
                    set_left_warned(uid, 1)
            else:
                # اگر دوباره عضو شد، ریست وضعیت و آپدیت
                set_left_warned(uid, 0)
                update_joined(uid)

        time.sleep(PING_INTERVAL)
