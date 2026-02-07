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
import motor.motor_asyncio

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Pro Report Bot is Online!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
SUPPORT_USER = os.environ.get("SUPPORT_USER", "AdminUsername")
SESSIONS_RAW = os.environ.get("SESSIONS", "")
SESSIONS = [s.strip() for s in SESSIONS_RAW.split(",") if s.strip()]

# --- DATABASE SETUP ---
db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- KEYBOARDS ---
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("🚀 Launch Attack", callback_data="attack_info")],
        [InlineKeyboardButton("💳 Buy Subscription", url=f"https://t.me/{SUPPORT_USER}")],
        [InlineKeyboardButton("📊 My Account", callback_data="my_stats")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Generate 30-Day Key", callback_data="gen_key")])
    return InlineKeyboardMarkup(buttons)

# --- COMMANDS & HANDLERS ---

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    welcome_text = (
        "🔥 **Mass Reporting Service Pro**\n\n"
        f"Connected IDs: `{len(SESSIONS)}` Accounts\n"
        "System Status: `Active` ✅\n\n"
        "Choose an option from the menu:"
    )
    await message.reply_text(welcome_text, reply_markup=main_menu(message.from_user.id))

@bot.on_callback_query()
async def cb_handler(client, query):
    if query.data == "attack_info":
        await query.message.edit_text(
            "📝 **How to Start?**\n\n"
            "Send the command in this format:\n"
            "`/report [TARGET_LINK_OR_USERNAME]`\n\n"
            "Example: `/report @username`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        )

    elif query.data == "my_stats":
        user_data = await subs_col.find_one({"user_id": query.from_user.id})
        if user_data:
            expiry = user_data["expiry"].strftime("%Y-%m-%d %H:%M")
            await query.answer(f"✅ Active Access\nExpires: {expiry}", show_alert=True)
        else:
            await query.answer("❌ No Subscription Found!", show_alert=True)

    elif query.data == "gen_key":
        if query.from_user.id != ADMIN_ID: return
        key = ''.join(random.choices(string.digits, k=6))
        expiry_date = datetime.now() + timedelta(days=30)
        await subs_col.insert_one({"auth_key": key, "expiry": expiry_date, "claimed": False})
        await query.message.reply_text(f"🔑 **1-Month Key Generated:**\n\n`{key}`\n\nCommand: `/redeem {key}`")

    elif query.data == "home":
        await query.message.edit_text("Main Menu Selection:", reply_markup=main_menu(query.from_user.id))

@bot.on_message(filters.command("redeem"))
async def redeem_key(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Use: `/redeem 123456`")
    
    input_key = message.command[1]
    key_data = await subs_col.find_one({"auth_key": input_key, "claimed": False})
    
    if key_data:
        await subs_col.update_one({"auth_key": input_key}, {"$set": {"claimed": True, "user_id": message.from_user.id}})
        await message.reply("✅ **Subscription Activated!**\nAccess granted for 30 days.")
    else:
        await message.reply("🚫 Invalid or Expired Key.")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    # Subscription Check
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        return await message.reply("🚫 **Access Denied!**\nActive subscription required.")

    if len(message.command) < 2:
        return await message.reply("❌ Use: `/report [LINK]`")

    target = message.command[1]
    status_msg = await message.reply(f"🚀 **Attack Initialized!**\nTarget: `{target}`\nTotal IDs: `{len(SESSIONS)}`")

    # Mass Reporting Logic
    successful = 0
    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # Corrected Raw Import Usage
                await acc.report_peer(peer=target, reason=InputReportReasonSpam())
                successful += 1
            if i % 2 == 0:
                await status_msg.edit(f"🔄 **In Progress...**\nSuccess: `{successful}/{len(SESSIONS)}` reports.")
            await asyncio.sleep(1) 
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass

    await status_msg.edit(f"🏁 **Attack Finished!**\n\n✅ Total Successful: `{successful}`\n🎯 Target: `{target}`")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
