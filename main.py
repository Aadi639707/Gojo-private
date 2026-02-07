import os
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputReportReasonSpam
import motor.motor_asyncio

# --- RENDER FAKE SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot UI Active!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
SESSIONS = [s.strip() for s in os.environ.get("SESSIONS", "").split(",") if s.strip()]

db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_bot"]
codes_col = db["access_codes"]

bot = Client("ReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- KEYBOARDS ---
MAIN_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🚀 Start Reporting", callback_data="ask_report")],
    [InlineKeyboardButton("🔑 Generate Access Code (Admin)", callback_data="gen_code")],
    [InlineKeyboardButton("📊 Bot Status", callback_data="bot_stats")]
])

# --- HANDLERS ---

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_photo(
        photo="https://graph.org/file/f833503f56360c4068571.jpg", # Ek cool image link
        caption=f"👋 **Welcome to Multi-Account Reporter!**\n\nTotal Connected IDs: `{len(SESSIONS)}`",
        reply_markup=MAIN_MARKUP
    )

@bot.on_callback_query()
async def callback_handler(client, query):
    if query.data == "ask_report":
        await query.message.edit_caption(
            caption="📝 **Kaise Report Karein?**\n\nNiche diye gaye format mein message bhejein:\n\n`/report [CODE] [TARGET_LINK]`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]])
        )
    
    elif query.data == "gen_code":
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Aap Admin nahi hain!", show_alert=True)
            return
        import random, string
        new_code = '-'.join([''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)])
        await codes_col.insert_one({"code": new_code})
        await query.message.edit_caption(
            caption=f"✅ **New Access Code Generated:**\n\n`{new_code}`\n\nIse user ko dein reporting start karne ke liye.",
            reply_markup=MAIN_MARKUP
        )

    elif query.data == "bot_stats":
        await query.answer(f"Status: Working\nIDs: {len(SESSIONS)}\nUptime: 100%", show_alert=True)

    elif query.data == "back_home":
        await query.message.edit_caption(caption="Main Menu Selection:", reply_markup=MAIN_MARKUP)

@bot.on_message(filters.command("report"))
async def report_logic(client, message):
    args = message.text.split(" ")
    if len(args) < 3:
        await message.reply("Format: `/report [CODE] [LINK]`")
        return

    code_input, target = args[1], args[2]
    
    # Code Validation
    if not await codes_col.find_one({"code": code_input}):
        await message.reply("🚫 Invalid or Used Code!")
        return

    status = await message.reply(f"⚡ **Initiating Attack...**\nTarget: `{target}`")
    
    success = 0
    for i, sess in enumerate(SESSIONS):
        try:
            await status.edit(f"🔄 **Reporting...**\nAccount `{i+1}` is hitting the target.")
            async with Client(f"acc_{i}", api_id=API_ID, api_hash=API_HASH, session_string=sess) as acc:
                await acc.report_peer(peer=target, reason=InputReportReasonSpam)
                success += 1
            await asyncio.sleep(1.5) # Protection delay
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass

    await codes_col.delete_one({"code": code_input})
    await status.edit(f"🏁 **Task Completed!**\n\n✅ Reports Sent: `{success}`\n🎯 Target: `{target}`\n🔑 Code Expired.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
      
