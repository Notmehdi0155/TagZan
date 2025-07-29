from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from database import (
    save_file, get_file, get_channels, add_channel, remove_channel,
    get_all_user_ids, save_user_id, get_active_users, get_start_count
)
from utils import gen_code

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True
active_users = set()

def send(method, data):
    response = requests.post(f"{URL}/{method}", json=data).json()
    print(f"Response from {method}: {response}")
    return response

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def is_joined(user_id, channel_link):
    try:
        username = channel_link.split("/")[-1]
        r = requests.get(f"{URL}/getChatMember", params={
            "chat_id": f"@{username}", "user_id": user_id
        }).json()
        return r.get("result", {}).get("status") in ["member", "administrator", "creator"]
    except:
        return False

def get_user_unjoined_channels(user_id):
    return [ch for ch in get_channels() if not is_joined(user_id, ch)]

def make_force_join_markup(channels, code):
    buttons = [[{"text": f"📢 کانال {i+1}", "url": ch}] for i, ch in enumerate(channels)]
    buttons.append([{"text": "✅ عضو شدم", "callback_data": f"checksub_{code}"}])
    return {"inline_keyboard": buttons}

def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

def monitor_subscriptions():
    while True:
        for uid in list(active_users):
            unjoined = get_user_unjoined_channels(uid)
            if unjoined:
                send("sendMessage", {
                    "chat_id": uid,
                    "text": "کون طلایی از چنل لفت دادی چرا بیا جوین شو چنل بدون تو صفا نداره 😔💔",
                    "reply_markup": make_force_join_markup(unjoined, "dummy")
                })
                active_users.remove(uid)
        time.sleep(1)

