@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID, content_types=['text', 'audio', 'document', 'photo', 'sticker', 'video', 'video_note', 'voice', 'location', 'contact', 'animation'])
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
    elif text == "تغير لون":
        msg = bot.send_message(ADMIN_ID, "• حسناً عزيزي المطور ارسل نص الزر الذي تريد تعديل لونة", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_button_name_for_color)
    elif text == "اضف رمز مميز":
        msg = bot.send_message(ADMIN_ID, "• حسناً عزيزي المطور ارسل نص الزر الذي تريد اضافة له ايموجي", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_button_name_for_emoji)
        
    # نظام الرد المطور على المستخدمين (يدعم الوسائط وتجاوز الخصوصية)
    elif message.reply_to_message:
        # البحث عن ID المستخدم المرتبط بالرسالة
        target_id = Redis.get(f"reply_to:{message.reply_to_message.message_id}")
        
        # كإجراء احتياطي، المحاولة من توجيه الرسالة
        if not target_id and message.reply_to_message.forward_from:
            target_id = message.reply_to_message.forward_from.id
            
        if target_id:
            target_id = int(target_id)
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
                
                bot.send_message(message.chat.id, "تم ارسال رسالتك للمستخدم بنجاح ✅", reply_to_message_id=message.message_id)
            except Exception as e:
                bot.send_message(message.chat.id, "تعذر ارسال الرد، ربما قام المستخدم بحظر البوت.", reply_to_message_id=message.message_id)
        else:
            if message.content_type == 'text':
                bot.send_message(ADMIN_ID, "استخدم الاوامر من الكيبورد", reply_markup=admin_keyboard())
    else:
        if message.content_type == 'text':
            bot.send_message(ADMIN_ID, "استخدم الاوامر من الكيبورد", reply_markup=admin_keyboard())
