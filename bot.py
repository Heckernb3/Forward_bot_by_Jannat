import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeVideo

# ================= LOAD ENV =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

ADMINS = [ADMIN_ID]

DB = "forwarder.db"

user = TelegramClient("user_session", API_ID, API_HASH)
bot = TelegramClient("bot_session", API_ID, API_HASH)

# ================= DATABASE =================

def init_db():
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sources (id TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS dests (id TEXT UNIQUE)")
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT)")

def set_setting(k,v):
    with sqlite3.connect(DB) as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",(k,v))

def get_setting(k,default):
    with sqlite3.connect(DB) as db:
        r=db.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
        return int(r[0]) if r else default

def get_sources():
    with sqlite3.connect(DB) as db:
        return [x[0] for x in db.execute("SELECT id FROM sources")]

def get_dests():
    with sqlite3.connect(DB) as db:
        return [x[0] for x in db.execute("SELECT id FROM dests")]

# ================= CAPTION =================

def make_caption():

    now=datetime.now()

    return f"""🔥 New Video

📅 Date : {now.strftime('%d-%m-%Y')}
⏰ Time : {now.strftime('%H:%M')}

📢 Join For More
"""

# ================= VIDEO FORWARD =================

@user.on(events.NewMessage)
async def forward_video(event):

    if str(event.chat_id) not in get_sources():
        return

    if not event.video:
        return

    duration=0

    if event.video.attributes:
        for a in event.video.attributes:
            if isinstance(a,DocumentAttributeVideo):
                duration=a.duration

    if duration < 480:
        return

    caption=make_caption()

    for dest in get_dests():

        try:

            await bot.send_file(dest,event.video,caption=caption)

            delay=get_setting("speed",3)
            await asyncio.sleep(delay)

        except FloodWaitError as e:

            print("FloodWait:",e.seconds)
            await asyncio.sleep(e.seconds)

        except Exception as e:

            print("Error:",e)

# ================= COMMANDS =================

@bot.on(events.NewMessage(pattern="/add_source"))
async def add_source(event):

    if event.sender_id not in ADMINS:
        return

    try:
        link=event.text.split()[1]

        with sqlite3.connect(DB) as db:
            db.execute("INSERT OR IGNORE INTO sources VALUES (?)",(link,))

        await event.reply("✅ Source Added")

    except:
        await event.reply("Use /add_source -100xxxx")

@bot.on(events.NewMessage(pattern="/add_dest"))
async def add_dest(event):

    if event.sender_id not in ADMINS:
        return

    try:
        link=event.text.split()[1]

        with sqlite3.connect(DB) as db:
            db.execute("INSERT OR IGNORE INTO dests VALUES (?)",(link,))

        await event.reply("🎯 Destination Added")

    except:
        await event.reply("Use /add_dest -100xxxx")

@bot.on(events.NewMessage(pattern=r"/speed (\d+)"))
async def speed(event):

    if event.sender_id not in ADMINS:
        return

    s=int(event.pattern_match.group(1))

    set_setting("speed",s)

    await event.reply(f"⚡ Delay set to {s} sec")

# ================= START =================

async def main():

    init_db()

    await user.start()
    await bot.start(bot_token=BOT_TOKEN)

    print("🚀 Forwarder Running")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

if __name__=="__main__":
    asyncio.run(main())
