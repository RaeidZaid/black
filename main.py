import os
import json
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

# ================= الإعدادات =================
API_TOKEN = os.getenv('API_TOKEN', '7227340595:AAE0ps5m0aRZk3zusLdVctS03ZmE4w8w8PM')
ADMIN_ID = int(os.getenv('ADMIN_ID', 81522084))

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

DATA_FILE = "bot_data.json"

# ================= التخزين =================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"custom_buttons": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ================= الحالات (FSM) =================
class BotStates(StatesGroup):
    waiting_for_button_name = State()
    waiting_for_button_emoji = State()
    waiting_for_button_style = State()

# ================= بناء الكيبورد الثابت =================
def get_main_keyboard():
    data = load_data()
    
    # الزر الأساسي للمطور
    keyboard = [
        [KeyboardButton(text="إضافة زر جديد")]
    ]
    
    # بناء الأزرار المخصصة التي صنعها المطور
    custom_buttons_row = []
    for btn in data.get("custom_buttons", []):
        btn_kwargs = {"text": btn["name"]}
        
        # 1. إضافة الرمز المميز (Premium) إن وُجد، أو الرمز العادي
        if btn.get("custom_emoji_id"):
            btn_kwargs["icon_custom_emoji_id"] = btn["custom_emoji_id"]
        elif btn.get("regular_emoji"):
            btn_kwargs["text"] = f"{btn['regular_emoji']} {btn['name']}"
            
        # 2. إضافة اللون (Style) إن وُجد
        if btn.get("style") and btn["style"] != "default":
            btn_kwargs["style"] = btn["style"]
            
        custom_buttons_row.append(KeyboardButton(**btn_kwargs))
        
        # ترتيب الأزرار: زرين في كل صف
        if len(custom_buttons_row) == 2:
            keyboard.append(custom_buttons_row)
            custom_buttons_row = []
            
    if custom_buttons_row:
        keyboard.append(custom_buttons_row)
        
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True # هذه الخاصية تمنع اختفاء الكيبورد تماماً
    )

# ================= أوامر البداية والإلغاء =================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("مرحباً عزيزي المطور! الكيبورد السفلي ثابت الآن ويدعم الألوان والرموز المميزة.", reply_markup=get_main_keyboard())

@dp.message(F.text == "الغاء")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("تم الإلغاء.", reply_markup=get_main_keyboard())

# ================= مسار إضافة الزر =================
@dp.message(F.text == "إضافة زر جديد")
async def add_custom_button_cmd(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    # نزيل الكيبورد مؤقتاً أثناء إدخال البيانات لعدم التشتت
    await message.answer("أرسل الآن **اسم الزر** الذي تريده (مثال: طلباتي):\n\nللإلغاء أرسل (الغاء)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(BotStates.waiting_for_button_name)

@dp.message(BotStates.waiting_for_button_name)
async def process_button_name(message: Message, state: FSMContext):
    if message.text == "الغاء": return
    btn_name = message.text.strip()
    
    await state.update_data(btn_name=btn_name)
    await message.answer(f"الاسم: '{btn_name}'.\nالآن أرسل **الإيموجي المميز (Premium)** أو إيموجي عادي:\n\nللإلغاء أرسل (الغاء)")
    await state.set_state(BotStates.waiting_for_button_emoji)

@dp.message(BotStates.waiting_for_button_emoji)
async def process_button_emoji(message: Message, state: FSMContext):
    if message.text == "الغاء": return
    
    custom_emoji_id = None
    regular_emoji = None
    
    # التقاط الرمز المميز
    if message.entities:
        for ent in message.entities:
            if ent.type == "custom_emoji":
                custom_emoji_id = ent.custom_emoji_id
                break
                
    if not custom_emoji_id:
        regular_emoji = message.text.strip()
        
    await state.update_data(custom_emoji_id=custom_emoji_id, regular_emoji=regular_emoji)
    
    # قائمة الألوان لاختيار لون الزر
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1- احمر"), KeyboardButton(text="2- اخضر")],
            [KeyboardButton(text="3- ازرق"), KeyboardButton(text="4- افتراضي")],
            [KeyboardButton(text="الغاء")]
        ],
        resize_keyboard=True
    )
    
    text_msg = (
        "حسنا ارسل لي اسم اللون الذي تريده للزر\n"
        "الاختيارات المتاحة:\n\n"
        "1- احمر (Danger)\n"
        "2- اخضر (Success)\n"
        "3- ازرق (Primary)\n"
        "4- افتراضي\n\n"
        "للإلغاء ارسل (الغاء)"
    )
    await message.answer(text_msg, reply_markup=markup)
    await state.set_state(BotStates.waiting_for_button_style)

@dp.message(BotStates.waiting_for_button_style)
async def process_button_style(message: Message, state: FSMContext):
    if message.text == "الغاء": return
    text = message.text
    
    style = "default"
    if "احمر" in text: style = "danger"
    elif "اخضر" in text: style = "success"
    elif "ازرق" in text: style = "primary"
    
    user_data = await state.get_data()
    new_btn = {
        "name": user_data["btn_name"],
        "custom_emoji_id": user_data.get("custom_emoji_id"),
        "regular_emoji": user_data.get("regular_emoji"),
        "style": style
    }
    
    data = load_data()
    # لتحديث الزر إذا كان موجوداً مسبقاً بنفس الاسم
    data["custom_buttons"] = [b for b in data.get("custom_buttons", []) if b["name"] != new_btn["name"]]
    data["custom_buttons"].append(new_btn)
    save_data(data)
    
    await state.clear()
    await message.answer("تم إنشاء الزر الملون وتثبيت الكيبورد بنجاح! ✅", reply_markup=get_main_keyboard())

# ================= الردود على الأزرار المخصصة =================
@dp.message()
async def handle_custom_button_clicks(message: Message):
    data = load_data()
    for btn in data.get("custom_buttons", []):
        
        # إذا كان الإيموجي عادي، فهو مدمج في النص، أما المميز فالنص يصل بدونه
        if btn.get("regular_emoji"):
            expected_text = f"{btn['regular_emoji']} {btn['name']}".strip()
        else:
            expected_text = btn['name']
            
        if message.text == expected_text:
            await message.answer(f"لقد ضغطت للتو على الزر: {btn['name']}", reply_markup=get_main_keyboard())
            return
            
async def main():
    print("Bot is starting perfectly...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
