import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json
import os
from datetime import datetime

# ========== CONFIGURATION ==========
BOT_TOKEN = "8593313629:AAERZCJwvtg16XglkxBCDVzFZxuB1Cd4iiY"
ADMIN_CHAT_ID = "7160486597"

# Your group and channel links (REPLACE THESE!)
SUPPORT_GROUP_LINK = "https://t.me/presectionA"
SUPPORT_CHANNEL_LINK = "https://t.me/temarineh"

# Game link (REPLACE THIS!)
GAME_WEB_URL = "https://estif-bingo-247.onrender.com/player.html"

# Account Holder Name
ACCOUNT_HOLDER = "Estifanos Yhannis"

# Payment accounts
PAYMENT_ACCOUNTS = {
    "CBE": "1000179576997",
    "ABBISINIYA": "35241051",
    "TELEBIRR": "0987713787",
    "MPESA": "0722345146"
}

# ========== SETUP ==========
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ========== DATABASE ==========
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def get_user(user_id):
    db = load_db()
    return db.get(str(user_id))

def save_user(user_id, data):
    db = load_db()
    db[str(user_id)] = data
    save_db(db)

def update_user(user_id, key, value):
    user = get_user(user_id)
    if user:
        user[key] = value
        save_user(user_id, user)

# ========== MAIN MENU (3x3 GRID - 2 ROWS, 3 COLUMNS) ==========
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎮 Play"), KeyboardButton("📝 Register"), KeyboardButton("💰 Deposit")],
        [KeyboardButton("💳 Cash Out"), KeyboardButton("📞 Contact Center"), KeyboardButton("🎉 Invite")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== CHECK IF USER JOINED GROUP ==========
async def check_joined_group(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_action):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    if user_data and user_data.get('joined_group'):
        return True
    else:
        context.user_data['pending_action'] = callback_action
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=SUPPORT_CHANNEL_LINK)],
            [InlineKeyboardButton("👥 Join Group", url=SUPPORT_GROUP_LINK)],
            [InlineKeyboardButton("✅ I've Joined", callback_data="joined")]
        ])
        await update.message.reply_text(
            "🔔 **IMPORTANT!** 🔔\n\n"
            "To use Estif Bingo, you MUST join our:\n\n"
            "📢 **Official Channel** - Latest news & winners\n"
            "👥 **Support Group** - 24/7 help\n\n"
            "👇 Click below, then press **'I've Joined'**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return False

# ========== JOIN CALLBACK ==========
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    update_user(user_id, 'joined_group', True)
    
    pending = context.user_data.get('pending_action')
    
    if pending == 'play':
        await query.edit_message_text("✅ Thanks for joining!\n\n🎮 Opening game...")
        await query.message.reply_text(f"🎮 **Click to Play:**\n{GAME_WEB_URL}\n\nGood luck! 🍀", parse_mode='Markdown')
        await query.message.reply_text("🏠 Main Menu:", reply_markup=get_main_keyboard())
        
    elif pending == 'register':
        contact_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Contact", request_contact=True)]],
            resize_keyboard=True
        )
        await query.edit_message_text("✅ Thanks for joining!\n\n📝 **Please share your contact to register:**")
        await query.message.reply_text("Tap the button below:", reply_markup=contact_keyboard)
        
    elif pending == 'deposit':
        await query.edit_message_text("✅ Thanks for joining!\n\n💰 Redirecting to deposit...")
        await show_deposit_options(query.message, context)
        
    elif pending == 'cashout':
        await query.edit_message_text("✅ Thanks for joining!\n\n💳 Redirecting to cash out...")
        await show_cashout_options(query.message, context)
    
    elif pending == 'contact':
        await query.edit_message_text("✅ Thanks for joining!\n\n📞 Redirecting to support...")
        await show_contact_options(query.message, context)
    
    elif pending == 'invite':
        await query.edit_message_text("✅ Thanks for joining!\n\n🎉 Redirecting to invite...")
        await handle_invite_button(query.message, context)
    
    context.user_data['pending_action'] = None

