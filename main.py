import telebot
from telebot import types

import os
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 2092515567
GROUP_CHAT_IDS = [-1003680070293, -1003720457902, -1003571310711]  # Bir nechta guruh ID
CHANNEL_USERNAME = "@Qorakoltalimmarkazi"
CHANNEL_LINK = "https://t.me/Qorakoltalimmarkazi"

bot = telebot.TeleBot(TOKEN)

MENU_BUTTONS = [
    "📝TOPSHIRIQLAR📝",
    "♻️TEST♻️",
    "📚KITOBLAR📚",
    "⤴️ORQAGA⤴️"
]
user_state = {}


# ===== /start komandasi =====
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup()
    join_button = types.InlineKeyboardButton("📖KANALGA OBUNA BO'LING📖", url=CHANNEL_LINK)
    check_button = types.InlineKeyboardButton("✅TASDIQLAYMAN✅", callback_data="check")
    markup.add(join_button)
    markup.add(check_button)

    bot.send_message(
        message.chat.id,
        "Botdan foydalanish uchun kanalga obuna bo‘ling.\n\nKeyin ✅TASDIQLAYMAN✅ tugmasini bosing.",
        reply_markup=markup
    )

# ===== Kanalga obuna tekshirish =====
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_subscription(call):
    user_id = call.from_user.id
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['member', 'administrator', 'creator']:
            bot.answer_callback_query(call.id, "Tasdiqlandi")
            bot.send_message(call.message.chat.id, "🔆Xush kelibsiz!🔆\nEndi menyudan birini tanlang.")
            show_main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "‼️Avval Kanalga obuna bo'ling‼️")
    except:
        bot.send_message(call.message.chat.id, "‼️Buyruqni takrorlang‼️")

# ===== Asosiy menyu =====
def show_main_menu(chat_id):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if chat_id == ADMIN_ID:
        menu.add("♻️TEST♻️")
        menu.add("⤴️ORQAGA⤴️")
    else:
        menu.add("📝TOPSHIRIQLAR📝")
        menu.add("♻️TEST♻️")
        menu.add("📚KITOBLAR📚")
        menu.add("⤴️ORQAGA⤴️")
    bot.send_message(chat_id, "Menyu tanlang:", reply_markup=menu)

# ===== Talaba TOPSHIRIQLAR menyusi =====
@bot.message_handler(func=lambda message: message.text == "📝TOPSHIRIQLAR📝")
def tasks_menu(message): 
    user_state[message.chat.id] = "task"
    bot.send_message(
        message.chat.id,
        "📝TOPSHIRIQLAR📝 shu yerga qabul qilindi xabari kelguncha yuboring.\nMatn yoki rasm bo‘lishi mumkin."
    )
# ===== Hozircha ishlamaydigan bo‘limlar =====
@bot.message_handler(func=lambda message: message.text in ["♻️TEST♻️", "📚KITOBLAR📚"])
def not_ready_sections(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ Hozircha faqat 📝TOPSHIRIQLAR📝 bo‘limi ishlayapti."
    )

# ===== Talaba topshiriqlari (matn yoki rasm) =====
@bot.message_handler(content_types=[
    'text',
    'photo',
    'voice',
    'video',
    'document',
    'audio'
])
def receive_task(message):

    if message.chat.type != 'private' or message.chat.id == ADMIN_ID:
        return

    # Menyu tugmalari bu yerga kirmaydi
    if message.content_type == 'text' and message.text in MENU_BUTTONS:
        return

    # Kanalga obuna tekshirish
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, message.chat.id).status
        if status not in ['member', 'administrator', 'creator']:
            bot.send_message(
                message.chat.id,
                "‼️ Avval /start bosib kanalga obuna bo‘ling ‼️"
            )
            return
    except:
        bot.send_message(message.chat.id, "‼️ Buyruqni takrorlang ‼️")
        return

    # MENYU TANLANMAGAN BO‘LSA — HAR QANDAY XABARDA
    if user_state.get(message.chat.id) != "task":
        bot.send_message(
            message.chat.id,
            "‼️Avval menyudan tanlang‼️"
        )
        return

    # === SHU YERDAN BOSHLAB HAQIQIY TOPSHIRIQ ===

    first_name = message.from_user.first_name

    bot.send_message(
        message.chat.id,
        "📝 TOPSHIRIQ qabul qilindi.\nTekshiruv kutilmoqda. Javob kelmasa, birozdan takror yuboring!"
    )

    # State tozalash
    user_state.pop(message.chat.id, None)

    # Adminga yuborish
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "✅ To‘g‘ri. Ofaring",
            callback_data=f"correct_{message.chat.id}_{first_name}"
        ),
        types.InlineKeyboardButton(
            "❌ Noto‘g‘ri. Takror bajaring",
            callback_data=f"wrong_{message.chat.id}_{first_name}"
        )
    )

    if message.content_type == 'text':
        bot.send_message(
            ADMIN_ID,
            f"✍️ Matnli topshiriq\n{first_name}\n🆔 {message.chat.id}\n\n{message.text}",
            reply_markup=markup
        )

    elif message.content_type == 'photo':
        bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=f"📸 Rasmli topshiriq\n{first_name}\n🆔 {message.chat.id}",
            reply_markup=markup
        )
    
    elif message.content_type == 'video':
        bot.send_video(
            ADMIN_ID,
            message.video[-1].file_id,
            caption=f"🎥 Video topshiriq\n{first_name}\n🆔 {message.chat.id}",
            reply_markup=markup
        )

    elif message.content_type == 'audio':
        bot.send_audio(
            ADMIN_ID,
            message.audio[-1].file_id,
            caption=f"🎥 Audio topshiriq\n{first_name}\n🆔 {message.chat.id}",
            reply_markup=markup
        )
    
    elif message.content_type == 'round':
        bot.send_round(
            ADMIN_ID,
            message.round[-1].file_id,
            caption=f"🎥 Round topshiriq\n{first_name}\n🆔 {message.chat.id}",
            reply_markup=markup
        )
    

    elif message.content_type == 'video_note':
        bot.send_video_note(
           ADMIN_ID,
           message.video_note.file_id,
           reply_markup=markup
        )

    elif message.content_type == 'document':
        bot.send_document(
           ADMIN_ID,
           message.document.file_id,
           caption=f"📎 Fayl topshiriq\n{first_name}\n🆔 {message.chat.id}",
           reply_markup=markup
        )

# ===== Admin tugmani bosganda javob va guruhlarga xabar =====
@bot.callback_query_handler(func=lambda call: call.data.startswith(("correct_", "wrong_")))
def handle_result(call):
    data_parts = call.data.split("_")
    target_id = int(data_parts[1])
    first_name = data_parts[2]

    if call.data.startswith("correct_"):
        bot.send_message(target_id, "✅ Sizning javobingiz to‘g‘ri. Ofaring!")

        for group_id in GROUP_CHAT_IDS:
            try:
                status = bot.get_chat_member(group_id, target_id).status
                if status in ['member', 'administrator', 'creator']:
                    bot.send_message(group_id, f"✅ Talaba {first_name} topshiriqni to‘g‘ri bajardi. Ofarin!")
            except:
                pass
    else:
        bot.send_message(target_id, "❌ Javob noto‘g‘ri. Takror bajaring!")

    bot.answer_callback_query(call.id, "✅ Xabar yuborildi")
    bot.send_message(admin_id, "✅ Tekshirldi")

# ===== Botni ishga tushirish =====
print("Bot ishga tushdi")

bot.infinity_polling()










