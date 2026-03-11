import os
import sqlite3
import asyncio
import random
from telethon import TelegramClient, events

# ================= CONFIGURATION =================
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DB_NAME = "database.db"

user = TelegramClient('user_session', API_ID, API_HASH)
bot = TelegramClient('bot_session', API_ID, API_HASH)

# ================= DATABASE & UTILS =================
def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sources (link TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS destinations (link TEXT UNIQUE)")
        db.commit()

def update_db(table, link, action="add"):
    with sqlite3.connect(DB_NAME) as db:
        if action == "add":
            db.execute(f"INSERT OR IGNORE INTO {table} VALUES (?)", (link,))
        elif action == "remove":
            db.execute(f"DELETE FROM {table} WHERE link = ?", (link,))
        db.commit()

# ইউনিক ক্যাপশন জেনারেটর
def get_unique_caption():
    emojis = ["💎", "✨", "🎬", "🔥", "🌟", "🎥", "⚡", "🌈"]
    texts = [
        "Exclusive Video Update", "Premium Content for You", 
        "Handpicked Selection", "Enjoy this special clip",
        "Must Watch Video", "Quality Content Only", 
        "Trending Clip", "Something New For You"
    ]
    tags = ["#Premium", "#Exclusive", "#Trending", "#Video", "#DailyUpdate"]
    
    caption = f"{random.choice(emojis)} **{random.choice(texts)}** {random.choice(emojis)}\n\n"
    caption += f"🚀 Join our channel for more!\n\n"
    caption += f"{random.choice(tags)} {random.choice(tags)}"
    return caption

# ================= BOT COMMANDS =================

@bot.on(events.NewMessage(pattern=r'^/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("✅ **FK Smart Pro V5 (Video Only Edition) is Online!**\n\nCommands: /add_source, /add_dest, /list, /clear_all")

@bot.on(events.NewMessage(pattern=r'^/add_source (.+)'))
async def add_src(event):
    if event.sender_id != ADMIN_ID: return
    link = event.pattern_match.group(1).strip()
    update_db("sources", link, "add")
    await event.reply(f"📥 Source Added: `{link}`")

@bot.on(events.NewMessage(pattern=r'^/add_dest (.+)'))
async def add_dst(event):
    if event.sender_id != ADMIN_ID: return
    link = event.pattern_match.group(1).strip()
    update_db("destinations", link, "add")
    await event.reply(f"🎯 Destination Added: `{link}`")

@bot.on(events.NewMessage(pattern=r'^/list'))
async def list_links(event):
    if event.sender_id != ADMIN_ID: return
    with sqlite3.connect(DB_NAME) as db:
        sources = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        destinations = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]
    
    msg = "📋 **Status:**\n\n📥 **Sources:** " + str(len(sources)) + "\n🎯 **Destinations:** " + str(len(destinations))
    await event.reply(msg)

@bot.on(events.NewMessage(pattern=r'^/clear_all'))
async def clear_all(event):
    if event.sender_id != ADMIN_ID: return
    with sqlite3.connect(DB_NAME) as db:
        db.execute("DELETE FROM sources")
        db.execute("DELETE FROM destinations")
    await event.reply("🗑️ All Data Cleared!")

# ================= FORWARDING LOGIC (VIDEO ONLY) =================

@user.on(events.NewMessage)
async def forwarder(event):
    # শুধুমাত্র ভিডিও চেক করা হচ্ছে
    if not event.video:
        return

    with sqlite3.connect(DB_NAME) as db:
        sources = [row[0] for row in db.execute("SELECT link FROM sources").fetchall()]
        destinations = [row[0] for row in db.execute("SELECT link FROM destinations").fetchall()]

    if not sources or not destinations: return

    chat = await event.get_chat()
    chat_id = str(event.chat_id)
    username = getattr(chat, 'username', '')

    # সোর্স ভেরিফিকেশন
    is_source = False
    for s in sources:
        if s in [chat_id, username, f"https://t.me/{username}"]:
            is_source = True
            break

    if is_source:
        new_caption = get_unique_caption() # ইউনিক ক্যাপশন তৈরি
        for dest in destinations:
            try:
                # ভিডিওটি নতুন ক্যাপশন সহ পাঠানো হচ্ছে
                await user.send_file(dest, event.video, caption=new_caption, parse_mode='md')
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error: {e}")

# ================= EXECUTION =================

async def main():
    init_db()
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("💎 Bot is running... (Monitoring Videos Only)")
    await asyncio.gather(user.run_until_disconnected(), bot.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