# ========== 1. PLAY BUTTON ==========
async def play_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_joined_group(update, context, 'play'):
        await update.message.reply_text(f"🎮 **Play Now:**\n{GAME_WEB_URL}\n\nGood luck! 🍀", parse_mode='Markdown')

# ========== 2. REGISTER BUTTON ==========
async def register_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    if user_data and user_data.get('registered'):
        await update.message.reply_text("✅ You are already registered! Use the menu to play.", reply_markup=get_main_keyboard())
        return
    
    if await check_joined_group(update, context, 'register'):
        contact_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Contact", request_contact=True)]],
            resize_keyboard=True
        )
        await update.message.reply_text("📝 **Please share your contact to register:**", reply_markup=contact_keyboard, parse_mode='Markdown')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    phone_number = contact.phone_number
    user_id = str(user.id)
    
    user_data = {
        'user_id': user_id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': phone_number,
        'balance': 0,
        'registered': True,
        'joined_group': True,
        'registered_at': datetime.now().isoformat()
    }
    save_user(user_id, user_data)
    
    admin_text = f"""🆕 **NEW REGISTRATION**

👤 Name: {user.first_name} {user.last_name or ''}
🆔 Username: @{user.username or 'N/A'}
📱 Phone: {phone_number}
🆔 ID: {user_id}
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode='Markdown')
    
    await update.message.reply_text(
        f"✅ **Registration Successful!** 🎉\n\n"
        f"📱 Phone: {phone_number}\n\n"
        f"🎮 **Start Playing:**\n{GAME_WEB_URL}\n\n"
        f"Welcome to Estif Bingo! 🎊",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

# ========== 3. DEPOSIT BUTTON ==========
async def deposit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_joined_group(update, context, 'deposit'):
        await show_deposit_options(update.message, context)

async def show_deposit_options(message, context):
    keyboard = []
    for name, number in PAYMENT_ACCOUNTS.items():
        keyboard.append([InlineKeyboardButton(f"{name} - {number}", callback_data=f"deposit_{name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        f"💰 **Select Payment Method**\n\n"
        f"👤 **Account Holder:** `{ACCOUNT_HOLDER}`\n\n"
        f"Click on an account to copy the number:\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    account_type = query.data.replace("deposit_", "")
    account_number = PAYMENT_ACCOUNTS[account_type]
    
    await query.edit_message_text(
        f"✅ **Selected: {account_type}**\n\n"
        f"👤 **Account Holder:** `{ACCOUNT_HOLDER}`\n"
        f"📋 **Account Number:**\n`{account_number}`\n\n"
        f"💡 **Instructions:**\n"
        f"1️⃣ Send payment to this number\n"
        f"2️⃣ Make sure the name shows **{ACCOUNT_HOLDER}**\n"
        f"3️⃣ Type the **amount** you sent\n"
        f"4️⃣ Then **send the screenshot**\n\n"
        f"💰 Please reply with the amount:",
        parse_mode='Markdown'
    )
    
    context.user_data['pending_deposit'] = {
        'account': account_type,
        'number': account_number,
        'step': 'waiting_amount'
    }

async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_deposit' not in context.user_data:
        return
    
    try:
        amount = float(update.message.text)
        context.user_data['pending_deposit']['amount'] = amount
        context.user_data['pending_deposit']['step'] = 'waiting_screenshot'
        
        await update.message.reply_text(
            f"✅ Amount: {amount} Birr\n\n"
            f"📸 **Please send the payment screenshot now:**"
        )
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number (e.g., 100)")

async def handle_deposit_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_deposit' not in context.user_data:
        return
    
    user = update.effective_user
    deposit_data = context.user_data['pending_deposit']
    
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        await update.message.reply_text("❌ Please send a photo/screenshot")
        return
    
    admin_text = f"""💰 **DEPOSIT REQUEST**

