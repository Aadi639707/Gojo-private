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
from pyrogram.raw.functions.channels import JoinChannel
import motor.motor_asyncio

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Log System Online"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
LOG_CHANNEL = -1003704307588 # Aapka Log Channel ID
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

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(f"🔥 **Mass Report v6.0**\nLog Channel: `Active` ✅")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        if message.from_user.id != ADMIN_ID:
            return await message.reply("🚫 Subscription Required!")

    if len(message.command) < 2:
        return await message.reply("❌ Use: `/report [LINK/USERNAME]`")

    target_input = message.command[1].replace("[", "").replace("]", "")
    target_clean = target_input.replace("@", "").split("/")[-1]
    
    if target_clean.lower() == OWNER_USERNAME.lower():
        return await message.reply("Beta, admin ko report nahi marte! 😂")

    status_msg = await message.reply(f"🚀 **Attack Started!**\nTarget: `@{target_clean}`\nJoining & Reporting...")

    success_count = 0
    total_reports = 0
    log_details = ""

    for i, session in enumerate(SESSIONS):
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # 1. AUTO-JOIN LOGIC
                try:
                    await acc.join_chat(target_input)
                    join_status = "Joined ✅"
                except Exception:
                    join_status = "Already in/Failed ❌"

                # 2. RESOLVE PEER & REPORT
                peer = await acc.resolve_peer(target_clean)
                id_hits = 0
                for r in REASONS:
                    await acc.invoke(Report(peer=peer, id=[0], reason=r, message="Severe Violation"))
                    id_hits += 1
                    total_reports += 1
                
                success_count += 1
                log_details += f"🔹 **Node {i}:** {join_status} | {id_hits} Reports\n"

        except Exception as e:
            log_details += f"🔸 **Node {i}:** Failed ({type(e).__name__})\n"
            continue

    # --- SENDING LOGS TO CHANNEL ---
    log_text = (
        f"📊 **Attack Log Report**\n\n"
        f"👤 **User:** {message.from_user.mention}\n"
        f"🎯 **Target:** `@{target_clean}`\n"
        f"✅ **Success IDs:** `{success_count}/{len(SESSIONS)}`\n"
        f"💥 **Total Hits:** `{total_reports}`\n\n"
        f"📜 **Details:**\n{log_details}"
    )
    
    try:
        await bot.send_message(LOG_CHANNEL, log_text)
    except Exception as le:
        print(f"Log Error: {le}")

    await status_msg.edit(f"🏁 **Attack Finished!**\n\nTotal Reports: `{total_reports}`\nCheck Logs: [Click Here](https://t.me/c/3704307588/1)")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
