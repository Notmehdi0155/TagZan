# bot.py - نسخه پیشرفته با عضویت اجباری چندکاناله

import logging
import sqlite3
from uuid import uuid4

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
import config

# ----- تنظیمات لاگ -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- دیتابیس -----
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS files (
    file_id TEXT,
    unique_id TEXT PRIMARY KEY,
    caption TEXT,
    downloads INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS force_channels (
    username TEXT PRIMARY KEY
)''')
conn.commit()

# ----- وضعیت کاربران -----
STATE = {}

# گرفتن لیست کانال‌های عضویت اجباری
def get_force_channels():
    rows = c.execute("SELECT username FROM force_channels").fetchall()
    return [row[0] for row in rows]

# بررسی عضویت در همه کانال‌ها
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channels = [config.MAIN_FORCE_SUB_CHANNEL] + get_force_channels()
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    if args and args[0].startswith("file_"):
        unique_id = args[0].split("_", 1)[1]

        if not await check_membership(user_id, context):
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("عضو شدم ✅", callback_data=f"checksub_{unique_id}")]])
            await update.message.reply_text("برای دریافت فایل باید ابتدا در کانال‌های زیر عضو شوید:", reply_markup=btn)
            return

        file = c.execute("SELECT * FROM files WHERE unique_id=?", (unique_id,)).fetchone()
        if file:
            file_id, _, caption, downloads = file
            new_count = downloads + 1
            c.execute("UPDATE files SET downloads=? WHERE unique_id=?", (new_count, unique_id))
            conn.commit()

            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"📥 دریافت: {new_count} بار", url="https://t.me/"+config.BOT_USERNAME)]])
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=caption, reply_markup=btn)
    else:
        await update.message.reply_text("سلام! برای دریافت فایل از لینک‌های اختصاصی استفاده کن.")

# دکمه بررسی عضویت
async def checksub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    _, unique_id = query.data.split("_", 1)
    await query.answer()

    if await check_membership(user_id, context):
        file = c.execute("SELECT * FROM files WHERE unique_id=?", (unique_id,)).fetchone()
        if file:
            file_id, _, caption, downloads = file
            new_count = downloads + 1
            c.execute("UPDATE files SET downloads=? WHERE unique_id=?", (new_count, unique_id))
            conn.commit()

            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"📥 دریافت: {new_count} بار", url="https://t.me/"+config.BOT_USERNAME)]])
            await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=caption, reply_markup=btn)
            await query.message.delete()
    else:
        await query.answer("هنوز عضو نشدی!", show_alert=True)

# /panel
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        return

    btns = ReplyKeyboardMarkup([
        ["📤 آپلود فایل", "📊 آمار"],
        ["➕ افزودن کانال اجباری", "➖ حذف کانال اجباری"],
        ["📋 لیست کانال‌های اجباری"]
    ], resize_keyboard=True)
    await update.message.reply_text("پنل مدیریت باز شد:", reply_markup=btns)

# پیام‌های ادمین
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        return

    if text == "📤 آپلود فایل":
        STATE[user_id] = "awaiting_file"
        await update.message.reply_text("فایل را بفرستید.", reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True))

    elif text == "📊 آمار":
        count = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        total = c.execute("SELECT SUM(downloads) FROM files").fetchone()[0] or 0
        await update.message.reply_text(f"📁 فایل‌ها: {count}\n📥 مجموع دریافت‌ها: {total}")

    elif text == "➕ افزودن کانال اجباری":
        STATE[user_id] = "add_channel"
        await update.message.reply_text("یوزرنیم کانال (با @) را وارد کنید:")

    elif text == "➖ حذف کانال اجباری":
        STATE[user_id] = "remove_channel"
        await update.message.reply_text("یوزرنیم کانال برای حذف:")

    elif text == "📋 لیست کانال‌های اجباری":
        channels = get_force_channels()
        msg = "📌 کانال‌ها:\n" + "\n".join(channels) if channels else "⚠️ کانالی تنظیم نشده."
        await update.message.reply_text(msg)

    elif text == "🔙 بازگشت":
        STATE.pop(user_id, None)
        await panel(update, context)

    elif STATE.get(user_id) == "add_channel":
        username = text.strip()
        try:
            c.execute("INSERT INTO force_channels (username) VALUES (?)", (username,))
            conn.commit()
            await update.message.reply_text(f"✅ کانال {username} اضافه شد.")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ این کانال قبلاً اضافه شده.")
        STATE.pop(user_id)

    elif STATE.get(user_id) == "remove_channel":
        username = text.strip()
        c.execute("DELETE FROM force_channels WHERE username = ?", (username,))
        conn.commit()
        await update.message.reply_text(f"❌ کانال {username} حذف شد.")
        STATE.pop(user_id)

# فایل‌ها
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS or STATE.get(user_id) != "awaiting_file":
        return

    doc = update.message.document or update.message.video or update.message.photo or update.message.audio
    if not doc:
        await update.message.reply_text("فایل معتبر نیست.")
        return

    caption = update.message.caption or ""
    forwarded = await context.bot.forward_message(chat_id=config.STORAGE_CHANNEL, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    file_id = forwarded.document.file_id if forwarded.document else forwarded.video.file_id if forwarded.video else None
    unique_id = str(uuid4())[:8]
    c.execute("INSERT INTO files (file_id, unique_id, caption) VALUES (?, ?, ?)", (file_id, unique_id, caption))
    conn.commit()

    link = f"https://t.me/{config.BOT_USERNAME}?start=file_{unique_id}"
    await update.message.reply_text(f"✅ فایل ذخیره شد\n🔗 لینک: {link}")
    await panel(update, context)
    STATE.pop(user_id)

# اجرای Webhook
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(checksub_callback, pattern="checksub_.*"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.Photo.ALL | filters.Audio.ALL, file_handler))

    async def setup_webhook():
        await app.bot.set_webhook(url=config.WEBHOOK_URL)

    app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_path="",
        on_startup=setup_webhook,
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,
            )
    