👤 User: {user.first_name} (@{user.username or 'N/A'})
🆔 ID: {user.id}
🏦 Account: {deposit_data['account']}
👤 Account Holder: {ACCOUNT_HOLDER}
💰 Amount: {deposit_data['amount']} Birr
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏳ Status: Pending Approval"""
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode='Markdown')
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo.file_id, caption=f"Deposit proof from @{user.username or user.id}")
    
    await update.message.reply_text(
        f"✅ **Deposit Request Sent!**\n\n"
        f"💰 Amount: {deposit_data['amount']} Birr\n"
        f"🏦 Method: {deposit_data['account']}\n"
        f"👤 Account Holder: {ACCOUNT_HOLDER}\n\n"
        f"⏳ **Waiting for admin approval...**\n"
        f"You'll be notified once confirmed.\n\n"
        f"Thank you for your patience! 🙏",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    
    context.user_data['pending_deposit'] = None

# ========== 4. CASH OUT BUTTON ==========
async def cashout_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_joined_group(update, context, 'cashout'):
        await show_cashout_options(update.message, context)

async def show_cashout_options(message, context):
    keyboard = [
        [InlineKeyboardButton("CBE", callback_data="cashout_CBE")],
        [InlineKeyboardButton("ABBISINIYA", callback_data="cashout_ABBISINIYA")],
        [InlineKeyboardButton("TELEBIRR", callback_data="cashout_TELEBIRR")],
        [InlineKeyboardButton("MPESA", callback_data="cashout_MPESA")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "💳 **Select Withdrawal Method:**\n\n"
        "Choose your preferred payment method:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def cashout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("cashout_", "")
    context.user_data['cashout_method'] = method
    
    await query.edit_message_text(
        f"✅ **Selected: {method}**\n\n"
        f"📝 **Please enter your account number or phone number:**\n\n"
        f"Example: `0912345678` or `1000179576997`\n\n"
        f"💳 Send your {method} account number:",
        parse_mode='Markdown'
    )
    context.user_data['pending_cashout'] = True

async def handle_cashout_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('pending_cashout'):
        return
    
    user = update.effective_user
    account_number = update.message.text
    method = context.user_data.get('cashout_method', 'Unknown')
    
    admin_text = f"""💳 **CASH OUT REQUEST**

👤 User: {user.first_name} (@{user.username or 'N/A'})
🆔 ID: {user.id}
🏦 Method: {method}
📱 Account: {account_number}
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏳ Status: Pending Approval"""
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode='Markdown')
    
    await update.message.reply_text(
        f"✅ **Cash Out Request Sent!**\n\n"
        f"💳 Method: {method}\n"
        f"📱 Account: {account_number}\n\n"
        f"⏳ **Waiting for admin approval...**\n"
        f"You'll be notified once processed.\n\n"
        f"Thank you for your patience! 🙏",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    
    context.user_data['pending_cashout'] = False
    context.user_data['cashout_method'] = None

# ========== 5. CONTACT CENTER BUTTON ==========
async def contact_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    if user_data and user_data.get('joined_group'):
        await show_contact_options(update.message, context)
    else:
        await check_joined_group(update, context, 'contact')

async def show_contact_options(message, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=SUPPORT_CHANNEL_LINK)],
        [InlineKeyboardButton("👥 Join Group", url=SUPPORT_GROUP_LINK)]
    ])
    
    await message.reply_text(
        "📞 **Contact Center**\n\n"
        "Get 24/7 support:\n\n"
        "✅ Latest announcements\n"
        "✅ Live chat with admins\n"
        "✅ Instant help\n\n"
        "👇 **Click to join:**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

# ========== 6. INVITE BUTTON ==========
async def invite_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    if user_data and user_data.get('joined_group'):
        await handle_invite_button(update.message, context)
    else:
        await check_joined_group(update, context, 'invite')

async def handle_invite_button(message, context):
    invite_link = GAME_WEB_URL
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link", switch_inline_query=f"Play Estif Bingo: {invite_link}")],
        [InlineKeyboardButton("📋 Copy Link", callback_data="copy_link")]
    ])
    
    await message.reply_text(
        f"🎉 **Invite Friends & Earn!** 🎉\n\n"
        f"🔗 **Your Invite Link:**\n"
        f"`{invite_link}`\n\n"
        f"💡 **How it works:**\n"
        f"1️⃣ Share this link with friends\n"
        f"2️⃣ They register and play\n"
        f"3️⃣ You earn bonuses!\n\n"
        f"👇 **Share or copy the link:**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def copy_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"✅ **Link copied!**\n\n"
        f"🔗 `{GAME_WEB_URL}`\n\n"
        f"📤 Share this link with your friends!\n\n"
        f"Each friend who joins = Bonus for you! 🎁",
        parse_mode='Markdown'
    )

# ========== CHECK BALANCE ==========
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    if user_data:
        await update.message.reply_text(
            f"💰 **Your Balance**\n\n"
            f"🎮 Main Balance: {user_data.get('balance', 0)} Birr\n"
            f"📊 Status: {'Active' if user_data.get('registered') else 'Not Registered'}",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ You are not registered yet!\n\n"
            "Click **Register** to get started.",
            reply_markup=get_main_keyboard()
        )

# ========== START COMMAND ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""🎉 **Welcome to Estif Bingo, {user.first_name}!** 🎉

🎮 **Your #1 Bingo Gaming Platform!**

✅ Play & Win Real Money
✅ Instant Withdrawals
✅ 24/7 Support

👇 **Choose an option below:**"""
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# ========== ADMIN COMMANDS ==========
async def approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user_data = get_user(str(user_id))
        if user_data:
            new_balance = user_data.get('balance', 0) + amount
            update_user(str(user_id), 'balance', new_balance)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **Deposit Approved!** 🎉\n\n"
                f"💰 Amount: {amount} Birr added\n"
                f"💵 New Balance: {new_balance} Birr\n\n"
                f"Thank you for playing Estif Bingo! 🎮",
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Deposit of {amount} Birr approved for user {user_id}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /approve_deposit USER_ID AMOUNT")

