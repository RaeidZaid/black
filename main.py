import telebot
import json
import os
from telebot import types

API_TOKEN = '7227340595:AAE0ps5m0aRZk3zusLdVctS03ZmE4w8w8PM'
ADMIN_ID = 81522084

bot = telebot.TeleBot(API_TOKEN)

BUTTON_STYLES_FILE = "button_styles.json"
admin_sessions = {}

def load_button_styles():
    if os.path.exists(BUTTON_STYLES_FILE):
        try:
            with open(BUTTON_STYLES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_button_styles(styles):
    with open(BUTTON_STYLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(styles, f, ensure_ascii=False, indent=4)

# ==========================================
# دالة ذكية لإنشاء الأزرار الملونة وبها إيموجي
# استخدمها دائماً عند إنشاء أي زر شفاف (Inline)
# ==========================================
def create_styled_inline_button(text, callback_data):
    styles = load_button_styles()
    btn_kwargs = {'text': text, 'callback_data': callback_data}
    
    if text in styles:
        if 'style' in styles[text]:
            btn_kwargs['style'] = styles[text]['style']
        if 'icon_custom_emoji_id' in styles[text]:
            btn_kwargs['icon_custom_emoji_id'] = styles[text]['icon_custom_emoji_id']
            
    return types.InlineKeyboardButton(**btn_kwargs)

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("تغير لون"), types.KeyboardButton("اضف رمز مميز"))
        
        # مثال على كيفية عرض زر ملون للوحة الشفافة لتجربة ما قمت بتصميمه
        inline_markup = types.InlineKeyboardMarkup()
        test_btn = create_styled_inline_button("زر التجربة", "test_callback")
        inline_markup.add(test_btn)
        
        bot.send_message(message.chat.id, "مرحباً عزيزي المطور، استخدم الأزرار أدناه لتخصيص البوت:", reply_markup=markup)
        bot.send_message(message.chat.id, "هذا زر تجريبي لمعاينة الألوان والرموز:", reply_markup=inline_markup)

# ================= ( قسم تغيير اللون ) =================
@bot.message_handler(func=lambda msg: msg.text == "تغير لون" and msg.from_user.id == ADMIN_ID)
def change_color_start(message):
    msg = bot.send_message(message.chat.id, "• حسناً عزيزي المطور ارسل نص الزر الذي تريد تعديل لونة")
    bot.register_next_step_handler(msg, process_button_name_for_color)

def process_button_name_for_color(message):
    if message.text == "الغاء الامر": return
    
    button_name = message.text
    admin_sessions[message.from_user.id] = {'action': 'color', 'button': button_name}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("• اللون الاحمر 🔴", callback_data="setcolor_danger"),
        types.InlineKeyboardButton("• اللون الاخضر 🟢", callback_data="setcolor_success"),
        types.InlineKeyboardButton("• اللون الازرق 🔵", callback_data="setcolor_primary"),
        types.InlineKeyboardButton("• اللون الافتراضي ⚪", callback_data="setcolor_default"),
        types.InlineKeyboardButton("• حذف اللون", callback_data="setcolor_remove"),
        types.InlineKeyboardButton("• الغاء الامر", callback_data="setcolor_cancel")
    )
    bot.send_message(message.chat.id, f"• حسناً عزيزي اختار اللون المناسب للأزرار التي فيها نص :\n- {button_name}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcolor_"))
def color_callback(call):
    user_id = call.from_user.id
    color_choice = call.data.split("_")[1]
    
    if color_choice == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        admin_sessions.pop(user_id, None)
        return
        
    session_data = admin_sessions.get(user_id)
    if not session_data or session_data['action'] != 'color':
        bot.answer_callback_query(call.id, "انتهت الجلسة، أعد المحاولة.", show_alert=True)
        return
        
    button_name = session_data['button']
    styles = load_button_styles()
    
    if button_name not in styles:
        styles[button_name] = {}
        
    if color_choice in ["remove", "default"]:
        if 'style' in styles[button_name]:
            del styles[button_name]['style']
        bot.answer_callback_query(call.id, "تم إرجاع اللون الافتراضي.", show_alert=True)
    else:
        # الألوان الرسمية من تيليجرام: primary, success, danger
        styles[button_name]['style'] = color_choice
        bot.answer_callback_query(call.id, "تم حفظ إعداد اللون بنجاح.", show_alert=True)
        
    save_button_styles(styles)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_sessions.pop(user_id, None)

# ================= ( قسم الرموز المميزة ) =================
@bot.message_handler(func=lambda msg: msg.text == "اضف رمز مميز" and msg.from_user.id == ADMIN_ID)
def add_emoji_start(message):
    msg = bot.send_message(message.chat.id, "• حسناً عزيزي المطور ارسل نص الزر الذي تريد اضافة له ايموجي")
    bot.register_next_step_handler(msg, process_button_name_for_emoji)

def process_button_name_for_emoji(message):
    if message.text == "الغاء الامر": return
    button_name = message.text
    msg = bot.send_message(message.chat.id, "• حسناً عزيزي المطور ارسل الايموجي المميز الان (كـ Premium Emoji)")
    bot.register_next_step_handler(msg, save_emoji_to_button, button_name)

def save_emoji_to_button(message, button_name):
    custom_emoji_id = None
    
    # التقاط الـ ID الخاص بالإيموجي المميز من رسالتك
    if message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
                
    if not custom_emoji_id:
        bot.send_message(message.chat.id, "عذراً، يجب أن ترسل إيموجي مميز (Premium Emoji) ليتمكن البوت من استخراج المعرف الخاص به.")
        return
        
    styles = load_button_styles()
    if button_name not in styles:
        styles[button_name] = {}
        
    styles[button_name]['icon_custom_emoji_id'] = custom_emoji_id
    save_button_styles(styles)
    bot.send_message(message.chat.id, f"تم بنجاح ربط الرمز المميز بالزر: {button_name}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
