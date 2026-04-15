# bot.py
import asyncio
import logging
import json
import sqlite3
import aiosqlite
from datetime import datetime
import os
from typing import Dict, List, Optional
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import openai
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

openai.api_key = OPENAI_API_KEY

# Database
DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                ban_date TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# States
class SupportStates(StatesGroup):
    waiting_stars = State()

# Helper Functions
async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

async def add_user(user_id: int, username: str, first_name: str, last_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, join_date, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (user_id, username, first_name, last_name, datetime.now().isoformat()))
        await db.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_users', 1) ON CONFLICT(key) DO UPDATE SET value = value + 1")
        await db.commit()

async def get_stats() -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        active_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM banned_users")
        banned_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT SUM(value) FROM stats WHERE key = 'messages_received'")
        messages = (await cursor.fetchone())[0] or 0
        
        return {
            "active_users": active_users,
            "banned_users": banned_count,
            "messages_received": messages
        }

async def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

async def add_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def get_admins() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admins")
        return [row[0] for row in await cursor.fetchall()]

async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO banned_users (user_id, ban_date) VALUES (?, ?)", 
                        (user_id, datetime.now().isoformat()))
        await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def increment_messages():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('messages_received', 1) ON CONFLICT(key) DO UPDATE SET value = value + 1")
        await db.commit()

# OpenAI Chat
async def chat_with_gpt(message: str, user_id: int) -> str:
    try:
        increment_messages()
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "أنت مساعد ذكي ومختصر. رد بالعربية فقط، كن مفيداً وسريعاً."
                },
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "عذراً، حدث خطأ في الخادم. حاول مرة أخرى لاحقاً."

# Keyboards
def get_start_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 قناة بلاك", url="https://t.me/rrr6zzz"),
            InlineKeyboardButton(text="💻 المطور بلاگ ١", url="https://t.me/rrr7zzz")
        ],
        [InlineKeyboardButton(text="⭐ دعم المطور", callback_data="support_stars")]
    ])
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 بث للجميع", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="🚫 حظر", callback_data="admin_ban"),
            InlineKeyboardButton(text="✅ فك الحظر", callback_data="admin_unban")
        ],
        [
            InlineKeyboardButton(text="👨‍💼 الأدمنية", callback_data="admin_list")
        ]
    ])
    return keyboard

# Handlers
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    if await is_banned(user_id):
        await message.answer("❌ أنت محظور من استخدام البوت.")
        return
    
    await add_user(user_id, username, first_name, last_name)
    
    text = "🤖 مرحباً في بوت الذكاء الاصطناعي المتطور"
    await message.answer(text, reply_markup=get_start_keyboard())
    
    if await is_admin(user_id):
        await message.answer("🔧 لوحة التحكم:", reply_markup=get_admin_keyboard())

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    stats = await get_stats()
    text = f"""
📊 إحصائيات البوت:
👥 المستخدمين النشطين: {stats['active_users']}
🚫 المحظورين: {stats['banned_users']}
💬 الرسائل المستلمة: {stats['messages_received']}
    """
    await message.answer(text)

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    try:
        target_id = int(message.text.split()[1])
        await ban_user(target_id)
        await message.answer(f"✅ تم حظر المستخدم {target_id}")
    except:
        await message.answer("❌ خطأ في الأمر. استخدم: /ban <user_id>")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    try:
        target_id = int(message.text.split()[1])
        await unban_user(target_id)
        await message.answer(f"✅ تم فك حظر المستخدم {target_id}")
    except:
        await message.answer("❌ خطأ في الأمر. استخدم: /unban <user_id>")

@dp.message(Command("promote"))
async def cmd_promote(message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    try:
        target_id = int(message.text.split()[1])
        await add_admin(target_id)
        await message.answer(f"✅ تم رفع {target_id} للأدمن")
    except:
        await message.answer("❌ خطأ في الأمر. استخدم: /promote <user_id>")

@dp.message(Command("admins"))
async def cmd_admins(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    admins = await get_admins()
    text = "👨‍💼 قائمة الأدمنية:\n" + "\n".join([f"• {admin_id}" for admin_id in admins])
    await message.answer(text)

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    await message.answer("📢 أرسل الرسالة التي تريد بثها للجميع:")
    
    @dp.message(F.text)
    async def process_broadcast(m: Message):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE is_active = 1")
            users = await cursor.fetchall()
        
        success = 0
        for (uid,) in users:
            try:
                await bot.send_message(uid, m.text)
                success += 1
                await asyncio.sleep(0.05)
            except:
                continue
        
        await m.answer(f"✅ تم إرسال الرسالة لـ {success} مستخدم")
        await dp.current().storage.delete_state(m.chat.id)

@dp.callback_query(F.data == "support_stars")
async def support_stars(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("⭐ أرسل عدد النجوم التي تريد دعم المطور بها (مثال: 10):")
    await state.set_state(SupportStates.waiting_stars)
    await callback.answer()

@dp.message(SupportStates.waiting_stars)
async def process_stars(message: Message, state: FSMContext):
    try:
        stars = int(message.text)
        if stars < 1:
            await message.answer("❌ يجب أن يكون العدد أكبر من 0")
            return
        
        payload = f"stars_{message.from_user.id}_{int(datetime.now().timestamp())}"
        
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="دعم المطور ⭐",
            description=f"دعم المطور بـ {stars} نجمة",
            payload=payload,
            provider_token="",  # Railway will handle this
            currency="XTR",
            prices=[LabeledPrice(label="الدعم", amount=stars)],
            start_parameter="support"
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ أرسل رقم صحيح فقط")
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await message.answer("❌ خطأ في إنشاء الفاتورة")

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: CallbackQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    await message.answer("✅ شكراً لدعمك! تم استلام الدفع بنجاح ⭐")

@dp.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        await callback.answer("❌ ليس لديك صلاحيات")
        return
    
    data = callback.data
    if data == "admin_stats":
        stats = await get_stats()
        text = f"""
📊 إحصائيات البوت:
👥 المستخدمين النشطين: {stats['active_users']}
🚫 المحظورين: {stats['banned_users']}
💬 الرسائل المستلمة: {stats['messages_received']}
        """
        await callback.message.answer(text)
    
    elif data == "admin_broadcast":
        await callback.message.answer("📢 أرسل الرسالة التي تريد بثها:")
    
    await callback.answer()

# Chat Handler
@dp.message(F.text & ~Command("start", "stats", "ban", "unban", "promote", "admins", "broadcast"))
async def handle_chat(message: Message):
    user_id = message.from_user.id
    
    if await is_banned(user_id):
        await message.answer("❌ أنت محظور من استخدام البوت.")
        return
    
    await message.answer("🤖 يفكر...")
    
    response = await chat_with_gpt(message.text, user_id)
    await message.answer(response)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