async def approve_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        user_data = get_user(str(user_id))
        if user_data:
            new_balance = user_data.get('balance', 0) - amount
            update_user(str(user_id), 'balance', max(0, new_balance))
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **Cash Out Approved!** 💳\n\n"
                f"💰 Amount: {amount} Birr sent\n"
                f"💵 Remaining Balance: {max(0, new_balance)} Birr\n\n"
                f"Thank you for playing Estif Bingo! 🎮",
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Cash out of {amount} Birr approved for user {user_id}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /approve_cashout USER_ID AMOUNT")

# ========== MAIN FUNCTION ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve_deposit", approve_deposit))
    app.add_handler(CommandHandler("approve_cashout", approve_cashout))
    app.add_handler(CommandHandler("balance", check_balance))
    
    app.add_handler(MessageHandler(filters.Regex("🎮 Play"), play_button))
    app.add_handler(MessageHandler(filters.Regex("📝 Register"), register_button))
    app.add_handler(MessageHandler(filters.Regex("💰 Deposit"), deposit_button))
    app.add_handler(MessageHandler(filters.Regex("💳 Cash Out"), cashout_button))
    app.add_handler(MessageHandler(filters.Regex("📞 Contact Center"), contact_button))
    app.add_handler(MessageHandler(filters.Regex("🎉 Invite"), invite_button))
    
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))
    app.add_handler(CallbackQueryHandler(deposit_callback, pattern="deposit_"))
    app.add_handler(CallbackQueryHandler(cashout_callback, pattern="cashout_"))
    app.add_handler(CallbackQueryHandler(copy_link_callback, pattern="copy_link"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🎮 Play|📝 Register|💰 Deposit|💳 Cash Out|📞 Contact Center|🎉 Invite)"), handle_deposit_amount))
    app.add_handler(MessageHandler(filters.PHOTO, handle_deposit_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(🎮 Play|📝 Register|💰 Deposit|💳 Cash Out|📞 Contact Center|🎉 Invite)"), handle_cashout_account))
    
    print("🤖 Estif Bingo Bot is running...")
    print(f"👤 Account Holder Name: {ACCOUNT_HOLDER}")
    print(f"🎮 Game URL: {GAME_WEB_URL}")
    print(f"📢 Group: {SUPPORT_GROUP_LINK}")
    print(f"📢 Channel: {SUPPORT_CHANNEL_LINK}")
    app.run_polling()

if __name__ == "__main__":
    main()