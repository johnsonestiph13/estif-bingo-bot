# ========== FLASK WEB SERVER FOR RENDER ==========
from flask import Flask
import threading
import os

flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "✅ Estif Bingo Bot is alive!", 200

def run_webserver():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_webserver, daemon=True).start()

# ========== IMPORTS ==========
import logging
import json
import random
import re
from datetime import datetime

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

# ========== CONFIG ==========
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_CHAT_ID = "YOUR_ADMIN_ID"

GAME_WEB_URL = "https://estif-bingo-247.onrender.com/player.html"

PAYMENT_ACCOUNTS = {
    "CBE": "1000179576997",
    "ABBISINIYA": "35241051",
    "TELEBIRR": "0987713787",
    "MPESA": "0722345146"
}

ACCOUNT_HOLDER = "Estifanos Yhannis"

logging.basicConfig(level=logging.INFO)

# ========== DB ==========
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE))
    return {}

def save_db(db):
    json.dump(db, open(DB_FILE, "w"), indent=2)

def get_user(uid):
    return load_db().get(str(uid))

def save_user(uid, data):
    db = load_db()
    db[str(uid)] = data
    save_db(db)

# ========== FLOW SYSTEM ==========
def reset_flow(context):
    context.user_data['flow'] = None
    context.user_data['step'] = None
    context.user_data['data'] = {}

# ========== MENU ==========
def menu():
    return ReplyKeyboardMarkup([
        ["🎮 Play", "📝 Register", "💰 Deposit"],
        ["💳 Cash Out", "📞 Contact Center", "🎉 Invite"]
    ], resize_keyboard=True)

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    await update.message.reply_text("🎉 Welcome!", reply_markup=menu())

# ========== REGISTER ==========
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    user = update.effective_user
    save_user(user.id, {
        "balance": 0,
        "total_deposited": 0,
        "pending_withdrawals": []
    })
    await update.message.reply_text("✅ Registered!", reply_markup=menu())

# ========== PLAY ==========
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    await update.message.reply_text(f"🎮 Play:\n{GAME_WEB_URL}")

# ========== DEPOSIT ==========
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    keyboard = [[InlineKeyboardButton(k, callback_data=f"dep_{k}")] for k in PAYMENT_ACCOUNTS]
    await update.message.reply_text("Choose method:", reply_markup=InlineKeyboardMarkup(keyboard))

async def deposit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method = query.data.split("_")[1]
    reset_flow(context)

    context.user_data['flow'] = 'deposit'
    context.user_data['step'] = 'amount'
    context.user_data['data'] = {'method': method}

    await query.edit_message_text(f"{method} selected. Enter amount:")

# ========== CASHOUT ==========
async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    keyboard = [[InlineKeyboardButton(k, callback_data=f"cash_{k}")] for k in PAYMENT_ACCOUNTS]
    await update.message.reply_text("Choose withdrawal method:", reply_markup=InlineKeyboardMarkup(keyboard))

async def cashout_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method = query.data.split("_")[1]
    reset_flow(context)

    context.user_data['flow'] = 'cashout'
    context.user_data['step'] = 'amount'
    context.user_data['data'] = {'method': method}

    await query.edit_message_text(f"{method} selected. Enter amount:")

# ========== UNIVERSAL TEXT ==========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data.get('flow')
    step = context.user_data.get('step')
    text = update.message.text

    if not flow:
        await update.message.reply_text("Use menu", reply_markup=menu())
        return

    nums = re.findall(r"\d+\.?\d*", text)
    if not nums:
        await update.message.reply_text("Enter valid number")
        return

    amount = float(nums[0])

    # ===== DEPOSIT =====
    if flow == 'deposit':
        if step == 'amount':
            context.user_data['data']['amount'] = amount
            context.user_data['step'] = 'photo'
            await update.message.reply_text("Send screenshot")
            return

    # ===== CASHOUT =====
    if flow == 'cashout':
        user = get_user(update.effective_user.id)
        if step == 'amount':
            if amount > user.get("balance", 0):
                await update.message.reply_text("Not enough balance")
                return

            context.user_data['data']['amount'] = amount
            context.user_data['step'] = 'account'
            await update.message.reply_text("Enter account number")
            return

        if step == 'account':
            acc = text.strip()
            data = context.user_data['data']

            user['pending_withdrawals'].append({
                "amount": data['amount'],
                "account": acc
            })
            save_user(update.effective_user.id, user)

            await update.message.reply_text("✅ Cashout requested", reply_markup=menu())
            reset_flow(context)

# ========== PHOTO ==========
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('flow') != 'deposit':
        return

    await update.message.reply_text("✅ Deposit sent", reply_markup=menu())
    reset_flow(context)

# ========== MAIN ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.Regex("🎮 Play"), play))
    app.add_handler(MessageHandler(filters.Regex("📝 Register"), register))
    app.add_handler(MessageHandler(filters.Regex("💰 Deposit"), deposit))
    app.add_handler(MessageHandler(filters.Regex("💳 Cash Out"), cashout))

    app.add_handler(CallbackQueryHandler(deposit_cb, pattern="dep_"))
    app.add_handler(CallbackQueryHandler(cashout_cb, pattern="cash_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🤖 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()