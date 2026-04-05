# ========== FLASK WEB SERVER FOR RENDER ==========
from flask import Flask, request, jsonify
import threading
import os
import secrets
from datetime import datetime, timedelta

flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "✅ Estif Bingo Bot is alive!", 200

# ========== BINGO OTP SYSTEM ==========
# Store OTP codes with expiry
BINGO_OTP_STORE = {}  # {telegram_user_id: {'otp': '123456', 'expires': datetime}}

# OTP Configuration
OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6

def generate_otp():
    """Generate a 6-digit OTP"""
    return f"{secrets.randbelow(1000000):06d}"

def store_otp(telegram_user_id):
    """Generate and store OTP for a user"""
    otp = generate_otp()
    BINGO_OTP_STORE[str(telegram_user_id)] = {
        'otp': otp,
        'expires': datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    }
    return otp

def verify_otp(telegram_user_id, user_otp):
    """Verify OTP for a user"""
    record = BINGO_OTP_STORE.get(str(telegram_user_id))
    if not record:
        return False, "No OTP request found"
    
    if datetime.now() > record['expires']:
        del BINGO_OTP_STORE[str(telegram_user_id)]
        return False, "OTP expired (5 minutes)"
    
    if record['otp'] != user_otp:
        return False, "Invalid OTP"
    
    # OTP is valid, remove it (one-time use)
    del BINGO_OTP_STORE[str(telegram_user_id)]
    return True, "OTP verified"

# ========== FLASK API ENDPOINTS FOR NODE.JS SERVER ==========
@flask_app.route('/api/request-otp', methods=['POST'])
def api_request_otp():
    """Node.js server calls this to request OTP for a user"""
    data = request.json
    telegram_user_id = data.get('telegramUserId')
    phone = data.get('phone')
    
    if not telegram_user_id:
        return jsonify({'success': False, 'message': 'telegramUserId required'}), 400
    
    # Generate and store OTP
    otp = store_otp(telegram_user_id)
    
    # Send OTP via Telegram to the user (async handled by main bot)
    # The bot will send the OTP when user requests /bingo
    return jsonify({'success': True, 'message': 'OTP ready. User must send /bingo to bot.'})

@flask_app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    """Node.js server calls this to verify OTP"""
    data = request.json
    telegram_user_id = data.get('telegramUserId')
    otp = data.get('otp')
    
    if not telegram_user_id or not otp:
        return jsonify({'success': False, 'message': 'telegramUserId and otp required'}), 400
    
    is_valid, message = verify_otp(telegram_user_id, otp)
    
    return jsonify({
        'success': is_valid,
        'message': message,
        'telegramUserId': telegram_user_id
    })

def run_webserver():
    """Run Flask server for Node.js integration"""
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

# Start the web server in a separate thread
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
BOT_TOKEN = "8593313629:AAGLz9l6G4ZXHNIgenbOPhBhUcmDl_wTcKg"
ADMIN_CHAT_ID = "7160486597"

# Group and Channel Links
SUPPORT_GROUP_LINK = "https://t.me/presectionA"
SUPPORT_CHANNEL_LINK = "https://t.me/temarineh"

GAME_WEB_URL = "https://estif-bingo-247.onrender.com/player.html"

PAYMENT_ACCOUNTS = {
    "CBE": "1000179576997",
    "ABBISINIYA": "35241051",
    "TELEBIRR": "0987713787",
    "MPESA": "0722345146"
}

ACCOUNT_HOLDER = "Estifanos Yhannis"

logging.basicConfig(level=logging.INFO)

