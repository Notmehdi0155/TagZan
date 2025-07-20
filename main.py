import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import asyncio
from utils import gen_code, save_files, get_files
import os

API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# حالت‌های FSM برای سوپر ادمین
class SuperAdminStates(StatesGroup):
    waiting_files = State()
    waiting_cover = State()
    waiting_caption = State()

# حافظه موقت برای ذخیره فایل‌های دریافتی قبل از مرحله بعد
superadmin_temp = {}

# کیبورد مرحله بعد
next_step_kb = ReplyKeyboardMarkup(resize_keyboard=True)
next_step_kb.add(KeyboardButton("📎 مرحله بعد"))

@dp.message_handler(commands=['start'])
async def start_cmd(msg: types.Message):
    await msg.answer("سلام! خوش آمدید.")

@dp.message_handler(commands=['super'])
async def superadmin_start(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    superadmin_temp[cid] = []
    await msg.answer("فایل‌های خود را ارسال کنید. سپس روی '📎 مرحله بعد' بزنید.", reply_markup=next_step_kb)
    await SuperAdminStates.waiting_files.set()

@dp.message_handler(lambda m: m.text == "📎 مرحله بعد", state=SuperAdminStates.waiting_files)
async def handle_next_step(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    if not superadmin_temp.get(cid):
        await msg.reply("هنوز فایلی ارسال نکردید!")
        return
    await msg.reply("حالا فایل کاور را بفرستید (عکس یا ویدیو).", reply_markup=types.ReplyKeyboardRemove())
    await SuperAdminStates.waiting_cover.set()

@dp.message_handler(content_types=types.ContentType.ANY, state=SuperAdminStates.waiting_files)
async def handle_files(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    file_id = None
    if msg.video:
        file_id = msg.video.file_id
    elif msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document:
        file_id = msg.document.file_id
    else:
        await msg.reply("فقط عکس، ویدیو یا فایل قابل قبول است.")
        return
    superadmin_temp[cid].append(file_id)
    await msg.reply("فایل دریافت شد. می‌تونید فایل‌های بیشتری ارسال کنید یا روی '📎 مرحله بعد' بزنید.")

@dp.message_handler(content_types=types.ContentType.ANY, state=SuperAdminStates.waiting_cover)
async def handle_cover(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    cover_id = None
    if msg.video:
        cover_id = msg.video.file_id
    elif msg.photo:
        cover_id = msg.photo[-1].file_id
    else:
        await msg.reply("فقط عکس یا ویدیو به عنوان کاور قابل قبول است.")
        return
    await state.update_data(cover_id=cover_id)
    await msg.reply("کپشن را بفرستید.")
    await SuperAdminStates.waiting_caption.set()

@dp.message_handler(state=SuperAdminStates.waiting_caption)
async def handle_caption(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    caption = msg.text
    data = await state.get_data()
    cover_id = data.get("cover_id")
    file_ids = superadmin_temp.get(cid, [])
    code = gen_code()
    save_files(file_ids, code, cover_id, caption)
    await msg.reply(f"✅ فایل‌ها ذخیره شدند. لینک مشاهده:
https://t.me/YOUR_BOT?start=view_{code}")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
