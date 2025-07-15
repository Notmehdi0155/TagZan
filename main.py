import logging
import uuid
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import MessageCantBeDeleted

API_TOKEN = '7301497411:AAG_Ku0lXkAzOhGQB021bpwxGDz0YqwkJhE'
WEBHOOK_HOST = 'https://tagzan.onrender.com'
WEBHOOK_PATH = '/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 10000

ADMIN_IDS = [6039863213, 6387942633]
REQUIRED_CHANNELS = [
    'https://t.me/zistkonkoordarvizist',
    'https://t.me/azmoon_jozveh'
]
DB_CHANNEL = '@file_database_channel'  # کانال دیتابیس با ادمین بودن ربات

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

user_links = {}
file_links = {}
channel_list = set(REQUIRED_CHANNELS)
user_files = {}

class UploadFiles(StatesGroup):
    waiting_files = State()

class Broadcast(StatesGroup):
    waiting_message = State()

def get_admin_panel():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("اپلود"),
        KeyboardButton("ارسال همگانی"),
        KeyboardButton("تنظیم کانال"),
        KeyboardButton("آمار")
    )

@dp.message_handler(commands=['start', 'panel'])
async def send_panel(msg: types.Message):
    if msg.from_user.id in ADMIN_IDS:
        await msg.answer("به پنل ادمین خوش آمدید:", reply_markup=get_admin_panel())

@dp.message_handler(lambda m: m.text == 'اپلود', user_id=ADMIN_IDS)
async def handle_upload(msg: types.Message, state: FSMContext):
    await msg.answer("فایل‌های خود را ارسال کنید. پس از اتمام، روی 'برگشت' بزنید.")
    await UploadFiles.waiting_files.set()
    user_files[msg.from_user.id] = []

@dp.message_handler(lambda m: m.text == 'برگشت', state=UploadFiles.waiting_files, user_id=ADMIN_IDS)
async def handle_done_uploading(msg: types.Message, state: FSMContext):
    files = user_files.get(msg.from_user.id, [])
    if not files:
        await msg.answer("هیچ فایلی ارسال نشده است.")
        return
    uid = str(uuid.uuid4())
    file_links[uid] = files
    user_links[msg.from_user.id] = uid
    await state.finish()
    await msg.answer(f"✅ لینک اختصاصی فایل‌ها:\nhttps://t.me/{(await bot.get_me()).username}?start={uid}")

@dp.message_handler(content_types=types.ContentType.ANY, state=UploadFiles.waiting_files, user_id=ADMIN_IDS)
async def save_file(msg: types.Message):
    sent = await bot.copy_message(DB_CHANNEL, msg.chat.id, msg.message_id)
    user_files[msg.from_user.id].append(sent.message_id)

@dp.message_handler(lambda m: m.text == 'ارسال همگانی', user_id=ADMIN_IDS)
async def ask_broadcast(msg: types.Message):
    await msg.answer("پیامی که می‌خواهید ارسال شود را بنویسید.")
    await Broadcast.waiting_message.set()

@dp.message_handler(state=Broadcast.waiting_message, content_types=types.ContentType.ANY, user_id=ADMIN_IDS)
async def do_broadcast(msg: types.Message, state: FSMContext):
    await state.finish()
    count = 0
    for user_id in user_links:
        try:
            await bot.copy_message(user_id, msg.chat.id, msg.message_id)
            count += 1
        except:
            continue
    await msg.answer(f"پیام برای {count} نفر ارسال شد.")

@dp.message_handler(lambda m: m.text == 'تنظیم کانال', user_id=ADMIN_IDS)
async def manage_channels(msg: types.Message):
    await msg.answer("لینک کانال را برای اضافه/حذف بفرستید:")

@dp.message_handler(lambda m: m.text.startswith('https://t.me/'), user_id=ADMIN_IDS)
async def add_or_remove_channel(msg: types.Message):
    link = msg.text.strip()
    if link in channel_list:
        channel_list.remove(link)
        await msg.answer("کانال حذف شد ✅")
    else:
        channel_list.add(link)
        await msg.answer("کانال اضافه شد ✅")

@dp.message_handler(lambda m: m.text == 'آمار', user_id=ADMIN_IDS)
async def ask_for_stat_link(msg: types.Message):
    await msg.answer("لینک اختصاصی فایل‌ها را بفرستید:")

@dp.message_handler(lambda m: m.text.startswith("https://t.me/"), user_id=ADMIN_IDS)
async def show_stats(msg: types.Message):
    if 'start=' not in msg.text:
        await msg.answer("لینک معتبر نیست.")
        return
    uid = msg.text.split("start=")[-1]
    count = len([u for u, l in user_links.items() if l == uid])
    await msg.answer(f"تعداد ارسال این فایل: {count} بار")

async def check_subscription(user_id):
    not_joined = []
    for link in channel_list:
        try:
            username = link.split('/')[-1]
            member = await bot.get_chat_member(username, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                not_joined.append(link)
        except:
            not_joined.append(link)
    return not_joined

@dp.message_handler(commands=['start'])
async def handle_start(msg: types.Message):
    if ' ' not in msg.text:
        return
    uid = msg.text.split()[1]
    if uid not in file_links:
        await msg.answer("لینک معتبر نیست یا فایل‌ها منقضی شده‌اند.")
        return
    not_joined = await check_subscription(msg.from_user.id)
    if not_joined:
        buttons = [
            [InlineKeyboardButton(text=link.split('/')[-1], url=link)] for link in not_joined
        ]
        buttons.append([InlineKeyboardButton(text='تایید عضویت ✅', callback_data=f'check:{uid}')])
        await msg.answer("برای دریافت فایل‌ها ابتدا در کانال‌های زیر عضو شوید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await send_files_to_user(msg.from_user.id, uid)

@dp.callback_query_handler(lambda c: c.data.startswith('check:'))
async def handle_check_subscription(call: types.CallbackQuery):
    uid = call.data.split(':')[1]
    not_joined = await check_subscription(call.from_user.id)
    try:
        await call.message.delete()
    except MessageCantBeDeleted:
        pass
    if not not_joined:
        await send_files_to_user(call.from_user.id, uid)
    else:
        buttons = [
            [InlineKeyboardButton(text=link.split('/')[-1], url=link)] for link in not_joined
        ]
        buttons.append([InlineKeyboardButton(text='تایید عضویت ✅', callback_data=f'check:{uid}')])
        await bot.send_message(call.from_user.id, "هنوز عضو همه کانال‌ها نشده‌اید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def send_files_to_user(user_id, uid):
    for msg_id in file_links.get(uid, []):
        try:
            await bot.copy_message(user_id, DB_CHANNEL, msg_id)
        except:
            pass
    await bot.send_message(user_id, "⚠️ این فایل‌ها پس از ۱۲۰ ثانیه حذف خواهند شد! ⏳")
    user_links[user_id] = uid

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
