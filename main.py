# bot.py - نسخه کامل Webhook-ready

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
conn.commit()

# ----- وضعیت کاربران -----
STATE = {}

# بررسی عضویت
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(config.FORCE_SUB_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    if args and args[0].startswith("file_"):
        unique_id = args[0].split("_", 1)[1]

        if not await check_membership(user_id, context):
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("عضو شدم ✅", callback_data=f"checksub_{unique_id}")]])
            await update.message.reply_text("برای دریافت فایل باید از قبل در کانال عضو شوید:", reply_markup=btn)
            return

        file = c.execute("SELECT * FROM files WHERE unique_id=?", (unique_id,)).fetchone()
        if file:
            file_id, _, caption, downloads = file
            new_count = downloads + 1
            c.execute("UPDATE files SET downloads=? WHERE unique_id=?", (new_count, unique_id))
            conn.commit()

            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"📅 دریافت: {new_count} بار", url="https://t.me/"+config.BOT_USERNAME)]])

            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=caption, reply_markup=btn)
    else:
        await update.message.reply_text("سلام! برای دریافت فایل از لینک‌های اختصاصی استفاده کن.")

# بررسی عضویت از دکمه
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

            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"📅 دریافت: {new_count} بار", url="https://t.me/"+config.BOT_USERNAME)]])
            await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=caption, reply_markup=btn)
            await query.message.delete()
    else:
        await query.answer("هنوز عضو نشدید!", show_alert=True)

# /panel
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        return

    btns = ReplyKeyboardMarkup([
        ["\ud83d\udcc4 \u0622\u067e\u0644\u0648\u062f \u0641\u0627\u06cc\u0644", "\ud83d\udcca \u0622\u0645\u0627\u0631"],
        ["\ud83d\udd17 \u0627\u0641\u0632\u0648\u062f\u0646 \u0639\u0636\u0648\u06cc\u062a \u0627\u062c\u0628\u0627\u0631\u06cc"]
    ], resize_keyboard=True)
    await update.message.reply_text("\u0648\u0627\u0631\u062f \u067e\u0646\u0644 \u0634\u062f\u06cc\u062f:", reply_markup=btns)

# متن‌ها
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        return

    if text == "\ud83d\udcc4 \u0622\u067e\u0644\u0648\u062f \u0641\u0627\u06cc\u0644":
        STATE[user_id] = "awaiting_file"
        await update.message.reply_text("فایلتون را ارسال کنید.", reply_markup=ReplyKeyboardMarkup([["\ud83d\udd19 \u0628\u0627\u0632\u06af\u0634\u062a"]], resize_keyboard=True))

    elif text == "\ud83d\udcca \u0622\u0645\u0627\u0631":
        count = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        total = c.execute("SELECT SUM(downloads) FROM files").fetchone()[0] or 0
        await update.message.reply_text(f"\ud83d\udcc5 \u062a\u0639\u062f\u0627\u062f \u0641\u0627\u06cc\u0644\u200c\u0647\u0627: {count}\n\ud83d\udce5 \u062f\u0631\u06cc\u0627\u0641\u062a \u0647\u0627: {total}")

    elif text == "\ud83d\udd17 \u0627\u0641\u0632\u0648\u062f\u0646 \u0639\u0636\u0648\u06cc\u062a \u0627\u062c\u0628\u0627\u0631\u06cc":
        STATE[user_id] = "awaiting_channel"
        await update.message.reply_text("ایدی کانال را وارد کنید (با @):")

    elif text == "\ud83d\udd19 \u0628\u0627\u0632\u06af\u0634\u062a":
        STATE.pop(user_id, None)
        await panel(update, context)

    elif STATE.get(user_id) == "awaiting_channel":
        config.FORCE_SUB_CHANNEL = text.strip()
        STATE.pop(user_id)
        await update.message.reply_text(f"تنظیم شد: {text.strip()}")
        await panel(update, context)

# هندلر فایل
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
    await update.message.reply_text(f"فایل ذخیره شد\nلینک: {link}")
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
    
