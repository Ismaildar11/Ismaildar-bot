import telebot
from telebot import types
import time
import sqlite3
import threading
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 2092515567
GROUP_CHAT_IDS = [-1005225264839, -1003819425342, -1003680070293]  # Natija yuboriladigan guruhlar
CHANNEL_USERNAME = "@Qorakoltalimmarkazi"
CHANNEL_LINK = "https://t.me/Qorakoltalimmarkazi"

bot = telebot.TeleBot(TOKEN)

# ===== DATABASE =====
conn = sqlite3.connect("Ismaildar.data.db", check_same_thread=False)
cur = conn.cursor()

# Testlar
cur.execute('''
CREATE TABLE IF NOT EXISTS tests(
    test_id TEXT PRIMARY KEY,
    content TEXT,
    answer_key TEXT,
    duration INTEGER
)
''')

# Natijalar
cur.execute('''
CREATE TABLE IF NOT EXISTS results(
    user_id INTEGER,
    username TEXT,
    test_id TEXT,
    answers TEXT,
    score REAL
)
''')
conn.commit()

user_state = {}

# ===== OBUNA TEKSHIRISH =====
def check_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    markup = types.InlineKeyboardMarkup(row_width=1)  # 1 ta tugma har qatorda
    btn1 = types.InlineKeyboardButton("📚KANALGA OBUNA BO'LING📚", url=CHANNEL_LINK)
    btn2 = types.InlineKeyboardButton("✅TASDIQLAYMAN✅", callback_data="check")
    markup.add(btn1, btn2)  # row_width=1 bo'lgani uchun ustma-ust chiqadi
    bot.send_message(msg.chat.id, "🔆Xush kelibsiz!🔆 Botdan foydalanish uchun kanalga obuna bo‘ling. Keyin ✅TASDIQLAYMAN✅ tugmasini bosing!", reply_markup=markup)

