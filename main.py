import telebot, json, webbrowser, re, requests, sqlite3, redis, os
from telebot import types

API_TOKEN = '7227340595:AAE0ps5m0aRZk3zusLdVctS03ZmE4w8w8PM'
ADMIN_ID = 81522084

bot = telebot.TeleBot(API_TOKEN)
Redis = redis.Redis(host='localhost', port=6379, decode_responses=True)

USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
TWASL_BANNED_FILE = "twasl_banned.json"

def load_users_data():
    users = set()
    banned = set()
    twasl_banned = set()
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = set(json.load(f))
        except:
            users = set()
    if os.path.exists(BANNED_FILE):
        try:
            with open(BANNED_FILE, 'r', encoding='utf-8') as f:
                banned = set(json.load(f))
        except:
            banned = set()
    if os.path.exists(TWASL_BANNED_FILE):
        try:
            with open(TWASL_BANNED_FILE, 'r', encoding='utf-8') as f:
                twasl_banned = set(json.load(f))
        except:
            twasl_banned = set()
    return users, banned, twasl_banned

def save_users_data(users, banned, twasl_banned):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(users), f, ensure_ascii=False)
    with open(BANNED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(banned), f, ensure_ascii=False)
    with open(TWASL_BANNED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(twasl_banned), f, ensure_ascii=False)

users, blocked_users, twasl_blocked = load_users_data()

def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            channel_username TEXT PRIMARY KEY,
            channel_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_subscription_channels():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_username, channel_name FROM subscriptions')
    channels = cursor.fetchall()
    conn.close()
    return channels