# ========== BILINGUAL TEXTS ==========
TEXTS = {
    'en': {
        'welcome': "🎉 *Welcome to Estif Bingo!* 🎉\n\n👇 Choose an option:",
        'register_prompt': "📝 *Share your contact to register:*",
        'register_success': "✅ *Registration Successful!*\n\n📱 Phone: {}\n🎮 Start Playing:\n{}",
        'already_registered': "✅ You are already registered!",
        'join_required': "🔔 *Join our channels first:*\n\n📢 Channel\n👥 Group",
        'deposit_select': "💰 *Select Payment Method*\n👤 Account Holder: `{}`",
        'deposit_selected': "✅ *Selected: {}*\n👤 Holder: `{}`\n📋 Number: `{}`\n\n💰 Enter amount:",
        'deposit_amount_accepted': "✅ Amount: {} Birr\n\n📸 Send screenshot:",
        'deposit_sent': "✅ Deposit request sent! Waiting for admin approval.",
        'cashout_not_allowed': "❌ *Cash Out Not Allowed*\n💰 Total Deposited: {} Birr\n⚠️ Minimum: 100 Birr",
        'insufficient_balance': "❌ *Insufficient Balance*\n💰 Your balance: 0 Birr",
        'cashout_select': "💳 *Select Withdrawal Method:*",
        'cashout_selected': "✅ *Selected: {}*\n💰 Balance: {} Birr\n\n💰 Enter amount (Min: 50, Max: 10000):",
        'cashout_amount_accepted': "✅ Amount: {} Birr\n\n📱 Enter account number:",
        'cashout_sent': "✅ Cashout request sent! Waiting for admin approval.",
        'contact': "📞 *Contact Center*\n\nJoin our channels for 24/7 support:",
        'invite': "🎉 *Invite Friends!*\n\n🔗 Share this link:\n`{}`",
        'balance': "💰 *Your Balance*\n🎮 Main: {} Birr\n📊 Total Deposited: {} Birr",
        'approved_deposit': "✅ *DEPOSIT APPROVED!*\n💰 Amount: {} Birr\n💵 New Balance: {} Birr",
        'approved_cashout': "✅ *CASH OUT APPROVED!*\n💰 Amount: {} Birr\n💵 New Balance: {} Birr",
        'rejected': "❌ *REJECTED*\n📝 Reason: {}",
        'use_menu': "Please use the menu buttons below:",
        'bingo_otp': "🔐 *Bingo Login Code*\n\nYour 6-digit code: `{}`\n\nThis code expires in {} minutes.\n\nEnter this code on the Bingo website to login.",
        'bingo_otp_button': "🔐 Bingo Code"
    },
    'am': {
        'welcome': "🎉 *እንኳን ወደ ኢስቲፍ ቢንጎ በደህና መጡ!* 🎉\n\n👇 ምርጫ ይምረጡ:",
        'register_prompt': "📝 *እባክዎ ለመመዝገብ አድራሻዎን ያጋሩ:*",
        'register_success': "✅ *ምዝገባ ተሳክቷል!*\n\n📱 ስልክ: {}\n🎮 ጨዋታ ለመጀመር:\n{}",
        'already_registered': "ቀድሞውንም ተመዝግበዋል!",
        'join_required': "🔔 *እባክዎ መቀላቀል ይጠበቅብዎታል:*\n\n📢 ቻናል\n👥 ቡድን",
        'deposit_select': "💰 *የክፍያ ዘዴ ይምረጡ*\n👤 ባለአካውንት: `{}`",
        'deposit_selected': "✅ *ተመርጧል: {}*\n👤 ባለአካውንት: `{}`\n📋 ቁጥር: `{}`\n\n💰 መጠን ያስገቡ:",
        'deposit_amount_accepted': "✅ መጠን: {} ብር\n\n📸 ማስረጃ ይላኩ:",
        'deposit_sent': "✅ ጥያቄ ተልኳል! ማጽደቅ በመጠባበቅ ላይ...",
        'cashout_not_allowed': "❌ *ገንዘብ ማውጣት አይቻልም*\n💰 አጠቃላይ ተቀማጭ: {} ብር\n⚠️ ዝቅተኛ: 100 ብር",
        'insufficient_balance': "❌ *በቂ ገንዘብ የለም*\n💰 ቀሪ ሂሳብ: 0 ብር",
        'cashout_select': "💳 *የመውጫ ዘዴ ይምረጡ:*",
        'cashout_selected': "✅ *ተመርጧል: {}*\n💰 ቀሪ ሂሳብ: {} ብር\n\n💰 መጠን ያስገቡ (ዝቅተኛ: 50, ከፍተኛ: 10000):",
        'cashout_amount_accepted': "✅ መጠን: {} ብር\n\n📱 የአካውንት ቁጥር ያስገቡ:",
        'cashout_sent': "✅ ጥያቄ ተልኳል! ማጽደቅ በመጠባበቅ ላይ...",
        'contact': "📞 *ደንበኛ አገልግሎት*\n\n24/7 ድጋፍ ለማግኘት ይቀላቀሉ:",
        'invite': "🎉 *ጓደኞችን ይጋብዙ!*\n\n🔗 ሊንኩን ያጋሩ:\n`{}`",
        'balance': "💰 *ቀሪ ሂሳብዎ*\n🎮 ዋና: {} ብር\n📊 አጠቃላይ ተቀማጭ: {} ብር",
        'approved_deposit': "✅ *ተቀማጭ ገንዘብ ጸድቋል!*\n💰 መጠን: {} ብር\n💵 አዲስ ቀሪ ሂሳብ: {} ብር",
        'approved_cashout': "✅ *ገንዘብ ማውጣት ጸድቋል!*\n💰 መጠን: {} ብር\n💵 አዲስ ቀሪ ሂሳብ: {} ብር",
        'rejected': "❌ *ውድቅ ተደርጓል*\n📝 ምክንያት: {}",
        'use_menu': "እባክዎ ከታች ያለውን ምናሌ ይጠቀሙ:",
        'bingo_otp': "🔐 *የቢንጎ መግቢያ ኮድ*\n\n6-አሃዝ ኮድዎ: `{}`\n\nይህ ኮድ በ{} ደቂቃ ውስጥ ያበቃል.\n\nእባክዎ ይህን ኮድ በቢንጎ ድህረ ገጽ ላይ ያስገቡ።",
        'bingo_otp_button': "🔐 የቢንጎ ኮድ"
    }
}

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

