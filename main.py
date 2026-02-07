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

# --- WEB SERVER FOR RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Pro Report Bot is Active!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
# Aapka Username
OWNER_USERNAME = "SANATANI_GOJO" 
SESSIONS_RAW = os.environ.get("SESSIONS", "")
SESSIONS = [s.strip() for s in SESSIONS_RAW.split(",") if s.strip()]

# --- DATABASE ---
db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_pro_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- KEYBOARDS ---
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("🚀 Launch Attack", callback_data="attack_info")],
        [InlineKeyboardButton("💳 Buy Plan / Support", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("📊 Subscription Info", callback_data="my_stats")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Gen 30-Day Key", callback_data="gen_key")])
    return InlineKeyboardMarkup(buttons)

# --- HANDLERS ---

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        "🔥 **Mass Reporting Service Pro v3.0**\n\n"
        f"Total Nodes: `{len(SESSIONS)}` IDs Connected\n"
        "System Status: `Secured` 🛡️\n\n"
        "Click below to start:",
        reply_markup=main_menu(message.from_user.id)
    )

@bot.on_callback_query()
async def cb_handler(client, query):
    if query.data == "attack_info":
        await query.message.edit_text(
            "📝 **How to Start?**\n\nUse command: `/report [TARGET_LINK]`\n\nExample: `/report @username`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        )
    elif query.data == "gen_key":
        if query.from_user.id != ADMIN_ID: return
        key = ''.join(random.choices(string.digits, k=6))
        expiry = datetime.now() + timedelta(days=30)
        await subs_col.insert_one({"auth_key": key, "expiry": expiry, "claimed": False})
        await query.message.reply_text(f"🔑 **30-Day Key:** `{key}`\nUse: `/redeem {key}`")
    elif query.data == "home":
        await query.message.edit_text("Main Menu Selection:", reply_markup=main_menu(query.from_user.id))

@bot.on_message(filters.command("redeem"))
async def redeem_key(client, message):
    if len(message.command) < 2: return await message.reply("❌ Use: `/redeem 123456`")
    key_data = await subs_col.find_one({"auth_key": message.command[1], "claimed": False})
    if key_data:
        await subs_col.update_one({"auth_key": message.command[1]}, {"$set": {"claimed": True, "user_id": message.from_user.id}})
        await message.reply("✅ **Premium Activated!** (30 Days)")
    else:
        await message.reply("🚫 Invalid Key!")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    # Subscription Check
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        return await message.reply("🚫 **Subscription Required!**")

    if len(message.command) < 2:
        return await message.reply("❌ Use: `/report [LINK]`")

    target = message.command[1].replace("[", "").replace("]", "").replace("@", "")
    
    # --- ANTI-SELF REPORT LOGIC (Funny Roast) ---
    if target.lower() == OWNER_USERNAME.lower():
        roasts = [
            "Beta, baap ko report maarega? Apni mummy se pooch kaun hoon main! 🖕😂",
            "Aukat mein reh bhikhari, admin ko report karne chala hai? Nikal yahan se! 🤡",
            "Report tere dimaag pe maarni chahiye, jo apne hi admin ka handle daal raha hai. 🧠💨",
            "Error 404: Your brain not found. Admin ko report karna mana hai, gadhe! 🚫🤣"
        ]
        return await message.reply(random.choice(roasts))

    status_msg = await message.reply(f"🚀 **Initializing Attack...**\nTarget: `@{target}`")

    successful = 0
    errors = []

    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                await acc.report_peer(peer=target, reason=InputReportReasonSpam())
                successful += 1
            if i % 3 == 0:
                await status_msg.edit(f"🔄 **Reporting...**\nProgress: `{successful}/{len(SESSIONS)}` Done.")
            await asyncio.sleep(1)
        except Exception as e:
            err_name = type(e).__name__
            if err_name not in errors: errors.append(err_name)
            continue

    final_report = f"🏁 **Attack Finished!**\n\n✅ Success: `{successful}`\n🎯 Target: `@{target}`"
    if successful == 0 and errors:
        final_report += f"\n\n❌ **Error Detected:** `{errors[0]}`\n*(Check your IDs or target link)*"
    
    await status_msg.edit(final_report)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