# ===== CHECK VA MENYU =====
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check(call):
    user_id = call.from_user.id
    if check_sub(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        # ===== ADMIN MENYU =====
        if user_id == ADMIN_ID:
            markup.add("➕Test qo‘shish")
            markup.add("📊NATIJALAR📊")  # Admin ham o'z natijalarini ko'rishi mumkin
        else:
            # ===== TALABA MENYU =====
            markup.add("♻️TEST♻️")
            markup.add("📝TOPSHIRIQLAR📝")
            markup.add("📊NATIJALAR📊")
        
        bot.send_message(call.message.chat.id, "Menyuni tanlang:", reply_markup=markup)
        bot.answer_callback_query(call.id, "✅Tasdiqlandi✅")
    else:
        bot.send_message(call.message.chat.id, "❌Avval /start tugmasini bosing va kanalga obuna bo‘ling❌")
        bot.answer_callback_query(call.id, "‼️Kanalga obuna bo‘ling‼️")

# ===== ADMIN: TEST QO‘SHISH =====
@bot.message_handler(func=lambda m: m.text == "➕Test qo‘shish" and m.chat.id == ADMIN_ID)
def add_test_menu(msg):
    bot.send_message(msg.chat.id, "Test ID kiriting:")
    bot.register_next_step_handler(msg, get_test_id)

def get_test_id(msg):
    test_id = msg.text.strip()
    bot.send_message(msg.chat.id, "Test matnini yoki rasm yuboring:")
    bot.register_next_step_handler  (msg, get_test_content, test_id)

def get_test_content(msg, test_id):
    if msg.content_type == 'photo':
        file_id = msg.photo[-1].file_id
        content = f"photo:{file_id}"
    else:
        content = msg.text
    bot.send_message(msg.chat.id, "Javob kalitini kiriting (masalan: abcdabcd)")
    bot.register_next_step_handler(msg, save_test, test_id, content)

def save_test(msg, test_id, content):
    answer_key = msg.text.strip().lower()
    cur.execute(
        "INSERT OR REPLACE INTO tests(test_id, content, answer_key, duration) VALUES(?,?,?,?)",
        (test_id, content, answer_key, 30)
    )
    conn.commit()
    bot.send_message(msg.chat.id, f"✅ Test saqlandi: {test_id}")
# ===== TALABA: TEST MENYU =====
@bot.message_handler(func=lambda m: m.text == "♻️TEST♻️")
def test_menu(msg):
    if not check_sub(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌Avval /start bosing va kanalga obuna bo‘ling❌")
        return
    bot.send_message(msg.chat.id, "🔐Test ID kiriting:")
    bot.register_next_step_handler(msg, start_test)



def start_test(msg):
    test_id = msg.text.strip()
    cur.execute("SELECT content, answer_key, duration FROM tests WHERE test_id=?", (test_id,))
    data = cur.fetchone()
    if not data:
        bot.send_message(msg.chat.id, "❌Bunday Test ID topilmadi❌")
        return
    content, answer_key, duration = data

    bot.send_message(msg.chat.id, f"⏳Test boshlandi\nVaqt: {duration} minut")
    if content.startswith("photo:"):
        bot.send_photo(msg.chat.id, content.split(":")[1])
    else:
        bot.send_message(msg.chat.id, content)

    bot.send_message(msg.chat.id, "📝Javoblaringizni yuboring (masalan: abcdabcd)")

    # Start timer
    def time_up():
        bot.send_message(msg.chat.id, "⏰Vaqt tugadi! Javob yuborish endi mumkin emas‼️")
        user_state[msg.chat.id] = "time_up"

    timer = threading.Timer(duration * 30, time_up)
    timer.start()

    # Javoblarni qabul qilish
    bot.register_next_step_handler(msg, check_answers, test_id, answer_key, timer)

def check_answers(msg, test_id, answer_key, timer):
    if user_state.get(msg.chat.id) == "time_up":
        bot.send_message(msg.chat.id, "❌Vaqt tugaganligi sababli javob qabul qilinmaydi‼️")
        return

    timer.cancel()  # agar vaqt tugamagan bo'lsa, timerni bekor qilish

    answers = msg.text.strip().lower()
    score = 0
    details = []

    for i, correct in enumerate(answer_key):
        if i < len(answers):
            if answers[i] == correct:
                score += 1
                details.append(f"{i+1}-savol: ✅")
            else:
                details.append(f"{i+1}-savol: ❌")
        else:
            details.append(f"{i+1}-savol: ⚠️")

    percent = round(score / len(answer_key) * 100, 2)
    bot.send_message(msg.chat.id, "\n".join(details))
    bot.send_message(msg.chat.id, f"📊 Natija: {percent}%")

    # Natijani saqlash
    cur.execute(
        "INSERT INTO results(user_id, username, test_id, answers, score) VALUES(?,?,?,?,?)",
        (msg.from_user.id, msg.from_user.username, test_id, answers, percent)
    )
    conn.commit()

    # GURUHGA yuborish tantana bilan va tg://user link
    if percent >= 85:
        for group_id in GROUP_CHAT_IDS:
            text = (
                f"👑 Talaba: <a href='tg://user?id={msg.from_user.id}'>{msg.from_user.first_name}</a>\n"
                f"🏆 Testdan natija: {percent}%\n"
                "🥳 Tantanali tarzda tabriklaymiz! Ofarin!👏"
            )
            bot.send_message(group_id, text, parse_mode='HTML')

    # Adminga natija
    bot.send_message(
        ADMIN_ID,
        f"📌 Natija talaba: <a href='tg://user?id={msg.from_user.id}'>{msg.from_user.first_name}</a>\n"
        f"Test ID: {test_id}\n"
        f"Javoblar: {answers}\n"
        f"Natija: {percent}%",
        parse_mode='HTML'
    )

# ===== ADMIN: TEST VAQTI O'ZGARTIRISH =====
@bot.message_handler(commands=['time'])
def set_test_time(msg):
    if msg.chat.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Faqat admin foydalanishi mumkin")
        return
    bot.send_message(msg.chat.id, "⏳ O'zgartirmoqchi bo'lgan test ID kiriting:")
    bot.register_next_step_handler(msg, get_test_id_for_time)

def get_test_id_for_time(msg):
    test_id = msg.text.strip()
    cur.execute("SELECT test_id FROM tests WHERE test_id=?", (test_id,))
    if not cur.fetchone():
        bot.send_message(msg.chat.id, "❌ Bunday test topilmadi")
        return
    bot.send_message(msg.chat.id, "⏳ Test uchun vaqt (minutlarda) kiriting:")
    bot.register_next_step_handler(msg, save_test_time, test_id)
def save_test_time(msg, test_id):
    try:
        duration = int(msg.text.strip())
        cur.execute("UPDATE tests SET duration=? WHERE test_id=?", (duration, test_id))
        conn.commit()
        bot.send_message(msg.chat.id, f"✅ Test ID {test_id} uchun vaqt {duration} minutga o'zgartirildi", parse_mode='Markdown')
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Iltimos, butun son kiriting")

@bot.message_handler(func=lambda m: m.text in ["📊Natijalar"])
def results(msg):

    # Natijalarni chiqarish
    cur.execute("SELECT test_id, score FROM results WHERE user_id=?", (msg.from_user.id,))
    res = cur.fetchall()

    # INLINE TUGMALAR
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("♻️Test natijalari♻️", callback_data="go_test")
    btn2 = types.InlineKeyboardButton("📝Topshiriq natijalari📝", callback_data="go_task")

    markup.add(btn1)
    markup.add(btn2)

    bot.send_message(msg.chat.id, "Quyidagidan birini tanlang:", reply_markup=markup)

# ===== TALABA: TOPSHIRIQLAR =====
@bot.message_handler(func=lambda m: m.text == "📝TOPSHIRIQLAR📝")
def tasks_menu(message):
    user_state[message.chat.id] = "task"
    bot.send_message(message.chat.id, "📝TOPSHIRIQLAR menyusi tanlandi. Matn yoki rasm yuborishingiz mumkin.")

@bot.message_handler(content_types=['text','photo'])
def receive_task(message):
    # Faqat task holatida ishlaydi
    if user_state.get(message.chat.id) != "task":
        return

    if message.chat.type != 'private' or message.chat.id == ADMIN_ID:
        return

    first_name = message.from_user.first_name

    bot.send_message(
        message.chat.id,
        "📝Topshiriq qabul qilindi. Tekshiruv kutilmoqda. 1soatda xabar kelmasa takror yuboring"
    )

    user_state.pop(message.chat.id, None)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "✅ To‘g‘ri",
            callback_data=f"correct_{message.chat.id}_{first_name}"
        ),
        types.InlineKeyboardButton(
            "❌ Noto‘g‘ri",
            callback_data=f"wrong_{message.chat.id}_{first_name}"
        ),
        types.InlineKeyboardButton(
            "✉️ Talabaga javob yuborish",
            callback_data=f"reply_{message.chat.id}"
        )
    )

    if message.content_type == 'text':
        bot.send_message(
            ADMIN_ID,
            f"{first_name}\n🆔 {message.chat.id}\n\n{message.text}",
            reply_markup=markup
        )

    elif message.content_type == 'photo':
        bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=f"{first_name}\n🆔 {message.chat.id}",
            reply_markup=markup
        )

    else:
        bot.send_message(
            ADMIN_ID,
            f"{first_name}\n🆔 {message.chat.id}\nTuri: {message.content_type}",
            reply_markup=markup
        )

