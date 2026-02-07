import os
import asyncio
import random
import string
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.types import InputReportReasonSpam
from pyrogram.raw.functions.messages import Report
import motor.motor_asyncio

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Pro Bot Online"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
OWNER_USERNAME = "SANATANI_GOJO" 
SESSIONS_RAW = os.environ.get("SESSIONS", "")
SESSIONS = [s.strip() for s in SESSIONS_RAW.split(",") if s.strip()]

db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_pro_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- KEYBOARDS ---
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("🚀 Launch Attack", callback_data="attack_info")],
        [InlineKeyboardButton("💳 Buy Plan", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("📊 Account Status", callback_data="my_stats")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Gen 30-Day Key", callback_data="gen_key")])
    return InlineKeyboardMarkup(buttons)

# --- HANDLERS ---
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("🔥 **Mass Report Pro**\n\nSystem: `Operational` ✅", reply_markup=main_menu(message.from_user.id))

@bot.on_callback_query()
async def cb_handler(client, query):
    if query.data == "attack_info":
        await query.message.edit_text("📝 Use: `/report @username`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))
    elif query.data == "gen_key":
        if query.from_user.id != ADMIN_ID: return
        key = ''.join(random.choices(string.digits, k=6))
        await subs_col.insert_one({"auth_key": key, "expiry": datetime.now() + timedelta(days=30), "claimed": False})
        await query.message.reply_text(f"🔑 **Key:** `{key}`")
    elif query.data == "home":
        await query.message.edit_text("Menu:", reply_markup=main_menu(query.from_user.id))

@bot.on_message(filters.command("redeem"))
async def redeem_key(client, message):
    if len(message.command) < 2: return
    key_data = await subs_col.find_one({"auth_key": message.command[1], "claimed": False})
    if key_data:
        await subs_col.update_one({"auth_key": message.command[1]}, {"$set": {"claimed": True, "user_id": message.from_user.id}})
        await message.reply("✅ **Premium Activated!**")
    else:
        await message.reply("🚫 Invalid Key!")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        return await message.reply("🚫 **Subscription Required!**")

    if len(message.command) < 2: return await message.reply("❌ Use: `/report @username`")

    target = message.command[1].replace("[", "").replace("]", "").replace("@", "")
    
    if target.lower() == OWNER_USERNAME.lower():
        return await message.reply("Beta, baap ko report maarega? Apni mummy se pooch kaun hoon main! 🖕😂")

    status_msg = await message.reply(f"🚀 **Starting...**\nTarget: `@{target}`")

    successful = 0
    errors = []

    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # FIXED: Peer resolution + initialized Reason
                peer = await acc.resolve_peer(target)
                await acc.invoke(Report(peer=peer, id=[0], reason=InputReportReasonSpam(), message="Spam"))
                successful += 1
            await asyncio.sleep(1)
        except Exception as e:
            err_name = type(e).__name__
            if err_name not in errors: errors.append(err_name)

    final_report = f"🏁 **Attack Finished!**\n\n✅ Success: `{successful}`\n🎯 Target: `@{target}`"
    if successful == 0 and errors:
        final_report += f"\n\n❌ **Error Detected:** `{errors[0]}`"
    
    await status_msg.edit(final_report)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
