import os
import sqlite3
import asyncio
import random
from telethon import TelegramClient, events, Button
from telethon.errors import QueryIdInvalidError

# ==================== কনফিগারেশন ====================
API_ID = int(os.getenv('API_ID', '37588682'))          # ডিফল্ট স্ট্রিংকে int‑এ রূপান্তর
API_HASH = os.getenv('API_HASH', 'ffc989361d4837612fff98440b896baa')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8402046891:AAHCIAsotpho1dCxuA1PG85u2sJtgUxw7ok')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8521924014'))   # নিশ্চিতভাবে int
DB_NAME = "database.db"

# ক্লায়েন্টগুলো
user = TelegramClient('user_session', API_ID, API_HASH)
bot = TelegramClient('bot_session', API_ID, API_HASH)

# গ্লোবাল ভেরিয়েবল
forwarding_active = False
current_delay = 3

# ==================== ডাটাবেস ও ইউটিলিটি ====================
def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sources (link TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS destinations (link TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT UNIQUE, value TEXT)")
        # `count` কলামকে `cnt`‑এ পরিবর্তন (SQLite‑এর রিজার্ভড কী এড়াতে)
        db.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT UNIQUE, cnt INTEGER)")
        db.execute("INSERT OR IGNORE INTO stats VALUES ('total_sent', 0)")
        db.execute("INSERT OR IGNORE INTO settings VALUES ('channel_name', 'My Channel')")
        db.execute("INSERT OR IGNORE INTO settings VALUES ('channel_link', 'https://t.me/example')")
        db.commit()

def get_settings():
    with sqlite3.connect(DB_NAME) as db:
        name = db.execute("SELECT value FROM settings WHERE key='channel_name'").fetchone()[0]
        link = db.execute("SELECT value FROM settings WHERE key='channel_link'").fetchone()[0]
        return name, link

def get_stats():
    with sqlite3.connect(DB_NAME) as db:
        src = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        dst = db.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
        sent = db.execute("SELECT cnt FROM stats WHERE key='total_sent'").fetchone()[0]
        return src, dst, sent

def get_unique_caption():
    c_name, c_link = get_settings()
    emojis = ["💎", "✨", "🎬", "🔥", "🌟", "🎥"]
    texts = ["Exclusive Content", "Premium Video", "Special Update", "Must Watch"]
    caption = f"{random.choice(emojis)} **{random.choice(texts)}** {random.choice(emojis)}\n\n"
    caption += f"🚀 **Join Our Channel:** [{c_name}]({c_link})\n"
    caption += "━━━━━━━━━━━━━━━━━━━━"
    return caption

# ==================== UI / কন্ট্রোল প্যানেল ====================
async def send_main_panel(event, text=True):
    src, dst, sent = get_stats()
    c_name, c_link = get_settings()
    status = "RUNNING 🚀" if forwarding_active else "IDLE 💤"

    panel_text = (
        "🖥 **FK SMART CONTROL PANEL**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 **Source:** {'Set ✅' if src > 0 else 'Not Set ❌'}\n"
        f"🎯 **Dest:** {'Set ✅' if dst > 0 else 'Not Set ❌'}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 **Branding:**\nName: `{c_name}`\nLink: `{c_link}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Bot Status:** {status}\n"
        f"📊 **Total Sent:** {sent} videos\n"
        f"⚡ **Delay:** {current_delay}s\n"
    )

    buttons = [
        [Button.inline("🚀 START", b"start_f"), Button.inline("🛑 STOP", b"stop_f")],
        [Button.inline("✏️ SET NAME", b"set_name"), Button.inline("🔗 SET LINK", b"set_link")],
        [Button.inline("📂 FORWARD ALL OLD", b"forward_old")],
        [Button.inline("🗑️ CLEAR ALL", b"clear")]
    ]

    try:
        if text and hasattr(event, "edit"):
            await event.message.edit(panel_text, buttons=buttons, link_preview=False)
        else:
            await event.reply(panel_text, buttons=buttons, link_preview=False)
    except Exception:
        pass

