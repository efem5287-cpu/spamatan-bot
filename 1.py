
import sqlite3
import telebot
from telebot import types

# Bot Token ve Kanal Bilgileri
TOKEN = "8680717584:AAHcbbcwuBwUGYifE9ClA0JE23fMYYwrzF4"
CHANNEL_USERNAME = "@swarovskiyeniden"  # Zorunlu abonelik kanalı
OWNER_USERNAME = "@Onlywmx"           # Botun Sahibi

bot = telebot.TeleBot(TOKEN)

# --- Veritabanı Kurulumu ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Kanal Üyelik Kontrolü ---
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception as e:
        print(f"[-] Kanal kontrol hatası: {e}")
    return False

# --- /start Komutu, Kanal Zorunluluğu ve Referans Sistemi ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Bilinmiyor"
    
    args = message.text.split()
    referrer_id = None
    
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                referrer_id = ref_id
        except ValueError:
            pass

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Kullanıcıyı güvenli bir şekilde ekle (Çakışma / UNIQUE hatasını tamamen önler)
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, referred_by, referrals_count) 
        VALUES (?, ?, ?, 0)
    """, (user_id, username, referrer_id))
    
    # Eğer yeni bota start verdiyse ve referansı varsa davet edenin sayısını artır
    if cursor.rowcount > 0 and referrer_id:
        cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
        try:
            bot.send_message(referrer_id, f"🎉 Tebrikler! Davet ettiğin kişi bota start verdi ve katıldı: @{username}")
        except:
            pass
            
    conn.commit()

    # Kullanıcının güncel referans sayısını çek
    cursor.execute("SELECT referrals_count FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    ref_count = res[0] if res else 0
    
    conn.close()

    # 1. ADIM: Önce Kanal Abonelik Kontrolü (En başta zorunlu!)
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        btn_channel = types.InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        btn_check = types.InlineKeyboardButton("✅ Kontrol Et / Başlat", callback_data="check_sub")
        markup.add(btn_channel)
        markup.add(btn_check)
        
        bot.send_message(
            message.chat.id, 
            f"❌ Botu kullanabilmek için önce kanalımıza abone olmalısın!\n\nKanal: {CHANNEL_USERNAME}\n\nAbone olduktan sonra aşağıdaki 'Kontrol Et' butonuna bas.",
            reply_markup=markup
        )
        return

    # 2. ADIM: En az 1 Kişiyi Davet Etme (Start Verdirme) Zorunluluğu
    if ref_count < 1:
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        bot.send_message(
            message.chat.id,
            f"🔒 **Botu Aktif Etmek İçin Son Adım!**\n\n"
            f"Kanalımıza katıldın teşekkürler! 🎉 Ancak botu kullanabilmek için en az **1 kişiyi** davet etmen ve o kişinin bota start vermesi gerekiyor.\n\n"
            f"🔗 **Senin Özel Davet Linkin:**\n`{ref_link}`\n\n"
            f"👥 Davet edip bota start verdiren kişi sayısı: **{ref_count}/1**\n\n"
            f"Arkadaşın bota start verdikten sonra buraya gelip tekrar `/start` yaz!",
            parse_mode="Markdown"
        )
        return

    # Tüm şartlar sağlandıysa ana menüyü aç
    show_main_menu(message.chat.id)

# --- Abonelik Kontrol Butonu Callback ---
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ Abonelik onaylandı!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referrals_count FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        ref_count = res[0] if res else 0
        conn.close()

        if ref_count < 1:
            bot_info = bot.get_me()
            ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
            bot.send_message(
                call.message.chat.id,
                f"✅ Abonelik onaylandı!\n\n🔒 **Botu Aktif Etmek İçin Son Adım!**\n\n"
                f"Botu kullanabilmek için en az **1 kişiyi** davet etmen gerekiyor.\n\n"
                f"🔗 **Senin Özel Davet Linkin:**\n`{ref_link}`\n\n"
                f"👥 Davet ettiğin kişi sayısı: **{ref_count}/1**",
                parse_mode="Markdown"
            )
        else:
            show_main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "❌ Henüz kanala abone olmamışsın!", show_alert=True)

# --- Ana Menü ---
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Spam İşlemleri", "👥 Referanslarım")
    markup.row("ℹ️ Bilgi / Panel")
    
    bot.send_message(
        chat_id, 
        "🤖 **Spamatan Bot Paneline Hoş Geldin!**\n\nİstediğin işlemi aşağıdaki butonlardan seçebilirsin:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- Mesaj Yönlendirici ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, f"⚠️ Botu kullanmaya devam etmek için önce {CHANNEL_USERNAME} kanalına abone olmalısın!")
        return

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT referrals_count FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    ref_count = res[0] if res else 0
    conn.close()

    if ref_count < 1:
        bot.send_message(message.chat.id, "⚠️ Botu kullanabilmek için önce en az 1 kişiyi davet etmelisin!")
        return

    text = message.text

    if text == "🚀 Spam İşlemleri":
        bot.send_message(
            message.chat.id, 
            "⚠️ **Spam Modu Bilgisi:**\n\nBotu gruplarda veya kanalınızda kullanabilirsiniz. Hedef grup veya kanal ID'sini kullanarak otomasyonu başlatabilirsiniz.",
            parse_mode="Markdown"
        )

    elif text == "👥 Referanslarım":
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referrals_count FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        ref_count = res[0] if res else 0
        conn.close()

        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

        bot.send_message(
            message.chat.id,
            f"🔗 **Referans Sistemi**\n\n"
            f"Davet Linkin:\n`{ref_link}`\n\n"
            f"👥 Toplam Davet Ettiğin Kişi: **{ref_count}**",
            parse_Mode="Markdown"
        )

    elif text == "ℹ️ Bilgi / Panel":
        bot.send_message(
            message.chat.id, 
            f"🤖 **Bot Bilgileri**\n\n"
            f"• Sistem: Aktif ve Sorunsuz\n"
            f"• Geliştirici / Sahip: **{OWNER_USERNAME}**\n"
            f"• Kanal: {CHANNEL_USERNAME}",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "Lütfen menüdeki butonları kullan.")

if __name__ == "__main__":
    print("[*] @Spamatan_bot başlatılıyor...")
    bot.infinity_polling()