# ===== Admin talabaga javob yuborish =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def reply_to_student(call):
    target_id = int(call.data.split("_")[1])

    bot.send_message(call.from_user.id, f"Talaba 🆔 {target_id} uchun xabar yuboring:")

    # Keyingi xabar admindan kelganini talabaga yuborish
    bot.register_next_step_handler_by_chat_id(call.from_user.id, forward_to_student, target_id)

def forward_to_student(msg, target_id):
    if msg.content_type == 'text':
        bot.send_message(target_id, f"📩Topshirig'ingiz bo'yicha xabar keldi:\n{msg.text}")
    elif msg.content_type == 'photo':
        bot.send_photo(target_id, msg.photo[-1].file_id, caption="📩Topshirig'ingiz bo'yicha xabar keldi")
    else:
        bot.send_message(target_id, "📩Topshirig'ingiz bo'yicha xabar keldi")

    bot.send_message(msg.chat.id, f"✅ Xabar talabaga yuborildi (🆔 {target_id})")
@bot.callback_query_handler(func=lambda call: call.data.startswith(("correct_", "wrong_")))
def handle_result(call):
    data_parts = call.data.split("_")
    target_id = int(data_parts[1])
    first_name = data_parts[2]
    if call.data.startswith("correct_"):
        # Talabaga xabar
        bot.send_message(target_id, "🥳 Sizning javobingiz to‘g‘ri. Ofaring!👏")

        # Guruhga tantanali yuborish tg://user link bilan
        for group_id in GROUP_CHAT_IDS:
            try:
                status = bot.get_chat_member(group_id, target_id).status
                if status in ['member', 'administrator', 'creator']:
                    text = (
                        f"👑 Talaba: <a href='tg://user?id={target_id}'>{first_name}</a>\n"
                        "🥳 Topshiriqni to‘g‘ri bajardi. Ofarin!👏"
                    )
                    bot.send_message(group_id, text, parse_mode='HTML')
            except:
                pass
    else:
        # Talabaga noto‘g‘ri javob xabari
        bot.send_message(target_id, "❌ Javob noto‘g‘ri. Takror bajaring!")

    # Adminga xabar yuborish tugmasi bosilgani haqida
    bot.send_message(call.from_user.id, "✅ Xabar yuborildi ✅")


print("Bot ishga tushdi...")
bot.infinity_polling()