def update_user(uid, key, value):
    user = get_user(uid)
    if user:
        user[key] = value
        save_user(uid, user)

# ========== FLOW SYSTEM ==========
def reset_flow(context):
    context.user_data['flow'] = None
    context.user_data['step'] = None
    context.user_data['data'] = {}

# ========== GET LANGUAGE ==========
def get_lang(user_id):
    user = get_user(user_id)
    return user.get('lang', 'en') if user else 'en'

# ========== MENU ==========
def menu(lang='en'):
    if lang == 'am':
        return ReplyKeyboardMarkup([
            ["🎮 ጨዋታ", "📝 ተመዝገብ", "💰 ገንዘብ አስገባ"],
            ["💳 ገንዘብ አውጣ", "📞 ደንበኛ አገልግሎት", "🎉 ጋብዝ"],
            ["🔐 የቢንጎ ኮድ"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["🎮 Play", "📝 Register", "💰 Deposit"],
            ["💳 Cash Out", "📞 Contact Center", "🎉 Invite"],
            ["🔐 Bingo Code"]
        ], resize_keyboard=True)

# ========== CHECK JOINED GROUP ==========
async def check_joined_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    lang = get_lang(user_id)
    
    if user_data and user_data.get('joined_group'):
        return True
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL_LINK)],
        [InlineKeyboardButton("👥 Group", url=SUPPORT_GROUP_LINK)],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ])
    
    await update.message.reply_text(TEXTS[lang]['join_required'], reply_markup=keyboard, parse_mode='Markdown')
    return False

async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    update_user(user_id, 'joined_group', True)
    await query.edit_message_text("✅ Thanks for joining!")
    await query.message.reply_text("🎉 Welcome!", reply_markup=menu(get_lang(user_id)))