# ==================== কলব্যাক হ্যান্ডলার ====================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    global forwarding_active
    if event.sender_id != ADMIN_ID:
        return

    data = event.data
    try:
        if data == b"start_f":
            forwarding_active = True
            await event.answer("🚀 Forwarding Started!")
            await send_main_panel(event)

        elif data == b"stop_f":
            forwarding_active = False
            await event.answer("🛑 Forwarding Stopped!")
            await send_main_panel(event)

        elif data == b"set_name":
            async with bot.conversation(event.sender_id) as conv:
                await conv.send_message("📝 আপনার চ্যানেলের নাম লিখে পাঠান:")
                name = await conv.get_response()
                with sqlite3.connect(DB_NAME) as db:
                    db.execute(
                        "UPDATE settings SET value=? WHERE key='channel_name'",
                        (name.text.strip(),)
                    )
                    db.commit()
                await conv.send_message(f"✅ নাম সেট হয়েছে: `{name.text}`")
                await send_main_panel(event, text=False)

        elif data == b"set_link":
            async with bot.conversation(event.sender_id) as conv:
                await conv.send_message("🔗 চ্যানেলের লিঙ্ক (https://t.me/...) পাঠান:")
                link = await conv.get_response()
                with sqlite3.connect(DB_NAME) as db:
                    db.execute(
                        "UPDATE settings SET value=? WHERE key='channel_link'",
                        (link.text.strip(),)
                    )
                    db.commit()
                await conv.send_message(f"✅ লিঙ্ক সেট হয়েছে: `{link.text}`")
                await send_main_panel(event, text=False)

        elif data == b"forward_old":
            await event.answer("Starting Old Forwarding...")
            # ইভেন্টের লাইফটাইম শেষ হলে সমস্যা না হয় এমনভাবে ডেটা কপি করে টাস্ক চালাই
            asyncio.create_task(run_forward_old())

        elif data == b"clear":
            with sqlite3.connect(DB_NAME) as db:
                db.execute("DELETE FROM sources")
                db.execute("DELETE FROM destinations")
                db.commit()
            await event.answer("🗑️ Cleared!")
            await send_main_panel(event)

    except QueryIdInvalidError:
        # কলব্যাক ইতিমধ্যে হ্যান্ডেল হয়ে গেলে উপেক্ষা
        pass
    except Exception as e:
        print(f"Callback error: {e}")

# ==================== পুরানো মেসেজ ফরওয়ার্ড ====================
async def run_forward_old():
    # ডাটাবেস থেকে লিঙ্কগুলো নিন
    with sqlite3.connect(DB_NAME) as db:
        src_links = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        dst_links = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]

    # লিঙ্ককে টেলিগ্রাম এন্টিটিতে রূপান্তর
    src_entities = [await user.get_entity(link) for link in src_links]
    dst_entities = [await user.get_entity(link) for link in dst_links]

    for src in src_entities:
        async for message in user.iter_messages(src):
            if not message.video:
                continue
            caption = get_unique_caption()
            for dst in dst_entities:
                try:
                    await user.send_file(
                        dst,
                        message.video,
                        caption=caption,
                        parse_mode='markdown'
                    )
                    with sqlite3.connect(DB_NAME) as db:
                        db.execute(
                            "UPDATE stats SET cnt = cnt + 1 WHERE key='total_sent'"
                        )
                        db.commit()
                    await asyncio.sleep(current_delay)
                except Exception as e:
                    print(f"Old forward error ({dst.id}): {e}")

    await bot.send_message(ADMIN_ID, "✅ সব পুরানো ভিডিও ফরওয়ার্ড শেষ!")

# ==================== কমান্ডগুলো ====================
@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_cmd(event):
    if event.sender_id == ADMIN_ID:
        await send_main_panel(event, text=False)

@bot.on(events.NewMessage(pattern=r'^/add_source\s+(.+)$'))
async def add_src(event):
    if event.sender_id != ADMIN_ID:
        return
    link = event.pattern_match.group(1).strip()
    with sqlite3.connect(DB_NAME) as db:
        db.execute("INSERT OR IGNORE INTO sources VALUES (?)", (link,))
        db.commit()
    await event.reply(f"✅ Source Added: {link}")

@bot.on(events.NewMessage(pattern=r'^/add_dest\s+(.+)$'))
async def add_dst(event):
    if event.sender_id != ADMIN_ID:
        return
    link = event.pattern_match.group(1).strip()
    with sqlite3.connect(DB_NAME) as db:
        db.execute("INSERT OR IGNORE INTO destinations VALUES (?)", (link,))
        db.commit()
    await event.reply(f"✅ Destination Added: {link}")

# ==================== রিয়েল‑টাইম অটো‑ফরওয়ার্ড ====================
@user.on(events.NewMessage)
async def auto_forward(event):
    if not forwarding_active:
        return

    # মেসেজে ভিডিও আছে কিনা নিশ্চিত করুন
    if not getattr(event.message, "video", None):
        return

    # ডাটাবেস থেকে সোর্স ও ডেস্ট লিস্ট নিন
    with sqlite3.connect(DB_NAME) as db:
        src_links = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        dst_links = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]

    # বর্তমান চ্যাটের আইডি/ইউজারনেম চেক
    chat = await event.get_chat()
    chat_id = str(event.chat_id)
    username = getattr(chat, "username", "")

    if chat_id not in src_links and username not in src_links:
        return

    # ডেস্ট এন্টিটিগুলো রেজল্ভ করুন (একবার রেজল্ভ করলে পারফরম্যান্স বাড়ে)
    dst_entities = [await user.get_entity(link) for link in dst_links]

    caption = get_unique_caption()
    for dst in dst_entities:
        try:
            await user.send_file(
                dst,
                event.message.video,
                caption=caption,
                parse_mode='markdown'
            )
            with sqlite3.connect(DB_NAME) as db:
                db.execute(
                    "UPDATE stats SET cnt = cnt + 1 WHERE key='total_sent'"
                )
                db.commit()
            await asyncio.sleep(current_delay)
        except Exception as e:
            print(f"Auto forward error ({dst.id}): {e}")

# ==================== রান ====================
async def main():
    init_db()
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)   # bot_token‑কে সরাসরি পাস
    print("🚀 Bot is Online and Error‑Proofed!")
    await asyncio.gather(user.run_until_disconnected(),
                         bot.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
