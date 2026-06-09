# =============================================
#  YouTube Bot — pyTelegramBotAPI (telebot)
#  Pydroid 3 + Python 3.13 da ishonchli ishlaydi
# =============================================

import os
import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============ TOKENNI SHU YERGA KIRITING ============
BOT_TOKEN = "8587657322:AAG1tzMEMDUvIemD-acvUQQCLI7W4B0l_KI"
# ====================================================

DOWNLOAD_DIR = "/sdcard/YouTubeBot"
MAX_MB = 50

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchi ma'lumotlarini saqlash
user_data = {}


def is_yt(url):
    return "youtube.com" in url or "youtu.be" in url


def get_info(url):
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print("Info xato:", e)
        return None


def dur(sec):
    sec = int(sec or 0)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return ("%02d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))


def sz(b):
    b = int(b or 0)
    if b < 1024**2: return "%.0f KB" % (b / 1024)
    if b < 1024**3: return "%.1f MB" % (b / 1024**2)
    return "%.2f GB" % (b / 1024**3)


def make_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🎬 360p", callback_data="v360"),
        InlineKeyboardButton("🎬 720p", callback_data="v720"),
    )
    kb.row(
        InlineKeyboardButton("🎵 Audio", callback_data="audio"),
        InlineKeyboardButton("❌ Bekor", callback_data="cancel"),
    )
    return kb


FMTS = {
    "v360":  "best[height<=360][ext=mp4]/best[height<=360]/best",
    "v720":  "best[height<=720][ext=mp4]/best[height<=720]/best",
    "audio": "bestaudio/best",
}


# ---------- KOMANDALAR ----------

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id,
        "YouTube Bot\n\n"
        "YouTube havolasini yuboring\n"
        "Format tanlang — bot faylni yuboradi\n\n"
        "/help — yordam"
    )


@bot.message_handler(commands=["help"])
def help_cmd(msg):
    bot.send_message(msg.chat.id,
        "Foydalanish:\n"
        "1) YouTube havolasini yuboring\n"
        "2) 360p / 720p / Audio tanlang\n"
        "3) Bot faylni yuboradi\n\n"
        "Max fayl: 50 MB"
    )


# ---------- XABAR ----------

@bot.message_handler(func=lambda m: True)
def handle_msg(msg):
    url = msg.text.strip()
    if not is_yt(url):
        bot.send_message(msg.chat.id, "YouTube havolasini yuboring.")
        return

    sent = bot.send_message(msg.chat.id, "Ma'lumotlar olinmoqda...")
    info = get_info(url)

    if not info:
        bot.edit_message_text("Video topilmadi.", msg.chat.id, sent.message_id)
        return

    title = info.get("title", "Video")
    user_data[msg.chat.id] = {"url": url, "title": title}

    text = (
        "📹 %s\n\n"
        "⏱ %s\n"
        "👤 %s\n\n"
        "Format tanlang:" % (
            title,
            dur(info.get("duration", 0)),
            info.get("uploader", "Noma'lum"),
        )
    )
    bot.edit_message_text(text, msg.chat.id, sent.message_id, reply_markup=make_keyboard())


# ---------- TUGMALAR ----------

@bot.callback_query_handler(func=lambda c: True)
def handle_btn(call):
    chat_id = call.message.chat.id
    msg_id  = call.message.message_id

    if call.data == "cancel":
        bot.edit_message_text("Bekor qilindi.", chat_id, msg_id)
        return

    if call.data not in FMTS:
        bot.edit_message_text("Noma'lum format.", chat_id, msg_id)
        return

    data  = user_data.get(chat_id)
    if not data:
        bot.edit_message_text("Xato. Havolani qayta yuboring.", chat_id, msg_id)
        return

    url   = data["url"]
    title = data["title"]

    labels = {"v360": "360p MP4", "v720": "720p MP4", "audio": "Audio"}
    bot.edit_message_text("⬇️ %s yuklanmoqda...\n⏳ Kuting." % labels[call.data], chat_id, msg_id)

    safe = "".join(c for c in title if c.isalnum() or c in " -_")[:40]
    out  = os.path.join(DOWNLOAD_DIR, safe + ".%(ext)s")

    try:
        with yt_dlp.YoutubeDL({"format": FMTS[call.data], "outtmpl": out, "quiet": True}) as ydl:
            info2 = ydl.extract_info(url, download=True)
            fpath = ydl.prepare_filename(info2)

        # Faylni topish
        if not os.path.exists(fpath):
            base = os.path.splitext(fpath)[0]
            for ext in [".mp4", ".webm", ".mkv", ".m4a", ".opus"]:
                if os.path.exists(base + ext):
                    fpath = base + ext
                    break

        if not os.path.exists(fpath):
            all_f = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)]
            if all_f:
                fpath = max(all_f, key=os.path.getmtime)

        if not os.path.exists(fpath):
            bot.edit_message_text("Fayl topilmadi.", chat_id, msg_id)
            return

        size = os.path.getsize(fpath)
        if size > MAX_MB * 1024 * 1024:
            os.remove(fpath)
            bot.edit_message_text(
                "Fayl juda katta (%s).\n360p tanlang." % sz(size),
                chat_id, msg_id
            )
            return

        bot.edit_message_text("📤 Yuborilmoqda... %s" % sz(size), chat_id, msg_id)

        ext = os.path.splitext(fpath)[1].lower()
        with open(fpath, "rb") as f:
            if ext in [".m4a", ".mp3", ".opus", ".ogg"] or call.data == "audio":
                bot.send_audio(chat_id, f, title=title)
            else:
                bot.send_video(chat_id, f, caption=title)

        os.remove(fpath)
        bot.edit_message_text("✅ Yuborildi!", chat_id, msg_id)

    except Exception as e:
        print("Xato:", e)
        bot.edit_message_text("Xato: %s" % str(e)[:200], chat_id, msg_id)
        try:
            for fn in os.listdir(DOWNLOAD_DIR):
                fp = os.path.join(DOWNLOAD_DIR, fn)
                if os.path.isfile(fp):
                    os.remove(fp)
        except Exception:
            pass


# ---------- ISHGA TUSHIRISH ----------

print("=" * 40)
print("  Bot ishga tushdi!")
print("  Toxtatish: Ctrl+C")
print("=" * 40)

bot.infinity_polling()