# ========== START WITH LANGUAGE SELECTION ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am")]
    ])
    await update.message.reply_text("🌐 Select your language / ቋንቋ ይምረጡ:", reply_markup=keyboard)

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user_id = str(query.from_user.id)
    
    user_data = get_user(user_id)
    if user_data:
        update_user(user_id, 'lang', lang)
    else:
        save_user(user_id, {'lang': lang, 'balance': 0, 'total_deposited': 0, 'joined_group': False, 'pending_withdrawals': []})
    
    await query.edit_message_text(TEXTS[lang]['welcome'], parse_mode='Markdown')
    await query.message.reply_text("👇 Choose an option:", reply_markup=menu(lang))

# ========== REGISTER ==========
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    
    if not await check_joined_group(update, context):
        return
    
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    lang = get_lang(user_id)
    
    if user_data and user_data.get('registered'):
        await update.message.reply_text(TEXTS[lang]['already_registered'], reply_markup=menu(lang))
        return
    
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("📱 Share Contact", request_contact=True)]], resize_keyboard=True)
    await update.message.reply_text(TEXTS[lang]['register_prompt'], reply_markup=keyboard, parse_mode='Markdown')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    user_id = str(user.id)
    lang = get_lang(user_id)
    
    user_data = {
        'user_id': user_id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': contact.phone_number,
        'balance': 0,
        'total_deposited': 0,
        'registered': True,
        'joined_group': True,
        'lang': lang,
        'pending_withdrawals': []
    }
    save_user(user_id, user_data)
    
    admin_text = f"🆕 NEW REGISTRATION\n\n👤 Name: {user.first_name}\n📱 Phone: {contact.phone_number}\n🆔 ID: {user_id}"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    
    await update.message.reply_text(TEXTS[lang]['register_success'].format(contact.phone_number, GAME_WEB_URL), reply_markup=menu(lang), parse_mode='Markdown')

# ========== PLAY ==========
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    if not await check_joined_group(update, context):
        return
    await update.message.reply_text(f"🎮 Play:\n{GAME_WEB_URL}")

# ========== DEPOSIT ==========
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    if not await check_joined_group(update, context):
        return
    
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    lang = get_lang(user_id)
    
    if not user_data or not user_data.get('registered'):
        await update.message.reply_text("❌ Please register first!", reply_markup=menu(lang))
        return
    
    keyboard = [[InlineKeyboardButton(k, callback_data=f"dep_{k}")] for k in PAYMENT_ACCOUNTS]
    await update.message.reply_text(TEXTS[lang]['deposit_select'].format(ACCOUNT_HOLDER), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def deposit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.split("_")[1]
    account_number = PAYMENT_ACCOUNTS[method]
    user_id = str(query.from_user.id)
    lang = get_lang(user_id)
    
    reset_flow(context)
    context.user_data['flow'] = 'deposit'
    context.user_data['step'] = 'waiting_amount'
    context.user_data['data'] = {
        'method': method,
        'account_number': account_number
    }
    
    await query.edit_message_text(
        TEXTS[lang]['deposit_selected'].format(method, ACCOUNT_HOLDER, account_number),
        parse_mode='Markdown'
    )

# ========== CASHOUT ==========
async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    if not await check_joined_group(update, context):
        return
    
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    lang = get_lang(user_id)
    
    if not user_data or not user_data.get('registered'):
        await update.message.reply_text("❌ Please register first!", reply_markup=menu(lang))
        return
    
    if user_data.get('total_deposited', 0) < 100:
        await update.message.reply_text(TEXTS[lang]['cashout_not_allowed'].format(user_data.get('total_deposited', 0)), parse_mode='Markdown', reply_markup=menu(lang))
        return
    
    if user_data.get('balance', 0) <= 0:
        await update.message.reply_text(TEXTS[lang]['insufficient_balance'], parse_mode='Markdown', reply_markup=menu(lang))
        return
    
    keyboard = [[InlineKeyboardButton(k, callback_data=f"cash_{k}")] for k in PAYMENT_ACCOUNTS]
    await update.message.reply_text(TEXTS[lang]['cashout_select'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def cashout_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.split("_")[1]
    user_id = str(query.from_user.id)
    lang = get_lang(user_id)
    user_data = get_user(user_id)
    balance = user_data.get('balance', 0) if user_data else 0
    
    reset_flow(context)
    context.user_data['flow'] = 'cashout'
    context.user_data['step'] = 'waiting_amount'
    context.user_data['data'] = {
        'method': method
    }
    
    await query.edit_message_text(
        TEXTS[lang]['cashout_selected'].format(method, balance),
        parse_mode='Markdown'
    )

# ========== CONTACT CENTER ==========
async def contact_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    lang = get_lang(str(update.effective_user.id))
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL_LINK)],
        [InlineKeyboardButton("👥 Group", url=SUPPORT_GROUP_LINK)]
    ])
    await update.message.reply_text(TEXTS[lang]['contact'], reply_markup=keyboard, parse_mode='Markdown')

