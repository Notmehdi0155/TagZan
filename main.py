from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from config import TOKEN, ADMINS, VIDEO_LINK

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

user_data = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_data[message.from_user.id] = {}
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("شروع"))
    await message.answer("سلام 👋 به پذیرش مشاوره هوشمند خوش اومدی! برای شروع روی دکمه زیر بزن:", reply_markup=kb)

@dp.message_handler(lambda message: message.text == "شروع")
async def step_1(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("تجربی", "ریاضی", "انسانی")
    await message.answer("رشته تحصیلی خودت رو انتخاب کن:", reply_markup=kb)

@dp.message_handler(lambda message: message.text in ["تجربی","ریاضی","انسانی"])
async def step_2(message: types.Message):
    user_data[message.from_user.id]['رشته'] = message.text
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("دهم","یازدهم","دوازدهم","پشت‌کنکور")
    await message.answer("پایه تحصیلی خودت رو انتخاب کن:", reply_markup=kb)

@dp.message_handler(lambda message: message.text in ["دهم","یازدهم","دوازدهم","پشت‌کنکور"])
async def step_3(message: types.Message):
    user_data[message.from_user.id]['پایه'] = message.text
    await message.answer("لطفاً نام و نام خانوادگی خودت رو وارد کن:")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'نام' not in user_data[message.from_user.id])
async def step_4(message: types.Message):
    user_data[message.from_user.id]['نام'] = message.text
    await message.answer("لطفاً آیدی تلگرام خودت رو وارد کن (مثلاً @Mehdi123):")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'آیدی' not in user_data[message.from_user.id])
async def step_5(message: types.Message):
    user_data[message.from_user.id]['آیدی'] = message.text
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("ارسال اطلاعات فعلی", "تکمیل اطلاعات بیشتر")
    await message.answer("می‌خوای اطلاعاتت همینجا ارسال بشه یا اطلاعات تکمیلی وارد کنی؟", reply_markup=kb)

@dp.message_handler(lambda message: message.text == "ارسال اطلاعات فعلی")
async def send_basic(message: types.Message):
    data = user_data[message.from_user.id]
    text = f"📋 فرم جدید مشاوره\n👤 نام: {data['نام']}\n📚 رشته: {data['رشته']}\n🎓 پایه: {data['پایه']}\n📞 آیدی: {data['آیدی']}"
    for admin in ADMINS:
        await bot.send_message(admin, text)
    await message.answer(f"✅ اطلاعاتت با موفقیت ثبت شد.\nبه‌زودی مشاورت باهات تماس می‌گیره ✨\n{VIDEO_LINK}")

@dp.message_handler(lambda message: message.text == "تکمیل اطلاعات بیشتر")
async def step_6(message: types.Message):
    await message.answer("میانگین ساعت مطالعه روزانه‌ت چقدره؟")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'ساعت مطالعه' not in user_data[message.from_user.id] and message.text.isdigit())
async def step_7(message: types.Message):
    user_data[message.from_user.id]['ساعت مطالعه'] = int(message.text)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("قلم‌چی","ماز","خیلی‌سبز","گزینه‌دو","ثبت‌نام نکردم","سایر")
    await message.answer("در حال حاضر در چه مؤسسه‌ای ثبت‌نام کردی؟", reply_markup=kb)

@dp.message_handler(lambda message: message.from_user.id in user_data and 'موسسه' not in user_data[message.from_user.id])
async def step_8(message: types.Message):
    text = message.text
    if text == "سایر":
        await message.answer("لطفاً نام مؤسسه رو بنویس:")
    else:
        user_data[message.from_user.id]['موسسه'] = text
        await message.answer("میانگین استفاده‌ت از فضای مجازی در روز چند ساعته؟")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'موسسه' in user_data[message.from_user.id] and 'فضای مجازی' not in user_data[message.from_user.id] and message.text.isdigit())
async def step_9(message: types.Message):
    user_data[message.from_user.id]['فضای مجازی'] = int(message.text)
    if int(message.text) > 3:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("تلگرام","اینستاگرام","یوتیوب","سایر")
        await message.answer("بیشتر زمانت رو در چه برنامه‌ای می‌گذرونی؟", reply_markup=kb)
    else:
        await message.answer("در چه شهر و استانی درس می‌خونی؟")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'فضای مجازی' in user_data[message.from_user.id] and 'برنامه اصلی' not in user_data[message.from_user.id])
async def step_10(message: types.Message):
    if message.text in ["تلگرام","اینستاگرام","یوتیوب","سایر"]:
        user_data[message.from_user.id]['برنامه اصلی'] = message.text
        await message.answer("در چه شهر و استانی درس می‌خونی؟")
    else:
        user_data[message.from_user.id]['برنامه اصلی'] = message.text
        await message.answer("در چه شهر و استانی درس می‌خونی؟")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'شهر' not in user_data[message.from_user.id])
async def step_11(message: types.Message):
    user_data[message.from_user.id]['شهر'] = message.text
    await message.answer("اگر یادداشت یا توضیح خاصی داری بنویس (اختیاری):")

@dp.message_handler(lambda message: message.from_user.id in user_data and 'یادداشت' not in user_data[message.from_user.id])
async def step_12(message: types.Message):
    user_data[message.from_user.id]['یادداشت'] = message.text
    data = user_data[message.from_user.id]
    text = f"📋 فرم جدید مشاوره\n👤 نام: {data['نام']}\n📚 رشته: {data['رشته']}\n🎓 پایه: {data['پایه']}\n📞 آیدی: {data['آیدی']}\n🕒 ساعت مطالعه: {data.get('ساعت مطالعه','-')}\n🏫 موسسه: {data.get('موسسه','-')}\n📱 فضای مجازی: {data.get('فضای مجازی','-')} ساعت\n💻 برنامه اصلی: {data.get('برنامه اصلی','-')}\n🏙️ شهر/استان: {data.get('شهر','-')}\n📝 یادداشت: {data.get('یادداشت','-')}"
    for admin in ADMINS:
        await bot.send_message(admin, text)
    await message.answer(f"✅ اطلاعاتت با موفقیت ثبت شد.\nبه‌زودی مشاورت باهات تماس می‌گیره ✨\n{VIDEO_LINK}")

executor.start_polling(dp, skip_updates=True)
