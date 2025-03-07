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
    ConversationHandler,
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
    user_details_command,
    delete_attendance_command
)
from reminders import setup_reminders
import datetime

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
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    common_commands = (
        "🤖 *Available Commands*\n\n"
        "*Worker Commands:*\n"
        "• `/start` - Start the bot and register\n"
        "• `/menu` - Show main menu\n"
        "• `/keyboard` - Show keyboard options\n"
        "• `/checkin` - Check in for work\n"
        "• `/checkout` - Check out after work\n"
        "• `/status` - Check your current status\n"
        "• `/history` - View your attendance history\n"
        "• `/help` - Show this help message\n\n"
    )
    
    admin_commands = ""
    if is_admin:
        admin_commands = (
            "*Admin Commands:*\n"
            "• `/admin` - Show admin menu\n"
            "• `/users` - List all registered users\n"
            "• `/attendance` - View today's attendance\n"
            "• `/report` - Generate attendance report\n"
            "• `/dashboard` - View attendance dashboard\n"
            "• `/deleteuser` - Delete a user\n"
            "• `/deleterecord` - Delete a record\n"
            "• `/clearattendance` - Clear attendance for a user\n"
            "• `/userdetails` - View user details\n"
            "• `/deleteattendance` - Delete specific attendance record\n\n"
        )
    
    update.message.reply_text(
        common_commands + admin_commands,
        reply_markup=get_user_menu_keyboard(is_admin),
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
        # For photo messages, send a new message instead of editing
        query.answer("Command received")
        
        # Handle different callback types 
        if data == "cmd_main_menu" or data == "show_worker_menu":
            # Show main worker menu
            context.bot.send_message(
                chat_id=user_id,
                text=f"👋 *Hello {user_name}!*\n\nWhat would you like to do?",
                reply_markup=get_user_menu_keyboard(is_admin),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "show_admin_menu" or data == "admin_menu":
            # Show admin menu
            context.bot.send_message(
                chat_id=user_id,
                text=f"👑 *Admin Panel*\n\nSelect an option:",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "admin_users":
            context.bot.send_message(
                chat_id=user_id,
                text="Loading users...",
                parse_mode=ParseMode.MARKDOWN
            )
            users_command(update, context)
        elif data == "admin_attendance":
            context.bot.send_message(
                chat_id=user_id,
                text="Loading today's attendance...",
                parse_mode=ParseMode.MARKDOWN
            )
            attendance_command(update, context)
        elif data == "admin_report":
            context.bot.send_message(
                chat_id=user_id,
                text="Loading reports...",
                parse_mode=ParseMode.MARKDOWN
            )
            report_command(update, context)
        elif data == "admin_dashboard": 
            context.bot.send_message(
                chat_id=user_id,
                text="Loading dashboard...",
                parse_mode=ParseMode.MARKDOWN
            )
            dashboard_command(update, context)
        elif data == "admin_user_management":
            context.bot.send_message(
                chat_id=user_id,
                text="🔧 *User Management*\n\nSelect an action to manage users:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 List All Users", callback_data="admin_users")],
                    [
                        InlineKeyboardButton("🗑️ Delete User", callback_data="prompt_delete_user"),
                        InlineKeyboardButton("🧹 Clear Attendance", callback_data="prompt_clear_attendance")
                    ],
                    [InlineKeyboardButton("👤 User Details", callback_data="prompt_user_details")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "prompt_delete_user":
            context.bot.send_message(
                chat_id=user_id,
                text="🗑️ *Delete User*\n\n"
                     "Please use the command:\n"
                     "`/deleteuser USER_ID`\n\n"
                     "Replace USER_ID with the ID of the user you want to delete.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]]),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "prompt_clear_attendance":
            context.bot.send_message(
                chat_id=user_id,
                text="🧹 *Clear Attendance*\n\n"
                     "Please use the command:\n"
                     "`/clearattendance USER_ID`\n\n"
                     "Replace USER_ID with the ID of the user whose attendance you want to clear.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]]),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "prompt_user_details":
            context.bot.send_message(
                chat_id=user_id,
                text="👤 *User Details*\n\n"
                     "Please use the command:\n"
                     "`/userdetails USER_ID`\n\n"
                     "Replace USER_ID with the ID of the user you want to view.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]]),
                parse_mode=ParseMode.MARKDOWN
            )
        # For other callbacks, do a simplified version 
        else:
            context.bot.send_message(
                chat_id=user_id,
                text="Please select from the menu:",
                reply_markup=get_user_menu_keyboard(is_admin)
            )
        return
    
    # Regular message handling
    try:
        if data.startswith("cmd_") or data.startswith(("cal", "hist")):
            handle_history_callback(update, context)
        elif data.startswith(("admin_", "report_", "dashboard_", "delete_user_", "clear_attendance_", "userdetails_", "prompt_", "confirm_")):
            handle_admin_callback(update, context)
        elif data.startswith("show_"):
            interface_callback_handler(update, context)
        else:
            # Unknown callback data
            query.answer("Unknown command")
            logger.warning(f"Unknown callback data received: {data}")
    except Exception as e:
        # If there's an error, send a new message instead of trying to edit
        logger.error(f"Update {update} caused error {e}")
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

def keyboard_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /keyboard command to always show the keyboard buttons."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    
    # If user doesn't exist yet, register them
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
    
    if is_admin:
        update.message.reply_text(
            f"👋 *Hello {user_name}!*\n\n"
            "Here are your keyboard options:",
            reply_markup=get_user_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Also send admin keyboard
        update.message.reply_text(
            "👑 *Admin Panel*\n\n"
            "Here are your admin options:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text(
            f"👋 *Hello {user_name}!*\n\n"
            "Here are your keyboard options:",
            reply_markup=get_user_menu_keyboard(False),
            parse_mode=ParseMode.MARKDOWN
        )

# ============================================================================
# ADMIN CONVERSATION HANDLER FUNCTIONS
# ============================================================================


def cancel_admin_conversation(update: Update, context: CallbackContext) -> int:
    """
    Cancel an ongoing admin conversation and return to the admin menu.
    Triggered when a user types /cancel during any conversation flow.
    """
    update.message.reply_text(
        "Operation cancelled. Returning to admin menu.",
        reply_markup=get_admin_menu_keyboard()
    )
    return ConversationHandler.END

# ----------------------------------------
# Delete User Conversation Functions
# ----------------------------------------

def start_delete_user(update: Update, context: CallbackContext) -> int:
    """
    Start the delete user conversation flow.
    Shows a list of all users to help the admin choose a user ID.
    """
    query = update.callback_query
    query.answer()
    
    # Show all users to help admin choose
    users = database.get_all_users()
    user_list = "👥 Available Users:\n\n"
    
    # Format each user's details
    for user in users:
        name = user.get('first_name', '')
        if user.get('last_name'):
            name += f" {user.get('last_name')}"
        username = f"@{user.get('username')}" if user.get('username') else "No username"
        user_list += f"ID: {user.get('user_id')} - {name} ({username})\n"
    
    # Prompt for user input
    query.edit_message_text(
        f"🗑️ Delete User\n\n{user_list}\n\nPlease enter the ID of the user you want to delete:\n\n(Type /cancel to abort)"
    )
    
    # Transition to the state where we wait for a user ID
    return "WAITING_USER_ID"

def process_delete_user_id(update: Update, context: CallbackContext) -> int:
    """
    Process the user ID for deletion.
    Validates the input, shows confirmation dialog with user details.
    """
    user_id_text = update.message.text.strip()
    
    # Validate that the input is a number
    try:
        user_id = int(user_id_text)
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    
    # Send confirmation button
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_user_{user_id}")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
    ]
    
    update.message.reply_text(
        f"⚠️ Delete User Confirmation\n\n"
        f"Are you sure you want to delete the user {name} (ID: {user_id})?\n\n"
        f"This will permanently delete the user and all their attendance records.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # End the conversation, further actions will be through callbacks
    return ConversationHandler.END

# ----------------------------------------
# Clear Attendance Conversation Functions
# ----------------------------------------

def start_clear_attendance(update: Update, context: CallbackContext) -> int:
    """
    Start the clear attendance conversation flow.
    Shows a list of all users to help the admin choose a user ID.
    """
    query = update.callback_query
    query.answer()
    
    # Show all users to help admin choose
    users = database.get_all_users()
    user_list = "👥 Available Users:\n\n"
    
    for user in users:
        name = user.get('first_name', '')
        if user.get('last_name'):
            name += f" {user.get('last_name')}"
        username = f"@{user.get('username')}" if user.get('username') else "No username"
        user_list += f"ID: {user.get('user_id')} - {name} ({username})\n"
    
    query.edit_message_text(
        f"🧹 Clear Attendance\n\n{user_list}\n\nPlease enter the ID of the user whose attendance records you want to clear:\n\n(Type /cancel to abort)"
    )
    
    return "WAITING_USER_ID"

def process_clear_attendance_id(update: Update, context: CallbackContext) -> int:
    """
    Process the user ID for clearing attendance.
    Validates the input, shows recent attendance records, and asks for confirmation.
    """
    user_id_text = update.message.text.strip()
    
    # Validate that the input is a number
    try:
        user_id = int(user_id_text)
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    
    # Show recent attendance records
    history = database.get_user_history(user_id, limit=5)
    history_text = ""
    
    if history:
        history_text = "\n\nRecent attendance records:\n"
        for record in history:
            try:
                date_str = record.get("date").strftime("%Y-%m-%d")
                check_in = record.get("check_in", "N/A")
                check_out = record.get("check_out", "N/A")
                
                check_in_str = "N/A"
                if check_in != "N/A" and check_in is not None:
                    check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                
                check_out_str = "N/A"
                if check_out != "N/A" and check_out is not None:
                    check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                
                history_text += f"{date_str}: {check_in_str} → {check_out_str}\n"
            except Exception:
                continue
    
    # Send confirmation button
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Clear All", callback_data=f"confirm_clear_attendance_{user_id}")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
    ]
    
    update.message.reply_text(
        f"⚠️ Clear Attendance Confirmation\n\n"
        f"Are you sure you want to clear all attendance records for {name} (ID: {user_id})?\n\n"
        f"This will permanently delete all attendance history for this user.{history_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ----------------------------------------
# User Details Conversation Functions
# ----------------------------------------

def start_user_details(update: Update, context: CallbackContext) -> int:
    """
    Start the user details conversation flow.
    Shows a list of all users to help the admin choose a user ID.
    """
    query = update.callback_query
    query.answer()
    
    # Show all users to help admin choose
    users = database.get_all_users()
    user_list = "👥 Available Users:\n\n"
    
    for user in users:
        name = user.get('first_name', '')
        if user.get('last_name'):
            name += f" {user.get('last_name')}"
        username = f"@{user.get('username')}" if user.get('username') else "No username"
        user_list += f"ID: {user.get('user_id')} - {name} ({username})\n"
    
    query.edit_message_text(
        f"👤 User Details\n\n{user_list}\n\nPlease enter the ID of the user whose details you want to view:\n\n(Type /cancel to abort)"
    )
    
    return "WAITING_USER_ID"

def process_user_details_id(update: Update, context: CallbackContext) -> int:
    """
    Process the user ID for viewing details.
    Validates the input and displays comprehensive user information and history.
    """
    user_id_text = update.message.text.strip()
    
    # Validate that the input is a number
    try:
        user_id = int(user_id_text)
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Get user details
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    name = first_name
    if last_name:
        name += f" {last_name}"
    
    username = f"@{user.get('username')}" if user.get('username') else "No username"
    admin_status = "Admin" if user.get("is_admin", False) else "Worker"
    
    # Get registration date
    created_at = "Unknown"
    if user.get('created_at'):
        try:
            created_at = user.get('created_at').strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            created_at = str(user.get('created_at'))
    
    # Get user history
    history = database.get_user_history(user_id, limit=10)
    history_text = ""
    
    if history:
        history_text = "\n\nRecent Attendance:\n"
        for record in history:
            try:
                date_str = record.get("date").strftime("%Y-%m-%d")
                check_in = record.get("check_in", "N/A")
                check_out = record.get("check_out", "N/A")
                duration = record.get("duration", "N/A")
                
                check_in_str = "N/A"
                if check_in != "N/A" and check_in is not None:
                    check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                
                check_out_str = "N/A"
                if check_out != "N/A" and check_out is not None:
                    check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                
                history_text += f"• {date_str}: {check_in_str} → {check_out_str} ({duration} hours)\n"
            except Exception:
                continue
    else:
        history_text = "\n\nNo attendance records found."
    
    # Build message
    message = f"👤 User Details\n\n"
    message += f"ID: {user_id}\n"
    message += f"Name: {name}\n"
    message += f"Username: {username}\n"
    message += f"Role: {admin_status}\n"
    message += f"Registered: {created_at}\n"
    message += history_text
    
    # Add admin action buttons
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Delete User", callback_data=f"delete_user_{user_id}"),
            InlineKeyboardButton("🧹 Clear Attendance", callback_data=f"clear_attendance_{user_id}")
        ],
        [InlineKeyboardButton("📅 Delete Specific Date", callback_data=f"delete_specific_date_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]
    ]
    
    update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ----------------------------------------
# Delete Specific Attendance Conversation Functions
# ----------------------------------------

def start_delete_attendance(update: Update, context: CallbackContext) -> int:
    """
    Start the delete specific attendance conversation flow.
    Shows a list of all users to help the admin choose a user ID.
    """
    query = update.callback_query
    query.answer()
    
    # Show all users to help admin choose
    users = database.get_all_users()
    user_list = "👥 Available Users:\n\n"
    
    for user in users:
        name = user.get('first_name', '')
        if user.get('last_name'):
            name += f" {user.get('last_name')}"
        username = f"@{user.get('username')}" if user.get('username') else "No username"
        user_list += f"ID: {user.get('user_id')} - {name} ({username})\n"
    
    query.edit_message_text(
        f"📅 Delete Attendance Record\n\n{user_list}\n\nPlease enter the ID of the user whose attendance record you want to delete:\n\n(Type /cancel to abort)"
    )
    
    return "WAITING_USER_ID"

def process_delete_attendance_user_id(update: Update, context: CallbackContext) -> int:
    """
    Process the user ID for deleting specific attendance.
    Validates the input, stores the user ID, and proceeds to date selection.
    """
    user_id_text = update.message.text.strip()
    
    # Validate that the input is a number
    try:
        user_id = int(user_id_text)
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found. Please try again or type /cancel to abort."
        )
        return "WAITING_USER_ID"
    
    # Store the user ID in context for next step
    context.user_data['target_user_id'] = user_id
    
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    context.user_data['target_user_name'] = name
    
    # Show recent attendance records
    history = database.get_user_history(user_id, limit=10)
    history_text = ""
    
    if history:
        history_text = "\nAttendance records:\n"
        for record in history:
            try:
                date_str = record.get("date").strftime("%Y-%m-%d")
                check_in = record.get("check_in", "N/A")
                check_out = record.get("check_out", "N/A")
                
                check_in_str = "N/A"
                if check_in != "N/A" and check_in is not None:
                    check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                
                check_out_str = "N/A"
                if check_out != "N/A" and check_out is not None:
                    check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                
                history_text += f"• {date_str}: {check_in_str} → {check_out_str}\n"
            except Exception:
                continue
    else:
        history_text = "\nNo attendance records found."
    
    # Prompt for date input
    update.message.reply_text(
        f"📅 Delete Attendance Record\n\n"
        f"Selected user: {name} (ID: {user_id})\n{history_text}\n\n"
        f"Please enter the date of the attendance record you want to delete (YYYY-MM-DD format):\n\n"
        f"(Type /cancel to abort)"
    )
    
    # Move to next state: waiting for date input
    return "WAITING_DATE"

def process_delete_attendance_date(update: Update, context: CallbackContext) -> int:
    """
    Process the date for deleting specific attendance.
    Validates the date, finds the matching record, and shows confirmation.
    """
    date_text = update.message.text.strip()
    user_id = context.user_data.get('target_user_id')
    name = context.user_data.get('target_user_name')
    
    # Validate date format
    try:
        date_obj = datetime.datetime.strptime(date_text, "%Y-%m-%d")
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        update.message.reply_text(
            "❌ Error: Invalid date format. Please use YYYY-MM-DD format or type /cancel to abort."
        )
        return "WAITING_DATE"
    
    # Check if there's a record for this date
    record, message = database.get_user_history_by_date(user_id, date_obj)
    
    if not record:
        update.message.reply_text(
            f"❌ No attendance record found for {name} on {date_text}.\n\n"
            f"Please try a different date or type /cancel to abort."
        )
        return "WAITING_DATE"
    
    # Format the record details
    check_in = record.get("check_in", "N/A")
    check_out = record.get("check_out", "N/A")
    
    check_in_str = "N/A"
    if check_in != "N/A" and check_in is not None:
        check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
    
    check_out_str = "N/A"
    if check_out != "N/A" and check_out is not None:
        check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
    
    record_details = f"Date: {date_text}\nCheck-in: {check_in_str}\nCheck-out: {check_out_str}"
    
    # Create keyboard for confirmation
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_record_{user_id}_{date_text}")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
    ]
    
    # Show confirmation message
    update.message.reply_text(
        f"⚠️ Delete Attendance Record Confirmation\n\n"
        f"Are you sure you want to delete the following attendance record for {name}?\n\n"
        f"{record_details}\n\n"
        f"This action cannot be undone.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    global reminder_scheduler
    
    # Create the Updater and pass it your bot's token
    updater = Updater(config.TELEGRAM_BOT_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # ============================================================================
    # CONVERSATION HANDLERS - INTERACTIVE ADMIN FLOWS
    # ============================================================================

    
    # User deletion conversation - Allows admins to delete users via an interactive flow
    # Flow: Show user list -> Admin enters user ID -> Confirmation screen -> Delete user
    delete_user_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_delete_user, pattern='^prompt_delete_user$')],
        states={
            'WAITING_USER_ID': [MessageHandler(Filters.text & ~Filters.command, process_delete_user_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_conversation)],
        allow_reentry=True
    )
    
    # Clear attendance conversation - Allows admins to clear all attendance for a user
    # Flow: Show user list -> Admin enters user ID -> Show attendance history -> Confirmation -> Clear
    clear_attendance_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_clear_attendance, pattern='^prompt_clear_attendance$')],
        states={
            'WAITING_USER_ID': [MessageHandler(Filters.text & ~Filters.command, process_clear_attendance_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_conversation)],
        allow_reentry=True
    )
    
    # User details conversation - Allows admins to view detailed user info
    # Flow: Show user list -> Admin enters user ID -> Display detailed user profile
    user_details_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_user_details, pattern='^prompt_user_details$')],
        states={
            'WAITING_USER_ID': [MessageHandler(Filters.text & ~Filters.command, process_user_details_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_conversation)],
        allow_reentry=True
    )
    
    # Delete specific attendance record conversation
    # Flow: Show user list -> Admin enters user ID -> Admin enters date -> Confirmation -> Delete
    delete_attendance_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_delete_attendance, pattern='^prompt_delete_attendance$')],
        states={
            'WAITING_USER_ID': [MessageHandler(Filters.text & ~Filters.command, process_delete_attendance_user_id)],
            'WAITING_DATE': [MessageHandler(Filters.text & ~Filters.command, process_delete_attendance_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_conversation)],
        allow_reentry=True
    )
    
    # Register conversation handlers (before the other handlers for priority)
    dispatcher.add_handler(delete_user_conv_handler)
    dispatcher.add_handler(clear_attendance_conv_handler)
    dispatcher.add_handler(user_details_conv_handler)
    dispatcher.add_handler(delete_attendance_conv_handler)
    
    # ============================================================================
    # REGULAR COMMAND HANDLERS
    # ============================================================================
    
    # General commands
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("menu", show_menu_command))
    dispatcher.add_handler(CommandHandler("keyboard", keyboard_command))
    dispatcher.add_handler(CommandHandler("admin", admin_menu_command))
    
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
    dispatcher.add_handler(CommandHandler("deleteattendance", delete_attendance_command))
    
    # ============================================================================
    # CALLBACK QUERY HANDLERS
    # ============================================================================
    
    # Interface callbacks (showing menus)
    dispatcher.add_handler(CallbackQueryHandler(interface_callback_handler, pattern="^show_"))
    
    # All other callbacks (admin operations, attendance, etc.)
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # ============================================================================
    # MESSAGE HANDLERS AND ERROR HANDLING
    # ============================================================================
    
    # Add handler for text messages (non-commands)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))
    
    # Register error handler
    dispatcher.add_error_handler(error_handler)
    
    # ============================================================================
    # STARTUP OPERATIONS
    # ============================================================================
    
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