# ========== INVITE ==========
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    lang = get_lang(str(update.effective_user.id))
    await update.message.reply_text(TEXTS[lang]['invite'].format(GAME_WEB_URL), parse_mode='Markdown')

# ========== BALANCE ==========
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_flow(context)
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    lang = get_lang(user_id)
    
    if user_data and user_data.get('registered'):
        await update.message.reply_text(TEXTS[lang]['balance'].format(user_data.get('balance', 0), user_data.get('total_deposited', 0)), parse_mode='Markdown', reply_markup=menu(lang))
    else:
        await update.message.reply_text("❌ Please register first!", reply_markup=menu(lang))

# ========== BINGO OTP ==========
async def bingo_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send Bingo login OTP to user"""
    reset_flow(context)
    user_id = update.effective_user.id
    lang = get_lang(str(user_id))
    
    # Generate and store OTP
    otp = store_otp(user_id)
    
    # Send OTP message
    await update.message.reply_text(
        TEXTS[lang]['bingo_otp'].format(otp, OTP_EXPIRY_MINUTES),
        parse_mode='Markdown',
        reply_markup=menu(lang)
    )

# ========== UNIVERSAL TEXT HANDLER ==========
async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data.get('flow')
    step = context.user_data.get('step')
    
    if not flow:
        lang = get_lang(str(update.effective_user.id))
        await update.message.reply_text(
            TEXTS[lang]['use_menu'],
            reply_markup=menu(lang)
        )
        return
    
    # ===== DEPOSIT FLOW =====
    if flow == 'deposit':
        if step == 'waiting_amount':
            text = update.message.text
            nums = re.findall(r"\d+\.?\d*", text)
            
            if not nums:
                await update.message.reply_text("❌ Enter valid amount (e.g., 100)")
                return
            
            amount = float(nums[0])
            context.user_data['data']['amount'] = amount
            context.user_data['step'] = 'waiting_screenshot'
            
            lang = get_lang(str(update.effective_user.id))
            await update.message.reply_text(
                TEXTS[lang]['deposit_amount_accepted'].format(amount),
                parse_mode='Markdown'
            )
            return
    
    # ===== CASHOUT FLOW =====
    if flow == 'cashout':
        user_id = str(update.effective_user.id)
        user_data = get_user(user_id)
        lang = get_lang(user_id)
        
        if step == 'waiting_amount':
            text = update.message.text
            nums = re.findall(r"\d+\.?\d*", text)
            
            if not nums:
                await update.message.reply_text("❌ Enter valid amount (e.g., 500)")
                return
            
            amount = float(nums[0])
            
            if amount < 50:
                await update.message.reply_text("❌ Minimum withdrawal is 50 Birr")
                return
            
            if amount > 10000:
                await update.message.reply_text("❌ Maximum withdrawal is 10,000 Birr")
                return
            
            if amount > user_data.get('balance', 0):
                await update.message.reply_text(f"❌ Insufficient balance! Your balance: {user_data.get('balance', 0)} Birr")
                return
            
            context.user_data['data']['amount'] = amount
            context.user_data['step'] = 'waiting_account'
            
            await update.message.reply_text(TEXTS[lang]['cashout_amount_accepted'].format(amount), parse_mode='Markdown')
            return
        
        elif step == 'waiting_account':
            account = update.message.text.strip()
            data = context.user_data['data']
            request_id = random.randint(10000, 99999)
            
            # Store pending withdrawal
            user_data['pending_withdrawals'] = user_data.get('pending_withdrawals', [])
            user_data['pending_withdrawals'].append({
                'id': request_id,
                'amount': data['amount'],
                'account': account,
                'method': data['method'],
                'status': 'pending',
                'requested_at': datetime.now().isoformat()
            })
            save_user(user_id, user_data)
            
            # SEND COPYABLE TEXT (NO INLINE BUTTONS)
            copy_text = f"""
