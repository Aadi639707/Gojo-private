import os
import asyncio
import random
import string
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, PeerIdInvalid, UsernameInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.types import (
    InputReportReasonSpam, 
    InputReportReasonViolence, 
    InputReportReasonChildAbuse, 
    InputReportReasonCopyright, 
    InputReportReasonOther
)
from pyrogram.raw.functions.messages import Report
import motor.motor_asyncio

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Universal Pro Bot is Online!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
OWNER_USERNAME = "SANATANI_GOJO" 
SESSIONS = [s.strip() for s in os.environ.get("SESSIONS", "").split(",") if s.strip()]

db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_pro_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- KEYBOARDS ---
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("🚀 Launch Extreme Attack", callback_data="attack_info")],
        [InlineKeyboardButton("💳 Buy Subscription", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("📊 My Account", callback_data="my_stats")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Generate 30-Day Key", callback_data="gen_key")])
    return InlineKeyboardMarkup(buttons)

# --- HANDLERS ---
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(f"🔥 **Mass Reporting Pro v5.0**\nActive IDs: `{len(SESSIONS)}`", reply_markup=main_menu(message.from_user.id))

@bot.on_callback_query()
async def cb_handler(client, query):
    if query.data == "attack_info":
        await query.message.edit_text("📝 Use: `/report @username` (No Brackets!)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))
    elif query.data == "home":
        await query.message.edit_text("Main Menu:", reply_markup=main_menu(query.from_user.id))

@bot.on_message(filters.command("redeem"))
async def redeem_key(client, message):
    if len(message.command) < 2: return
    key_data = await subs_col.find_one({"auth_key": message.command[1], "claimed": False})
    if key_data:
        await subs_col.update_one({"auth_key": message.command[1]}, {"$set": {"claimed": True, "user_id": message.from_user.id}})
        await message.reply("✅ Subscription Activated!")
    else: await message.reply("🚫 Invalid Key!")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        return await message.reply("🚫 Subscription Required!")

    if len(message.command) < 2: return await message.reply("❌ Use: `/report @username`")

    # Clean target (Removing brackets, @, and full links)
    target = message.command[1].replace("[", "").replace("]", "").replace("@", "").split("/")[-1]
    
    if target.lower() == OWNER_USERNAME.lower():
        return await message.reply("Beta, baap ko report maarega? 😂🖕")

    status_msg = await message.reply(f"🚀 **Targeting:** `@{target}`\nNodes Active: `{len(SESSIONS)}`")

    successful_ids = 0
    total_hits = 0
    reasons = [InputReportReasonSpam(), InputReportReasonViolence(), InputReportReasonChildAbuse(), InputReportReasonCopyright(), InputReportReasonOther()]

    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # ADVANCE PEER RESOLUTION (Works for IDs)
                try:
                    user_entity = await acc.get_users(target)
                    peer = await acc.resolve_peer(user_entity.id)
                except:
                    peer = await acc.resolve_peer(target)

                for r in reasons:
                    await acc.invoke(Report(peer=peer, id=[0], reason=r, message="Harassment and Violation"))
                    total_hits += 1
                successful_ids += 1
            await asyncio.sleep(0.5)
        except Exception: continue

    await status_msg.edit(f"🏁 **Finished!**\n\n✅ IDs: `{successful_ids}`\n💥 Hits: `{total_hits}`\n🎯 Target: `@{target}`")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
