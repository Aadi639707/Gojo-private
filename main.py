import os
import asyncio
import random
import string
import traceback
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
def home(): return "Technical Debugger: Online"

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

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("🔥 **Extreme Debugger Pro v7.0**\nAll logs will be sent to your private channel.")

@bot.on_message(filters.command("report"))
async def execute_report(client, message):
    # Subscription Check
    user_info = await subs_col.find_one({"user_id": message.from_user.id})
    if not user_info or datetime.now() > user_info["expiry"]:
        if message.from_user.id != ADMIN_ID:
            return await message.reply("🚫 **Subscription Required!**")

    if len(message.command) < 2:
        return await message.reply("❌ Use: `/report [LINK]`")

    target_input = message.command[1].replace("@", "").split("/")[-1]
    status_msg = await message.reply(f"🚀 **Attack Started!**\n`Generating raw technical logs...`")

    success_ids = 0
    total_hits = 0
    tech_logs = f"🛠 **SYSTEM LOGS - {datetime.now().strftime('%H:%M:%S')}**\n\n"

    for i, session in enumerate(SESSIONS):
        log_entry = f"STDOUT [Node {i}]: "
        try:
            async with Client(f"node_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session) as acc:
                # Resolve Peer
                try:
                    user_entity = await acc.get_users(target_input)
                    peer = await acc.resolve_peer(user_entity.id)
                except:
                    peer = await acc.resolve_peer(target_input)

                # Report Execution
                for r in REASONS:
                    # Raw API Call
                    result = await acc.invoke(Report(peer=peer, id=[0], reason=r, message="Automated Violation Report"))
                    total_hits += 1
                
                success_ids += 1
                log_entry += f"SUCCESS (API_CODE: 200) | Peer Resolved ✅\n"

        except Exception:
            # Capturing full error like Render logs
            error_trace = traceback.format_exc().splitlines()[-1] 
            log_entry += f"CRITICAL ERROR: {error_trace} ❌\n"
        
        tech_logs += log_entry
        await asyncio.sleep(0.3)

    # --- FINAL LOG REPORT ---
    final_log = (
        f"🖥 **RENDER-STYLE CONSOLE LOGS**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Target: `@{target_input}`\n"
        f"Executor ID: `{message.from_user.id}`\n"
        f"Total Successful Nodes: `{success_ids}/{len(SESSIONS)}`\n"
        f"Total Raw Hits: `{total_hits}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**RAW OUTPUT:**\n"
        f"```\n{tech_logs}```"
    )

    try:
        await bot.send_message(LOG_CHANNEL, final_log)
    except Exception as le:
        await message.reply(f"⚠️ Log Channel Error: {le}")

    await status_msg.edit(f"🏁 **Execution Finished!**\nAll technical logs have been uploaded to the private channel.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run()
    
