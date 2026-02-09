import os
import asyncio
import random
import string
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError
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
def home(): return "Mass Report System: Online"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
LOG_CHANNEL = -1003704307588 # Updated Log Channel ID
OWNER_USERNAME = "SANATANI_GOJO" 
SESSIONS = [s.strip() for s in os.environ.get("SESSIONS", "").split(",") if s.strip()]

db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_pro_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- REASONS ---
REASONS = [
    InputReportReasonSpam(),
    InputReportReasonViolence(),
    InputReportReasonChildAbuse(),
    InputReportReasonCopyright(),
    InputReportReasonOther()
]

# --- KEYBOARDS ---
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("🚀 Launch Extreme Attack", callback_data="attack_info")],
        [InlineKeyboardButton("💳 Buy Subscription", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("📊 My Account", callback_data="my_stats")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Gen 30-Day Key", callback_data="gen_key")])
    return InlineKeyboardMarkup(buttons)

# --- HANDLERS ---
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        f"🔥 **Mass Reporting Service Pro v6.0**\n\n"
        f"Active Nodes: `{len(SESSIONS)}` | Logs: `Enabled` ✅",
        reply_markup=main_menu(message.from_user.id)
    )

@bot.on_callback_query()
async def cb_handler(client, query):
    await query.answer()
    if query.data == "attack_info":
        await query.edit_message_text(
            "📝 **Attack Format**\n\nUse: `/report @username` or link.\n"
            "Bot will auto-join (if possible) and send 5 reports per ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]])
        )
    elif query.data == "home":
        await query.edit_message_text("Main Menu Selection:", reply_markup=main_menu(query.from_user.id))

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    # Subscription Check
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        if message.from_user.id != ADMIN_ID:
            return await message.reply("🚫 **Subscription Required!**")

    if len(message.command) < 2:
        return await message.reply("❌ Use: `/report [LINK/USERNAME]`")

    target_input = message.command[1].replace("[", "").replace("]", "")
    target_clean = target_input.replace("@", "").split("/")[-1]
    
    if target_clean.lower() == OWNER_USERNAME.lower():
        return await message.reply("Beta, admin ko report nahi marte! 😂🖕")

    status_msg = await message.reply(f"🚀 **Attack Initialized!**\nTarget: `@{target_clean}`\nNodes: `{len(SESSIONS)}` IDs")

    success_ids = 0
    total_hits = 0
    log_details = ""

    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # 1. AUTO-JOIN (Best for Groups/Channels)
                join_status = "Skipped/Personal"
                try:
                    await acc.join_chat(target_input)
                    join_status = "Joined ✅"
                except: pass

                # 2. RESOLVE PEER
                try:
                    user_entity = await acc.get_users(target_clean)
                    peer = await acc.resolve_peer(user_entity.id)
                except:
                    peer = await acc.resolve_peer(target_clean)

                # 3. HEAVY REPORTING (5 Reasons)
                for r in REASONS:
                    await acc.invoke(Report(peer=peer, id=[0], reason=r, message="Severe Violation"))
                    total_hits += 1
                
                success_ids += 1
                log_details += f"🔹 **Node {i}:** {join_status} | 5 Reports ✅\n"

        except Exception as e:
            log_details += f"🔸 **Node {i}:** Failed ({type(e).__name__})\n"
            continue

    # --- SENDING LOGS TO CHANNEL ---
    log_report = (
        f"📊 **Attack Summary Report**\n\n"
        f"👤 **Executor:** {message.from_user.mention}\n"
        f"🎯 **Target:** `@{target_clean}`\n"
        f"✅ **Success IDs:** `{success_ids}/{len(SESSIONS)}`\n"
        f"💥 **Total Reports Hit:** `{total_hits}`\n\n"
        f"📜 **Node Logs:**\n{log_details}"
    )
    
    try:
        await bot.send_message(LOG_CHANNEL, log_report)
    except Exception: pass

    await status_msg.edit(f"🏁 **Extreme Attack Finished!**\n\nTotal Hits: `{total_hits}`\nCheck Detailed Logs in Channel.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