threading.Thread(target=ping, daemon=True).start()
threading.Thread(target=monitor_subscriptions, daemon=True).start()

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        save_user_id(uid)
        if text.startswith("/start"):
            save_user_id(uid)  # استارت همزمان ثبت می‌شود

        if text.startswith("/start "):
            code = text.split("/start ")[1]
            from utils import get_file, recover_file_from_channel  # اضافه کردن بالا

            file_id = get_file(code)
            if not file_id:
                file_id = recover_file_from_channel(code)
            if file_id:
                unjoined = get_user_unjoined_channels(uid)
                if unjoined:
                    send("sendMessage", {
                        "chat_id": cid,
                        "text": "فدای اون شومبولت یه همت بکن عضو چنل شو تا فایل رو برات بفرستم ❤️",
                        "reply_markup": make_force_join_markup(unjoined, code)
                    })
                    return "ok"
                message_ids = []
                if "|" in file_id:
                    for fid in file_id.split("|"):
                        sent = send("sendDocument", {"chat_id": cid, "document": fid})
                        if sent and "result" in sent:
                            message_ids.append(sent["result"]["message_id"])
                else:
                    sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                    if sent and "result" in sent:
                        message_ids.append(sent["result"]["message_id"])
                warn = send("sendMessage", {"chat_id": cid, "text": "سریع ذخیره کن داخل سیو مسج 20 ثانیه دیگه میپاکمش ⚠️"})
                if warn and "result" in warn:
                    message_ids.append(warn["result"]["message_id"])
                for m in message_ids:
                    threading.Timer(20, delete, args=(cid, m)).start()
                active_users.add(uid)
            return "ok"

        if text == "/start":
            send("sendMessage", {
                "chat_id": cid,
                "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"
            })

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [
                [{"text": "📤آپلود"}],
                [{"text": "🖼پست"}],
                [{"text": "🔐 عضویت اجباری"}],
                [{"text": "📢 ارسالی همگانی"}],
                [{"text": "📊 آمار"}]
            ], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "📊 آمار" and uid in ADMIN_IDS:
            total = len(get_all_user_ids())
            hour_users = get_active_users(3600)
            day_users = get_active_users(86400)
            week_users = get_active_users(7 * 86400)
            month_users = get_active_users(30 * 86400)
            hour_starts = get_start_count(3600)
            day_starts = get_start_count(86400)
            week_starts = get_start_count(7 * 86400)

            stats = f"""آمار ربات از نظر تعداد افراد به شرح زیر می‌باشد 🤖

👥 تعداد کل اعضا : {total:,}
🕒 تعداد کاربران ساعت گذشته : {hour_users:,}
☪️ تعداد کاربران 24 ساعت گذشته : {day_users:,}
7️⃣ تعداد کاربران هفته گذشته : {week_users:,}
🌛 تعداد کاربران ماه گذشته : {month_users:,}

آمار ربات از نظر تعداد استارت ربات به شرح زیر می‌باشد 📩

تعداد استارت در ساعت گذشته :👾 {hour_starts:,}
تعداد استارت در 24 ساعت گذشته :🌝 {day_starts:,}
تعداد استارت در هفته گذشته : ⚡ {week_starts:,}
"""
            send("sendMessage", {"chat_id": cid, "text": stats})

        elif text == "📤آپلود" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_super_files", "files": []}
            send("sendMessage", {
                "chat_id": cid,
                "text": "همه فایل‌هاتو بفرست. هر وقت تموم شد، روی «⏭ مرحله بعد» بزن.",
                "reply_markup": {"keyboard": [[{"text": "⏭ مرحله بعد"}]], "resize_keyboard": True}
            })

        

        

        elif text == "📢 ارسالی همگانی" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_broadcast"}
            send("sendMessage", {
                "chat_id": cid, "text": "پیامت رو بفرست یا روی «↩️ بازگشت» بزن.",
                "reply_markup": {"keyboard": [[{"text": "↩️ بازگشت"}]], "resize_keyboard": True}
            })

        elif state.get("step") == "awaiting_broadcast":
            if text.strip() == "↩️ بازگشت":
                users.pop(uid)
                send("sendMessage", {
                    "chat_id": cid, "text": "بازگشت به پنل.",
                    "reply_markup": {"keyboard": [
                        [{"text": "📤آپلود"}],
                        [{"text": "🖼پست"}],
                        [{"text": "🔐 عضویت اجباری"}],
                        [{"text": "📢 ارسالی همگانی"}],
                        [{"text": "📊 آمار"}]
                    ], "resize_keyboard": True}
                })
            else:
                users.pop(uid)
                uids = get_all_user_ids()
                if "photo" in msg:
                    pid = msg["photo"][-1]["file_id"]
                    cap = msg.get("caption", "")
                    for uid2 in uids:
                        send("sendPhoto", {"chat_id": uid2, "photo": pid, "caption": cap})
                elif "text" in msg:
                    for uid2 in uids:
                        send("sendMessage", {"chat_id": uid2, "text": msg["text"]})
                send("sendMessage", {
                    "chat_id": cid, "text": "✅ پیام به همه ارسال شد.",
                    "reply_markup": {"keyboard": [
                        [{"text": "📤آپلود"}],
                        [{"text": "🖼پست"}],
                        [{"text": "🔐 عضویت اجباری"}],
                        [{"text": "📢 ارسالی همگانی"}],
                        [{"text": "📊 آمار"}]
                    ], "resize_keyboard": True}
                })

        elif text == "🔐 عضویت اجباری" and uid in ADMIN_IDS:
            channels = get_channels()
            lines = ["📋 لیست کانال‌ها:"] + [f"🔗 {ch}" for ch in channels] if channels else ["❌ هیچی ثبت نشده"]
            lines.append("\n➕ برای اضافه کردن: `+https://t.me/...`\n➖ برای حذف: `-https://t.me/...`")
            send("sendMessage", {"chat_id": cid, "text": "\n".join(lines), "parse_mode": "Markdown"})

        elif uid in ADMIN_IDS and text.startswith("+https://t.me/"):
            add_channel(text[1:])
            send("sendMessage", {"chat_id": cid, "text": "✅ کانال اضافه شد."})

        elif uid in ADMIN_IDS and text.startswith("-https://t.me/"):
            remove_channel(text[1:])
            send("sendMessage", {"chat_id": cid, "text": "🗑 کانال حذف شد."})

    elif "callback_query" in update:
        cq = update["callback_query"]
        uid = cq["from"]["id"]
        cid = cq["message"]["chat"]["id"]
        mid = cq["message"]["message_id"]
        data = cq["data"]

        if data.startswith("checksub_"):
            code = data.split("_")[1]
            unjoined = get_user_unjoined_channels(uid)
            if not unjoined:
                send("deleteMessage", {"chat_id": cid, "message_id": mid})
                file_id = get_file(code)
                message_ids = []
                if file_id:
                    if "|" in file_id:
                        for fid in file_id.split("|"):
                            sent = send("sendDocument", {"chat_id": cid, "document": fid})
                            if sent and "result" in sent:
                                message_ids.append(sent["result"]["message_id"])
                    else:
                        sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                        if sent and "result" in sent:
                            message_ids.append(sent["result"]["message_id"])
                    warn = send("sendMessage", {"chat_id": cid, "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک می‌شود"})
                    if warn and "result" in warn:
                        message_ids.append(warn["result"]["message_id"])
                    for m in message_ids:
                        threading.Timer(20, delete, args=(cid, m)).start()
                    active_users.add(uid)
                else:
                    send("sendMessage", {"chat_id": cid, "text": "❗ فایل یافت نشد."})
            else:
                send("answerCallbackQuery", {
                    "callback_query_id": cq["id"],
                    "text": "❌ هنوز عضو همه کانال‌ها نیستی!",
                    "show_alert": True
                })

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
