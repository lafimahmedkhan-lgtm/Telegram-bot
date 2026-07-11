import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ==========================================
# ⚙️ SYSTEM CONFIGURATION
# ==========================================
DURIAN_API_KEY = "a1R6QWJzOUNiME43SGV3em03cE9VZz09"
BOT_TOKEN = "8819748603:AAE6wE1MyIB0HUYGoZd7A29GJsp3Z3gbIsE"
GROUP_CHAT_ID = "-1003689624674"

BASE_URL = "https://mm.durianrcs.com/api"

# Logging setup for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Global State Management
class SystemState:
    def __init__(self):
        self.is_running = False
        self.total_fetched = 0
        self.total_otp_success = 0
        self.active_tasks = []

state = SystemState()

# ==========================================
# 🎮 TELEGRAM BOT HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Command Panel"""
    status_emoji = "🟢 RUNNING" if state.is_running else "🔴 STOPPED"
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 Start Engine", callback_data='engine_start'),
            InlineKeyboardButton("⏹ Stop Engine", callback_data='engine_stop')
        ],
        [
            InlineKeyboardButton("💰 Check Balance", callback_data='check_balance'),
            InlineKeyboardButton("📊 System Stats", callback_data='system_stats')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        "🔥 **DURIAN RCS ADVANCED AUTO-OTP SYSTEM** 🔥\n\n"
        f"⚡ **Status:** {status_emoji}\n"
        f"📱 **Total Numbers Processed:** `{state.total_fetched}`\n"
        f"✅ **Successful OTPs Forwarded:** `{state.total_otp_success}`\n\n"
        "নিচের বোতামগুলো দিয়ে সিস্টেম নিয়ন্ত্রণ করুন:"
    )
    
    if update.message:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'engine_start':
        if not state.is_running:
            state.is_running = True
            # Fire up async background engine worker
            asyncio.create_task(otp_worker_engine(context))
            await query.edit_message_text(
                "🚀 **Engine Started!**\n\nপ্যানেল থেকে আনলিমিটেড অটো ওটিপি এনে আপনার নির্দিষ্ট টেলিগ্রাম গ্রুপে পাঠানো শুরু হয়েছে...",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("⚠️ **Engine is already running!**", parse_mode='Markdown')

    elif query.data == 'engine_stop':
        state.is_running = False
        await query.edit_message_text(
            "🛑 **Engine Stopped!**\n\nনতুন কোনো নাম্বার তোলা বা প্রসেস করা বন্ধ রয়েছে।",
            parse_mode='Markdown'
        )

    elif query.data == 'check_balance':
        try:
            res = requests.get(f"{BASE_URL}/user/balance?token={DURIAN_API_KEY}", timeout=10).json()
            balance = res.get('data', {}).get('balance', 'N/A')
            await query.edit_message_text(
                f"💎 **Durian RCS Panel Balance:** `{balance}` Coins\n\n"
                "কন্ট্রোল প্যানেলে ফিরতে /start লিখুন।",
                parse_mode='Markdown'
            )
        except Exception:
            await query.edit_message_text("❌ API এর সাথে কানেক্ট করা সম্ভব হয়নি!", parse_mode='Markdown')

    elif query.data == 'system_stats':
        await query.edit_message_text(
            f"📊 **LIVE SYSTEM STATS** 📊\n\n"
            f"🔹 Engine Status: `{'ACTIVE' if state.is_running else 'INACTIVE'}`\n"
            f"🔹 Total Orders Initiated: `{state.total_fetched}`\n"
            f"🔹 Successful OTPs: `{state.total_otp_success}`\n\n"
            "কন্ট্রোল প্যানেলে ফিরতে /start টাইপ করুন।",
            parse_mode='Markdown'
        )

# ==========================================
# ⚙️ HIGH-SPEED OTP WORKER ENGINE
# ==========================================
async def process_single_number(context: ContextTypes.DEFAULT_TYPE):
    """Handles an individual order cycle asynchronously"""
    try:
        # Step 1: Request Phone Number from Durian RCS API
        req_url = f"{BASE_URL}/getPhone?token={DURIAN_API_KEY}&service=telegram"
        res = await asyncio.to_thread(requests.get, req_url, timeout=10)
        json_data = res.json()

        if json_data.get('code') == 200:
            phone_number = json_data.get('data', {}).get('phone')
            order_id = json_data.get('data', {}).get('order_id')
            state.total_fetched += 1

            logging.info(f"New Number Acquired: {phone_number} | Order ID: {order_id}")

            # Step 2: Poll for OTP with a 2-minute timeout
            poll_attempts = 0
            max_attempts = 40  # 40 attempts * 3 sec sleep = 120 sec total wait time

            while poll_attempts < max_attempts and state.is_running:
                await asyncio.sleep(3)
                poll_attempts += 1

                msg_url = f"{BASE_URL}/getMessage?token={DURIAN_API_KEY}&order_id={order_id}"
                msg_res = await asyncio.to_thread(requests.get, msg_url, timeout=10)
                msg_data = msg_res.json()

                if msg_data.get('code') == 200 and msg_data.get('data', {}).get('sms'):
                    otp_text = msg_data.get('data', {}).get('sms')
                    state.total_otp_success += 1

                    # Step 3: Format and Broadcast to Telegram Group
                    broadcast_card = (
                        "⚡ **NEW TELEGRAM OTP RECEIVED** ⚡\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 **Phone:** `{phone_number}`\n"
                        f"🔑 **OTP Code:** `{otp_text}`\n"
                        f"🆔 **Order ID:** `{order_id}`\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "💎 *Powered by Premium Auto Stream*"
                    )
                    
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=broadcast_card,
                        parse_mode='Markdown'
                    )
                    logging.info(f"OTP Delivered successfully for {phone_number}")
                    return

            # Step 4: Auto-Cancel Order if OTP is NOT received within timeout
            cancel_url = f"{BASE_URL}/cancelOrder?token={DURIAN_API_KEY}&order_id={order_id}"
            await asyncio.to_thread(requests.get, cancel_url, timeout=5)
            logging.info(f"Order {order_id} timed out and auto-cancelled.")

    except Exception as err:
        logging.error(f"Error processing number: {err}")

async def otp_worker_engine(context: ContextTypes.DEFAULT_TYPE):
    """Main Loop to keep generating requests as long as Engine is ON"""
    while state.is_running:
        # Runs tasks asynchronously so multiple numbers can be checked at the same time
        asyncio.create_task(process_single_number(context))
        # Interval delay between new number requests (adjust if needed)
        await asyncio.sleep(2)

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT
# ==========================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands & Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_click_handler))

    logging.info("Bot is starting successfully...")
    app.run_polling()

if __name__ == '__main__':
    main()
