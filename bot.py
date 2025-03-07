# bot.py
import logging
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)
import config
import database
from handlers.attendance import (
    check_in_command,
    check_out_command,
    status_command,
    history_command,
    handle_history_callback,
    get_user_menu_keyboard
)
from handlers.admin import (
    users_command,
    attendance_command,
    report_command,
    dashboard_command,
    handle_admin_callback,
    get_admin_menu_keyboard,
    delete_user_command,
    delete_record_command,
    clear_attendance_command,
    user_details_command
)
from reminders import setup_reminders

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variable to keep a reference to the reminder scheduler
reminder_scheduler = None

def start_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /start command."""
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name
    username = user.username
    
    # Check if user is admin
    is_admin = user_id == config.ADMIN_USER_ID
    
    # Register user
    database.register_user(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        is_admin=is_admin
    )
    
    # Welcome message
    welcome_text = (
        f"👋 *Hello {first_name}!*\n\n"
        "Welcome to the Attendance Bot. This bot helps you track your work attendance.\n\n"
    )
    
    if is_admin:
        welcome_text += (
            "*🔍 Admin Features:*\n"
            "• View all registered users\n"
            "• Monitor today's attendance\n"
            "• Generate attendance reports\n"
            "• View attendance dashboard\n\n"
        )
    
    welcome_text += (
        "*🔍 Worker Features:*\n"
        "• Check in when you start work\n"
        "• Check out when you finish work\n"
        "• View your current status\n"
        "• Access your attendance history\n\n"
        "*How to get started:*\n"
        "Use the buttons below to navigate and track your attendance."
    )
    
    # Create appropriate keyboard
    keyboard = get_admin_menu_keyboard() if is_admin else get_user_menu_keyboard()
    
    update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /help command."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    help_text = f"📚 *{user_name}'s Help Guide*\n\n"
    
    # Worker commands
    help_text += (
        "*Worker Commands:*\n"
        "• `/checkin` - Check in for work\n"
        "• `/checkout` - Check out after work\n"
        "• `/status` - Check your current status\n"
        "• `/history` - View your attendance history\n"
        "• `/history YYYY-MM-DD` - View history for a specific date\n\n"
    )
    
    # Admin commands
    if is_admin:
        help_text += (
            "*Admin Commands:*\n"
            "• `/users` - List all registered users\n"
            "• `/attendance` - View today's attendance\n"
            "• `/report` - Generate attendance report\n"
            "• `/report YYYY-MM-DD YYYY-MM-DD` - Report for date range\n"
            "• `/dashboard` - View attendance dashboard\n"
            "• `/dashboard N` - Dashboard for last N days\n"
            "• `/deleteuser` - Delete a user\n"
            "• `/deleterecord` - Delete a record\n"
            "• `/clearattendance` - Clear attendance for a user\n"
            "• `/userdetails` - View user details\n\n"
        )
    
    help_text += (
        "*Tips:*\n"
        "• Use the buttons for quick access to commands\n"
        "• Check in when you start work and check out when you finish\n"
        "• View your history to track your work hours\n"
    )
    
    # Create appropriate keyboard
    keyboard = get_admin_menu_keyboard() if is_admin else get_user_menu_keyboard()
    
    update.message.reply_text(
        help_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Global handler for callback queries from inline keyboards."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    # Check if this is a photo message - can't edit text in photo messages
    if query.message and query.message.photo:
        # For photo messages, we need to send a new message instead of editing
        query.answer("Command received")
        
        if data == "cmd_main_menu" or data == "show_worker_menu":
            # Show main worker menu
            context.bot.send_message(
                chat_id=user_id,
                text=f"👋 *Hello {user_name}!*\n\nWhat would you like to do?",
                reply_markup=get_user_menu_keyboard(is_admin),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        elif data == "show_admin_menu" or data == "admin_menu":
            # Show admin menu
            context.bot.send_message(
                chat_id=user_id,
                text=f"👑 *Admin Panel*\n\nSelect an option:",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Regular message handling
    # Route to the appropriate handler based on the prefix
    try:
        if data.startswith("cmd_") or data.startswith(("cal", "hist")):
            handle_history_callback(update, context)
        elif data.startswith(("admin_", "report_", "dashboard_")):
            handle_admin_callback(update, context)
        elif data.startswith("show_"):
            interface_callback_handler(update, context)
        else:
            # Unknown callback data
            query.answer("Unknown command")
            logger.warning(f"Unknown callback data received: {data}")
    except Exception as e:
        # If there's an error, send a new message instead of trying to edit
        logger.error(f"Error handling callback: {e}")
        query.answer("Error processing command")
        
        # Send a new message with the appropriate menu
        if is_admin:
            keyboard = [
                [
                    InlineKeyboardButton("👷 Worker Menu", callback_data="show_worker_menu"),
                    InlineKeyboardButton("👑 Admin Menu", callback_data="show_admin_menu")
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            
            context.bot.send_message(
                chat_id=user_id,
                text=f"❌ *Error*\n\nThere was a problem processing your request. Please select an option:",
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.bot.send_message(
                chat_id=user_id,
                text=f"❌ *Error*\n\nThere was a problem processing your request. Here's the main menu:",
                reply_markup=get_user_menu_keyboard(False),
                parse_mode=ParseMode.MARKDOWN
            )

def show_menu_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /menu command to always show the main menu."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    
    # If user doesn't exist, register them
    if not user:
        database.register_user(
            user_id=user_id,
            first_name=user_name,
            last_name=update.effective_user.last_name,
            username=update.effective_user.username,
            is_admin=user_id == config.ADMIN_USER_ID
        )
        user = database.get_user(user_id)
    
    is_admin = user and user.get("is_admin", False)
    
    # Send appropriate menu
    if is_admin:
        # Show both admin and worker options
        keyboard = [
            [
                InlineKeyboardButton("👷 Worker Interface", callback_data="show_worker_menu"),
                InlineKeyboardButton("👑 Admin Interface", callback_data="show_admin_menu")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"👋 *Hello {user_name}!*\n\n"
            "As an admin, you can access both worker and admin features.\n"
            "Please select which interface you'd like to use:",
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Show worker menu
        update.message.reply_text(
            f"👋 *Hello {user_name}!*\n\n"
            "What would you like to do?",
            reply_markup=get_user_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def admin_menu_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /admin command to directly access admin menu."""
    user_id = update.effective_user.id
    user = database.get_user(user_id)
    
    # Check if user is admin
    is_admin = user and user.get("is_admin", False)
    
    if is_admin:
        update.message.reply_text(
            "👑 *Admin Panel*\n\n"
            "Please select an option:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text(
            "❌ Sorry, this command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )

def interface_callback_handler(update: Update, context: CallbackContext) -> None:
    """Handle interface selection callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    query.answer()
    
    if query.data == "show_worker_menu":
        query.edit_message_text(
            f"👋 *Hello {user_name}!*\n\n"
            "What would you like to do?",
            reply_markup=get_user_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == "show_admin_menu":
        query.edit_message_text(
            "👑 *Admin Panel*\n\n"
            "Please select an option:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify user
    if update and update.effective_message:
        update.effective_message.reply_text(
            "❌ Sorry, an error occurred. Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

def text_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle text messages by showing the menu."""
    # If user sends any text that isn't a command, show the menu
    user_id = update.effective_user.id
    user = database.get_user(user_id)
    
    # If user doesn't exist yet, register them
    if not user:
        show_menu_command(update, context)
        return
    
    # Check if user is admin
    is_admin = user.get("is_admin", False)
    
    if is_admin:
        # Show admin/worker selector
        keyboard = [
            [
                InlineKeyboardButton("👷 Worker Menu", callback_data="show_worker_menu"),
                InlineKeyboardButton("👑 Admin Menu", callback_data="show_admin_menu")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Please select which menu you'd like to access:",
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Show worker menu
        update.message.reply_text(
            "Here's what you can do:",
            reply_markup=get_user_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def main() -> None:
    """Start the bot."""
    global reminder_scheduler
    
    # Create the Updater and pass it your bot's token
    updater = Updater(config.TELEGRAM_BOT_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("menu", show_menu_command))  # New menu command
    dispatcher.add_handler(CommandHandler("admin", admin_menu_command))  # Direct admin access
    
    # Worker command handlers
    dispatcher.add_handler(CommandHandler("checkin", check_in_command))
    dispatcher.add_handler(CommandHandler("checkout", check_out_command))
    dispatcher.add_handler(CommandHandler("status", status_command))
    dispatcher.add_handler(CommandHandler("history", history_command))
    
    # Admin command handlers
    dispatcher.add_handler(CommandHandler("users", users_command))
    dispatcher.add_handler(CommandHandler("attendance", attendance_command))
    dispatcher.add_handler(CommandHandler("report", report_command))
    dispatcher.add_handler(CommandHandler("dashboard", dashboard_command))
    dispatcher.add_handler(CommandHandler("deleteuser", delete_user_command))
    dispatcher.add_handler(CommandHandler("deleterecord", delete_record_command))
    dispatcher.add_handler(CommandHandler("clearattendance", clear_attendance_command))
    dispatcher.add_handler(CommandHandler("userdetails", user_details_command))
    
    # Register callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(interface_callback_handler, pattern="^show_"))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add handler for text messages (non-commands)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))
    
    # Register error handler
    dispatcher.add_error_handler(error_handler)
    
    # Start the reminder scheduler
    reminder_scheduler = setup_reminders(updater.bot)
    
    # Start the Bot
    updater.start_polling()
    logger.info("Bot started")
    
    # Run the bot until you press Ctrl-C
    try:
        updater.idle()
    finally:
        # Stop the reminder scheduler when the bot stops
        if reminder_scheduler:
            reminder_scheduler.stop()

if __name__ == "__main__":
    main() 