def add_subscription_channel(channel_username, channel_name):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO subscriptions (channel_username, channel_name) 
        VALUES (?, ?)
    ''', (channel_username, channel_name))
    conn.commit()
    conn.close()

def remove_subscription_channel(channel_username):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscriptions WHERE channel_username = ?', (channel_username,))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    channels = get_subscription_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            chat_member = bot.get_chat_member(channel[0], user_id)
            if chat_member.status not in ['creator', 'administrator', 'member']:
                return False
        except:
            return False
    return True

def create_subscription_keyboard():
    channels = get_subscription_channels()
    keyboard = types.InlineKeyboardMarkup()
    for channel in channels:
        clean_username = channel[0].replace('@', '')
        keyboard.add(types.InlineKeyboardButton(text=f" {channel[1]}", url=f"https://t.me/{clean_username}"))
    keyboard.add(types.InlineKeyboardButton(text="تحقق من الاشتراك", callback_data="check_sub"))
    return keyboard

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("قائمة المستخدمين"), types.KeyboardButton("حظر عضو"))
    markup.add(types.KeyboardButton("اذاعة للكل"), types.KeyboardButton("فك حظر"))
    markup.add(types.KeyboardButton("اضافة قناة"), types.KeyboardButton("حذف قناة"))
    markup.add(types.KeyboardButton("قنوات الاشتراك"), types.KeyboardButton("الاحصائيات"))
    markup.add(types.KeyboardButton("تفعيل التواصل"), types.KeyboardButton("تعطيل التواصل"))
    markup.add(types.KeyboardButton("تغيير رد ستارت"), types.KeyboardButton("تغيير رد التواصل"))
    markup.add(types.KeyboardButton("اظهار رد التواصل"), types.KeyboardButton("اخفاء رد التواصل"))
    markup.add(types.KeyboardButton("حظر تواصل"), types.KeyboardButton("الغاء حظر تواصل"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or ""
    
    if user_id == ADMIN_ID:
        bot.send_message(user_id, "مرحباً عزيزي المطور", reply_markup=admin_keyboard())
        return
        
    if user_id in blocked_users:
        bot.send_message(user_id, "عذراً، أنت محظور من استخدام البوت.")
        return
        
    if user_id not in users:
        users.add(user_id)
        save_users_data(users, blocked_users, twasl_blocked)
        try:
            url = f"https://api.telegram.org/bot{API_TOKEN}/getChat?chat_id={user_id}"
            res = requests.get(url).json()
            username = "لا يوجد"
            if res.get('ok') and res.get('result'):
                if res['result'].get('username'):
                    username = "@" + res['result']['username']
            is_premium = "مميز" if message.from_user.is_premium else "عادي"
            admin_info = bot.get_chat(ADMIN_ID)
            admin_name = admin_info.first_name or "المطور"
            notify_text = f"مرحبا عزيزي المطور : <a href='tg://user?id={ADMIN_ID}'>{admin_name}</a>\n"
            notify_text += f"لديك مشترك جديد\n"
            notify_text += f"اسمه : <a href='tg://user?id={user_id}'>{name}</a>\n"
            notify_text += f"يوزره : {username}\n"
            notify_text += f"ايديه : {user_id}\n"
            notify_text += f"نوع حسابه : {is_premium}"
            bot.send_message(ADMIN_ID, notify_text, parse_mode='HTML')
        except:
            pass
            
    if not check_subscription(user_id) and user_id != ADMIN_ID:
        bot.send_message(user_id, "يجب الاشتراك في القنوات التالية أولا\n\nبعد الاشتراك اضغط على زر التحقق", reply_markup=create_subscription_keyboard())
        return
        
    start_msg = Redis.get("StartMsg") or "مرحباً: #الاسم\nارسل رسالتك الى الدعم وسيتم الرد عليك"
    start_msg = start_msg.replace("#الاسم", name)
    start_msg = start_msg.replace("#اليوزر", username if 'username' in locals() else "لا يوجد")
    start_msg = start_msg.replace("#الايدي", str(user_id))
    bot.send_message(user_id, start_msg, reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID)
def handle_user_messages(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or ""
    
    if user_id in blocked_users:
        bot.send_message(user_id, "عذراً، أنت محظور من استخدام البوت.")
        return
        
    if user_id in twasl_blocked:
        bot.send_message(user_id, "عذراً، أنت محظور من التواصل.")
        return
        
    if user_id not in users:
        users.add(user_id)
        save_users_data(users, blocked_users, twasl_blocked)
        
    if not check_subscription(user_id) and user_id != ADMIN_ID:
        bot.send_message(user_id, "يجب الاشتراك في القنوات أولاً", reply_markup=create_subscription_keyboard())
        return
        
    if Redis.get("TwaslBot") != "true":
        return
        
    try:
        forwarded = bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        if forwarded:
            Redis.setex(f"Twasl:UserId{message.date}", 172800, user_id)
            Redis.setex(f"Twasl:UserName{message.date}", 172800, name)
            bot.send_message(ADMIN_ID, f"المستخدم : <a href='tg://user?id={user_id}'>{name}</a>", parse_mode='HTML', reply_to_message_id=forwarded.message_id)
    except:
        pass
        
    if Redis.get("ShowReplyMsg") == "true":
        reply_msg = Redis.get("TwaslReplyMsg") or "تم ارسال رسالتك للمطور"
        bot.send_message(message.chat.id, reply_msg, reply_to_message_id=message.message_id)

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_commands(message):
    text = message.text or ""
    user_id = message.from_user.id
    
    if text == "قائمة المستخدمين":
        bot.send_message(ADMIN_ID, f"عدد المشتركين الحالي: {len(users)}", reply_markup=admin_keyboard())
    elif text == "الاحصائيات":
        stats = f"إجمالي المستخدمين: {len(users)}\nالمحظورين: {len(blocked_users)}\nمحظوري التواصل: {len(twasl_blocked)}\nقنوات الاشتراك: {len(get_subscription_channels())}"
        bot.send_message(ADMIN_ID, stats, reply_markup=admin_keyboard())
    elif text == "حظر عضو":
        msg = bot.send_message(ADMIN_ID, "ارسل ايدي الشخص المراد حظره:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_block)
    elif text == "فك حظر":
        msg = bot.send_message(ADMIN_ID, "ارسل ايدي الشخص لفك حظره:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_unblock)
    elif text == "حظر تواصل":
        msg = bot.send_message(ADMIN_ID, "ارسل ايدي الشخص المراد حظره من التواصل:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_twasl_block)
    elif text == "الغاء حظر تواصل":
        msg = bot.send_message(ADMIN_ID, "ارسل ايدي الشخص لفك حظره من التواصل:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_twasl_unblock)
    elif text == "اذاعة للكل":
        msg = bot.send_message(ADMIN_ID, "ارسل نص الاذاعة الان:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_broadcast)
    elif text == "اضافة قناة":
        msg = bot.send_message(ADMIN_ID, "ارسل يوزر القناة مع @:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_add_channel)
    elif text == "حذف قناة":
        channels = get_subscription_channels()
        if not channels:
            bot.send_message(ADMIN_ID, "لا توجد قنوات مضافة.", reply_markup=admin_keyboard())
            return
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        for ch in channels:
            markup.add(types.KeyboardButton(f"حذف {ch[0]}"))
        markup.add(types.KeyboardButton("الغاء"))
        msg = bot.send_message(ADMIN_ID, "اضغط على اسم القناة للحذف:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_remove_channel)
    elif text == "قنوات الاشتراك":
        channels = get_subscription_channels()
        if not channels:
            bot.send_message(ADMIN_ID, "لا توجد قنوات مضافة.", reply_markup=admin_keyboard())
            return
        msg_text = "القنوات المضافة للاشتراك الإجباري\n\n"
        for i, (ch_username, ch_name) in enumerate(channels, 1):
            msg_text += f"{i}. {ch_username} - {ch_name}\n"
        bot.send_message(ADMIN_ID, msg_text, reply_markup=admin_keyboard())
    elif text == "تفعيل التواصل":
        Redis.set("TwaslBot", "true")
        bot.send_message(ADMIN_ID, "تم تفعيل التواصل", reply_markup=admin_keyboard())
    elif text == "تعطيل التواصل":
        Redis.set("TwaslBot", "false")
        bot.send_message(ADMIN_ID, "تم تعطيل التواصل", reply_markup=admin_keyboard())
    elif text == "تغيير رد ستارت":
        msg = bot.send_message(ADMIN_ID, "ارسل نص رد ستارت الجديد\nالمتغيرات: #الاسم #اليوزر #الايدي", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_change_start)
    elif text == "تغيير رد التواصل":
        msg = bot.send_message(ADMIN_ID, "ارسل نص رد التواصل الجديد", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_change_reply)
    elif text == "اظهار رد التواصل":
        Redis.set("ShowReplyMsg", "true")
        bot.send_message(ADMIN_ID, "تم اظهار رد التواصل", reply_markup=admin_keyboard())
    elif text == "اخفاء رد التواصل":
        Redis.set("ShowReplyMsg", "false")
        bot.send_message(ADMIN_ID, "تم اخفاء رد التواصل", reply_markup=admin_keyboard())
    elif message.reply_to_message and message.reply_to_message.forward_from:
        target_id = message.reply_to_message.forward_from.id
        target_name = message.reply_to_message.forward_from.first_name or ""
        if target_id in twasl_blocked:
            bot.send_message(message.chat.id, "هذا المستخدم محظور من التواصل", reply_to_message_id=message.message_id)
            return
        try:
            if message.content_type == 'text':
                bot.send_message(target_id, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(target_id, message.photo[-1].file_id, caption=message.caption or "")
            elif message.content_type == 'video':
                bot.send_video(target_id, message.video.file_id, caption=message.caption or "")
            elif message.content_type == 'document':
                bot.send_document(target_id, message.document.file_id, caption=message.caption or "")
            elif message.content_type == 'audio':
                bot.send_audio(target_id, message.audio.file_id, caption=message.caption or "")
            elif message.content_type == 'voice':
                bot.send_voice(target_id, message.voice.file_id)
            elif message.content_type == 'video_note':
                bot.send_video_note(target_id, message.video_note.file_id)
            elif message.content_type == 'sticker':
                bot.send_sticker(target_id, message.sticker.file_id)
            bot.send_message(message.chat.id, f"تم ارسال رسالتك اليه\nالمستخدم : <a href='tg://user?id={target_id}'>{target_name}</a>", parse_mode='HTML', reply_to_message_id=message.message_id)
        except:
            bot.send_message(message.chat.id, "تعذر ارسال الرد", reply_to_message_id=message.message_id)
    else:
        if message.content_type == 'text':
            bot.send_message(ADMIN_ID, "استخدم الاوامر من الكيبورد", reply_markup=admin_keyboard())

def process_change_start(message):
    Redis.set("StartMsg", message.text)
    bot.send_message(ADMIN_ID, "تم تغيير رد ستارت بنجاح", reply_markup=admin_keyboard())

def process_change_reply(message):
    Redis.set("TwaslReplyMsg", message.text)
    bot.send_message(ADMIN_ID, "تم تغيير رد التواصل بنجاح", reply_markup=admin_keyboard())

def process_block(message):
    try:
        target_id = int(message.text)
        blocked_users.add(target_id)
        save_users_data(users, blocked_users, twasl_blocked)
        bot.send_message(ADMIN_ID, f"تم حظر العضو {target_id} بنجاح", reply_markup=admin_keyboard())
    except:
        bot.send_message(ADMIN_ID, "ايدي غير صالح", reply_markup=admin_keyboard())

def process_unblock(message):
    try:
        target_id = int(message.text)
        blocked_users.discard(target_id)
        save_users_data(users, blocked_users, twasl_blocked)
        bot.send_message(ADMIN_ID, f"تم فك حظر العضو {target_id}", reply_markup=admin_keyboard())
    except:
        bot.send_message(ADMIN_ID, "ايدي غير صالح", reply_markup=admin_keyboard())

def process_twasl_block(message):
    try:
        target_id = int(message.text)
        twasl_blocked.add(target_id)
        save_users_data(users, blocked_users, twasl_blocked)
        bot.send_message(ADMIN_ID, f"تم حظر العضو {target_id} من التواصل", reply_markup=admin_keyboard())
    except:
        bot.send_message(ADMIN_ID, "ايدي غير صالح", reply_markup=admin_keyboard())

def process_twasl_unblock(message):
    try:
        target_id = int(message.text)
        twasl_blocked.discard(target_id)
        save_users_data(users, blocked_users, twasl_blocked)
        bot.send_message(ADMIN_ID, f"تم فك حظر العضو {target_id} من التواصل", reply_markup=admin_keyboard())
    except:
        bot.send_message(ADMIN_ID, "ايدي غير صالح", reply_markup=admin_keyboard())

def process_broadcast(message):
    count = 0
    text = message.text or ""
    for user in list(users):
        if user != ADMIN_ID:
            try:
                bot.send_message(user, text)
                count += 1
            except:
                continue
    bot.send_message(ADMIN_ID, f"تم ارسال الاذاعة لـ {count} مستخدم", reply_markup=admin_keyboard())

def process_add_channel(message):
    channel_input = message.text.strip()
    if not channel_input.startswith('@'):
        channel_input = '@' + channel_input
    try:
        chat_info = bot.get_chat(channel_input)
        channel_name = chat_info.title
        add_subscription_channel(channel_input, channel_name)
        bot.send_message(ADMIN_ID, f"تم اضافة القناة: {channel_input}", reply_markup=admin_keyboard())
    except:
        bot.send_message(ADMIN_ID, "لا يمكن العثور على القناة", reply_markup=admin_keyboard())

def process_remove_channel(message):
    text = message.text or ""
    if text == "الغاء":
        bot.send_message(ADMIN_ID, "تم الالغاء.", reply_markup=admin_keyboard())
        return
    m = re.match(r'حذف (.+)', text)
    if m:
        channel_input = m.group(1).strip()
        remove_subscription_channel(channel_input)
        bot.send_message(ADMIN_ID, f"تم حذف القناة: {channel_input}", reply_markup=admin_keyboard())
    else:
        bot.send_message(ADMIN_ID, "اختيار غير صالح.", reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_msg = Redis.get("StartMsg") or "مرحباً: #الاسم\nارسل رسالتك الى الدعم وسيتم الرد عليك"
            name = call.from_user.first_name or ""
            start_msg = start_msg.replace("#الاسم", name)
            bot.send_message(user_id, start_msg)
        else:
            bot.answer_callback_query(call.id, "لم تشترك بعد في جميع القنوات المطلوبة", show_alert=True)

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()
