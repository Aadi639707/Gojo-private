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
def home(): return "Health Check System: Online"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
LOG_CHANNEL = -1003704307588 
OWNER_USERNAME = "SANATANI_GOJO" 
SESSIONS = [s.strip() for s in os.environ.get("SESSIONS", "").split(",") if s.strip()]

db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client["report_pro_service"]
subs_col = db["users"]

bot = Client("MassReportBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

REASONS = [InputReportReasonSpam(), InputReportReasonViolence(), InputReportReasonChildAbuse(), InputReportReasonCopyright(), InputReportReasonOther()]

# --- HANDLERS ---
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("🔥 **Mass Reporting Pro v6.5**\nSystem Status: `Ready` ✅")

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
    
    status_msg = await message.reply(f"🚀 **Attack Initialized!**\nTarget: `@{target_clean}`\nCheck Logs for ID health.")

    success_ids = 0
    total_hits = 0
    log_details = ""

    for i, session in enumerate(SESSIONS):
        node_status = "Healthy ✅"
        join_info = "N/A"
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # 1. Join Logic
                try:
                    await acc.join_chat(target_input)
                    join_info = "Joined"
                except: join_info = "Skipped"

                # 2. Resolve & Report
                try:
                    user_entity = await acc.get_users(target_clean)
                    peer = await acc.resolve_peer(user_entity.id)
                except:
                    peer = await acc.resolve_peer(target_clean)

                for r in REASONS:
                    await acc.invoke(Report(peer=peer, id=[0], reason=r, message="Violation Report"))
                    total_hits += 1
                
                success_ids += 1
                log_details += f"🆔 **Node {i}:** {node_status} | {join_info} | 5 Hits\n"

        except Exception as e:
            err = type(e).__name__
            log_details += f"🆔 **Node {i}:** Dead ❌ ({err})\n"
            continue

    # --- SENDING PRIVATE LOGS ---
    log_report = (
        f"📋 **Detailed Attack Report**\n\n"
        f"👤 **Admin:** {message.from_user.mention}\n"
        f"🎯 **Target:** `@{target_clean}`\n"
        f"✅ **Success IDs:** `{success_ids}/{len(SESSIONS)}`\n"
        f"💥 **Total Reports:** `{total_hits}`\n\n"
        f"🩺 **Node Health Check:**\n{log_details}"
    )
    
    try:
        await bot.send_message(LOG_CHANNEL, log_report)
    except:
        await message.reply("⚠️ **Log Error:** Bot is not Admin in Log Channel!")

    await status_msg.edit(f"🏁 **Finished!**\nTotal Reports Sent: `{total_hits}`\n*Logs sent to Private Channel.*")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
