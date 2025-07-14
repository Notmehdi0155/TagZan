# utils.py

import requests
from config import BOT_TOKEN, REQUIRED_CHANNELS, PING_URL, PING_INTERVAL
from database import update_left
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

def is_subscribed(user_id):
    for ch in REQUIRED_CHANNELS:
        res = requests.get(f'{API_URL}/getChatMember', params={'chat_id': ch, 'user_id': user_id}).json()
        if res.get('result') is None or res['result'].get('status') in ['left', 'kicked']:
            return False
    return True

def ping_loop():
    from database import get_all_joined_users
    while True:
        try:
            requests.get(PING_URL)
        except:
            pass

        # چک عضویت کاربران و ارسال اخطار در صورت لفت
        for (uid,) in get_all_joined_users():
            if not is_subscribed(uid):
                update_left(uid)
                send_message(uid,
                    '⚠️ شما از کانال رفت دادید.\n'
                    'اگر قصد دارید در فرآیند قرعه‌کشی حضور داشته باشید لطفاً در کانال‌ها عضو بمانید👇💯'
                )
        time.sleep(PING_INTERVAL)