💰 *CASHOUT REQUEST* #{request_id}

👤 User ID: `{user_id}`
💰 Amount: `{data['amount']}` Birr
💳 Method: `{data['method']}`
📱 Account: `{account}`

Click to copy (select and Ctrl+C):

`/approve_cashout {user_id} {data['amount']}`

or

`/reject_cashout {user_id}`
"""
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=copy_text, parse_mode='Markdown')
            
            await update.message.reply_text(TEXTS[lang]['cashout_sent'], reply_markup=menu(lang), parse_mode='Markdown')
            
            # RESET FLOW
            reset_flow(context)
            return

# ========== PHOTO HANDLER (DEPOSIT) ==========
async def handle_deposit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('flow') != 'deposit' or context.user_data.get('step') != 'waiting_screenshot':
        return
    
    user = update.effective_user
    user_id = str(user.id)
    lang = get_lang(user_id)
    data = context.user_data['data']
    
    photo = update.message.photo[-1]
    
    # Generate request ID
    request_id = random.randint(100000, 999999)
    
    # SEND COPYABLE TEXT (NO INLINE BUTTONS)
    copy_text = f"""
💰 *NEW DEPOSIT REQUEST* #{request_id}

👤 User: {user.first_name} (@{user.username or 'N/A'})
🆔 ID: `{user_id}`
💰 Amount: `{data['amount']}` Birr
🏦 Method: `{data['method']}`
📋 Account: `{data['account_number']}`

Click to copy (select and Ctrl+C):

`/approve_deposit {user_id} {data['amount']}`

or

