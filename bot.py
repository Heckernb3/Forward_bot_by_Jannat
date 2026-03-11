import os
import sqlite3
import asyncio
import random
from telethon import TelegramClient, events, Button

# ================= CONFIGURATION =================
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DB_NAME = "database.db"

user = TelegramClient('user_session', API_ID, API_HASH)
bot = TelegramClient('bot_session', API_ID, API_HASH)

# গ্লোবাল ভেরিয়েবল
forwarding_active = False
current_delay = 3

# ================= DATABASE & UTILS =================
def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sources (link TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS destinations (link TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT UNIQUE, value TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT UNIQUE, count INTEGER)")
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
        src = db.execute("SELECT count(*) FROM sources").fetchone()[0]
        dst = db.execute("SELECT count(*) FROM destinations").fetchone()[0]
        sent = db.execute("SELECT count FROM stats WHERE key='total_sent'").fetchone()[0]
        return src, dst, sent

def get_unique_caption():
    c_name, c_link = get_settings()
    emojis = ["💎", "✨", "🎬", "🔥", "🌟", "🎥"]
    texts = ["Exclusive Content", "Premium Video", "Special Update", "Must Watch"]
    
    caption = f"{random.choice(emojis)} **{random.choice(texts)}** {random.choice(emojis)}\n\n"
    caption += f"🚀 **Join Our Channel:** [{c_name}]({c_link})\n"
    caption += f"━━━━━━━━━━━━━━━━━━━━"
    return caption

# ================= BOT UI / CONTROL PANEL =================

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
        f"📢 **Channel Info:**\nName: `{c_name}`\nLink: `{c_link}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Bot Status:** {status}\n"
        f"📊 **Total Sent:** {sent} videos\n"
        f"⚡ **Delay:** {current_delay}s\n"
    )
    
    buttons = [
        [Button.inline("🚀 START", b"start_f"), Button.inline("🛑 STOP", b"stop_f")],
        [Button.inline("✏️ SET NAME", b"set_name"), Button.inline("🔗 SET LINK", b"set_link")],
        [Button.inline("📂 FORWARD ALL OLD", b"forward_old")],
        [Button.inline("📊 STATS", b"stats"), Button.inline("🗑️ CLEAR ALL", b"clear")]
    ]
    
    if text and hasattr(event, 'edit'):
        await event.edit(panel_text, buttons=buttons, link_preview=False)
    else:
        await event.reply(panel_text, buttons=buttons, link_preview=False)

# ================= CALLBACK HANDLERS =================

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    global forwarding_active
    if event.sender_id != ADMIN_ID: return
    
    data = event.data
    
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
            await conv.send_message("📝 আপনার চ্যানেলের নতুন নাম লিখে পাঠান:")
            name = await conv.get_response()
            with sqlite3.connect(DB_NAME) as db:
                db.execute("UPDATE settings SET value=? WHERE key='channel_name'", (name.text,))
                db.commit()
            await conv.send_message(f"✅ চ্যানেলের নাম আপডেট করা হয়েছে: `{name.text}`")
            await send_main_panel(event, text=False)

    elif data == b"set_link":
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("🔗 আপনার চ্যানেলের লিঙ্ক (https://t.me/...) লিখে পাঠান:")
            link = await conv.get_response()
            with sqlite3.connect(DB_NAME) as db:
                db.execute("UPDATE settings SET value=? WHERE key='channel_link'", (link.text,))
                db.commit()
            await conv.send_message(f"✅ চ্যানেলের লিঙ্ক আপডেট করা হয়েছে: `{link.text}`")
            await send_main_panel(event, text=False)

    elif data == b"forward_old":
        await event.answer("Starting to forward all old videos...")
        asyncio.create_task(run_forward_old(event))

    elif data == b"clear":
        with sqlite3.connect(DB_NAME) as db:
            db.execute("DELETE FROM sources")
            db.execute("DELETE FROM destinations")
        await event.answer("🗑️ Cleared!")
        await send_main_panel(event)

# ================= FORWARD OLD TASK =================

async def run_forward_old(event):
    with sqlite3.connect(DB_NAME) as db:
        sources = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        destinations = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]

    for src in sources:
        async for message in user.iter_messages(src):
            if message.video:
                caption = get_unique_caption()
                for dest in destinations:
                    try:
                        await user.send_file(dest, message.video, caption=caption, parse_mode='md')
                        with sqlite3.connect(DB_NAME) as db:
                            db.execute("UPDATE stats SET count = count + 1 WHERE key='total_sent'")
                            db.commit()
                        await asyncio.sleep(current_delay)
                    except: pass
    await bot.send_message(ADMIN_ID, "✅ সব পুরানো ভিডিও পাঠানো শেষ!")

# ================= COMMANDS =================

@bot.on(events.NewMessage(pattern=r'^/start'))
async def start_cmd(event):
    if event.sender_id == ADMIN_ID:
        await send_main_panel(event, text=False)

@bot.on(events.NewMessage(pattern=r'^/add_source (.+)'))
async def add_src(event):
    if event.sender_id != ADMIN_ID: return
    link = event.pattern_match.group(1).strip()
    with sqlite3.connect(DB_NAME) as db:
        db.execute("INSERT OR IGNORE INTO sources VALUES (?)", (link,))
    await event.reply(f"✅ Source Added: {link}")

@bot.on(events.NewMessage(pattern=r'^/add_dest (.+)'))
async def add_dst(event):
    if event.sender_id != ADMIN_ID: return
    link = event.pattern_match.group(1).strip()
    with sqlite3.connect(DB_NAME) as db:
        db.execute("INSERT OR IGNORE INTO destinations VALUES (?)", (link,))
    await event.reply(f"✅ Destination Added: {link}")

# ================= AUTO FORWARDER =================

@user.on(events.NewMessage)
async def auto_forward(event):
    if not forwarding_active or not event.video: return
    with sqlite3.connect(DB_NAME) as db:
        sources = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        destinations = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]
    
    chat = await event.get_chat()
    chat_id = str(event.chat_id)
    username = getattr(chat, 'username', '')

    if chat_id in sources or username in sources:
        caption = get_unique_caption()
        for dest in destinations:
            try:
                await user.send_file(dest, event.video, caption=caption, parse_mode='md')
                with sqlite3.connect(DB_NAME) as db:
                    db.execute("UPDATE stats SET count = count + 1 WHERE key='total_sent'")
                    db.commit()
                await asyncio.sleep(current_delay)
            except: pass

# ================= RUN =================
async def main():
    init_db()
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("🚀 Bot is Online with Custom Branding!")
    await asyncio.gather(user.run_until_disconnected(), bot.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