`/reject_deposit {user_id}`
"""
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=copy_text, parse_mode='Markdown')
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo.file_id, caption=f"Deposit proof from {user.first_name}")
    
    await update.message.reply_text(TEXTS[lang]['deposit_sent'], reply_markup=menu(lang), parse_mode='Markdown')
    
    # RESET FLOW
    reset_flow(context)

# ========== ADMIN COMMANDS ==========
async def approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/approve_deposit USER_ID AMOUNT`\n\nExample: `/approve_deposit 1077270220 600`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user_data = get_user(str(user_id))
        if user_data:
            new_balance = user_data.get('balance', 0) + amount
            new_total = user_data.get('total_deposited', 0) + amount
            lang = user_data.get('lang', 'en')
            
            update_user(str(user_id), 'balance', new_balance)
            update_user(str(user_id), 'total_deposited', new_total)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]['approved_deposit'].format(amount, new_balance),
                parse_mode='Markdown',
                reply_markup=menu(lang)
            )
            await update.message.reply_text(f"✅ Deposit of {amount} Birr approved for user {user_id}")
        else:
            await update.message.reply_text(f"❌ User {user_id} not found")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/reject_deposit USER_ID`\n\nExample: `/reject_deposit 1077270220`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Not specified"
        
        user_data = get_user(str(user_id))
        if user_data:
            lang = user_data.get('lang', 'en')
            
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]['rejected'].format(reason),
                parse_mode='Markdown',
                reply_markup=menu(lang)
            )
            await update.message.reply_text(f"✅ Deposit rejected for user {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def approve_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/approve_cashout USER_ID AMOUNT`\n\nExample: `/approve_cashout 1077270220 500`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user_data = get_user(str(user_id))
        if user_data:
            withdrawals = user_data.get('pending_withdrawals', [])
            found = None
            for w in withdrawals:
                if w.get('status') == 'pending' and w.get('amount') == amount:
                    found = w
                    w['status'] = 'approved'
                    w['approved_at'] = datetime.now().isoformat()
                    break
            
            if not found:
                await update.message.reply_text(f"❌ No pending withdrawal of {amount} Birr found for user {user_id}")
                return
            
            new_balance = user_data.get('balance', 0) - amount
            lang = user_data.get('lang', 'en')
            
            update_user(str(user_id), 'balance', max(0, new_balance))
            update_user(str(user_id), 'pending_withdrawals', withdrawals)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]['approved_cashout'].format(amount, max(0, new_balance)),
                parse_mode='Markdown',
                reply_markup=menu(lang)
            )
            await update.message.reply_text(f"✅ Cashout of {amount} Birr approved for user {user_id}")
        else:
            await update.message.reply_text(f"❌ User {user_id} not found")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def reject_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/reject_cashout USER_ID`\n\nExample: `/reject_cashout 1077270220`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Not specified"
        
        user_data = get_user(str(user_id))
        if user_data:
            lang = user_data.get('lang', 'en')
            withdrawals = user_data.get('pending_withdrawals', [])
            
            for w in withdrawals:
                if w.get('status') == 'pending':
                    w['status'] = 'rejected'
                    w['reject_reason'] = reason
                    break
            
            update_user(str(user_id), 'pending_withdrawals', withdrawals)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]['rejected'].format(reason),
                parse_mode='Markdown',
                reply_markup=menu(lang)
            )
            await update.message.reply_text(f"✅ Cashout rejected for user {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ========== MAIN ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("bingo", bingo_otp))  # NEW: /bingo command
    app.add_handler(CommandHandler("approve_deposit", approve_deposit))
    app.add_handler(CommandHandler("reject_deposit", reject_deposit))
    app.add_handler(CommandHandler("approve_cashout", approve_cashout))
    app.add_handler(CommandHandler("reject_cashout", reject_cashout))
    
    # Button handlers
    app.add_handler(MessageHandler(filters.Regex("🎮 Play|🎮 ጨዋታ"), play))
    app.add_handler(MessageHandler(filters.Regex("📝 Register|📝 ተመዝገብ"), register))
    app.add_handler(MessageHandler(filters.Regex("💰 Deposit|💰 ገንዘብ አስገባ"), deposit))
    app.add_handler(MessageHandler(filters.Regex("💳 Cash Out|💳 ገንዘብ አውጣ"), cashout))
    app.add_handler(MessageHandler(filters.Regex("📞 Contact Center|📞 ደንበኛ አገልግሎት"), contact_center))
    app.add_handler(MessageHandler(filters.Regex("🎉 Invite|🎉 ጋብዝ"), invite))
    app.add_handler(MessageHandler(filters.Regex("🔐 Bingo Code|🔐 የቢንጎ ኮድ"), bingo_otp))  # NEW: Bingo button
    
    # Contact handler
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(language_callback, pattern="lang_"))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))
    app.add_handler(CallbackQueryHandler(deposit_cb, pattern="dep_"))
    app.add_handler(CallbackQueryHandler(cashout_cb, pattern="cash_"))
    
    # Text and photo handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_deposit_photo))
    
    print("=" * 50)
    print("🤖 Estif Bingo Bot is running...")
    print(f"👤 Account Holder: {ACCOUNT_HOLDER}")
    print(f"🎮 Game URL: {GAME_WEB_URL}")
    print("🌐 Bilingual: English + Amharic")
    print("🔐 Bingo OTP: Enabled (/bingo command + button)")
    print("📡 API Endpoint: /api/verify-otp")
    print("=" * 50)
    app.run_polling()

if __name__ == "__main__":
    main()