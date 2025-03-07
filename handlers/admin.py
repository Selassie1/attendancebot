# handlers/admin.py
import logging
import datetime
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import database
from utils.dashboard import generate_attendance_report, generate_dashboard_image
import config

def get_admin_menu_keyboard():
    """Create an inline keyboard with admin commands."""
    keyboard = [
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("📊 Today's Attendance", callback_data="admin_attendance")
        ],
        [
            InlineKeyboardButton("📝 Report", callback_data="admin_report"),
            InlineKeyboardButton("📈 Dashboard", callback_data="admin_dashboard")
        ],
        [
            InlineKeyboardButton("🔄 Worker Menu", callback_data="show_worker_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_required(func):
    """Decorator to restrict access to admin users only."""
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is admin
        user = database.get_user(user_id)
        if not user or not user.get("is_admin", False):
            update.message.reply_text(
                "❌ Sorry, this command is only available to administrators.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        return func(update, context, *args, **kwargs)
    
    return wrapper

@admin_required
def users_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /users command."""
    users = database.get_all_users()
    
    if not users:
        update.message.reply_text(
            "❌ No users registered yet.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    messages = ["👥 *Registered Users:*\n"]
    
    for user in users:
        admin_status = "👑 Admin" if user.get("is_admin", False) else "👤 Worker"
        name = f"{user['first_name']} {user.get('last_name', '')}"
        username = f"@{user['username']}" if user.get("username") else "No username"
        
        messages.append(
            f"*ID:* `{user['user_id']}`\n"
            f"*Name:* {name.strip()}\n"
            f"*Username:* {username}\n"
            f"*Role:* {admin_status}\n"
        )
    
    # Send in chunks to avoid message too long error
    full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
    max_length = 4000
    
    if len(full_message) <= max_length:
        update.message.reply_text(
            full_message,
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Send in chunks
        for i in range(0, len(full_message), max_length):
            chunk = full_message[i:i+max_length]
            
            # Only add keyboard to the last chunk
            if i + max_length >= len(full_message):
                update.message.reply_text(
                    chunk,
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )

@admin_required
def attendance_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /attendance command."""
    attendance = database.get_today_attendance()
    
    if not attendance:
        update.message.reply_text(
            "❌ No attendance records for today.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    messages = ["📊 *Today's Attendance:*\n"]
    
    # Sort by check-in time
    attendance.sort(key=lambda x: x.get("check_in", datetime.datetime.max))
    
    for record in attendance:
        user = database.get_user(record["user_id"])
        name = f"{user['first_name']} {user.get('last_name', '')}" if user else f"User {record['user_id']}"
        
        check_in = record.get("check_in", "N/A")
        check_out = record.get("check_out", "N/A")
        duration = record.get("duration", "N/A")
        
        if check_in != "N/A":
            check_in = check_in.strftime("%H:%M:%S")
        
        if check_out != "N/A":
            check_out = check_out.strftime("%H:%M:%S")
            status = "✅ Complete"
        else:
            status = "⏳ In Progress"
        
        messages.append(
            f"*👤 {name.strip()}*\n"
            f"*Status:* {status}\n"
            f"*✅ Check-in:* {check_in}\n"
            f"*🚪 Check-out:* {check_out}\n"
            f"*⏱️ Duration:* {duration} hours\n"
        )
    
    # Send in chunks to avoid message too long error
    full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
    max_length = 4000
    
    if len(full_message) <= max_length:
        update.message.reply_text(
            full_message,
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Send in chunks
        for i in range(0, len(full_message), max_length):
            chunk = full_message[i:i+max_length]
            
            # Only add keyboard to the last chunk
            if i + max_length >= len(full_message):
                update.message.reply_text(
                    chunk,
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )

def create_date_range_keyboard():
    """Create a keyboard for selecting date ranges for reports."""
    now = datetime.datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    keyboard = [
        [InlineKeyboardButton("Today", callback_data=f"report_range_{today.strftime('%Y-%m-%d')}_{today.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton("Last 7 Days", callback_data=f"report_range_{(today - datetime.timedelta(days=6)).strftime('%Y-%m-%d')}_{today.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton("Last 30 Days", callback_data=f"report_range_{(today - datetime.timedelta(days=29)).strftime('%Y-%m-%d')}_{today.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton("This Month", callback_data=f"report_range_{today.replace(day=1).strftime('%Y-%m-%d')}_{today.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton("Custom Range", callback_data="report_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

@admin_required
def report_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /report command."""
    args = context.args
    
    if not args:
        # No arguments, show date range selection
        update.message.reply_text(
            "📝 *Generate Attendance Report*\n\n"
            "Please select a date range:",
            reply_markup=create_date_range_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        if len(args) >= 2:
            # Parse date range from arguments
            start_date = datetime.datetime.strptime(args[0], "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.datetime.strptime(args[1], "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to last 7 days
            end_date = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - datetime.timedelta(days=6)  # 7 days including today
        
        # Generate report
        csv_data, message = generate_attendance_report(start_date, end_date)
        
        if csv_data:
            # Send CSV file
            date_range = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
            filename = f"attendance_report_{date_range}.csv"
            
            update.message.reply_document(
                document=csv_data.encode(),
                filename=filename,
                caption=f"📝 Attendance report for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    except ValueError:
        update.message.reply_text(
            "❌ Invalid date format. Please use YYYY-MM-DD format.\n"
            "Example: `/report 2023-01-01 2023-01-31`",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logging.error(f"Error generating report: {e}")
        update.message.reply_text(
            f"❌ Error generating report: {str(e)}",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def create_dashboard_options_keyboard():
    """Create a keyboard for dashboard options."""
    keyboard = [
        [InlineKeyboardButton("Last 7 Days", callback_data="dashboard_7")],
        [InlineKeyboardButton("Last 14 Days", callback_data="dashboard_14")],
        [InlineKeyboardButton("Last 30 Days", callback_data="dashboard_30")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

@admin_required
def dashboard_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /dashboard command."""
    args = context.args
    
    if not args:
        # No arguments, show options
        update.message.reply_text(
            "📈 *Attendance Dashboard*\n\n"
            "Please select a time period:",
            reply_markup=create_dashboard_options_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        days = 7  # Default
        if args and args[0].isdigit():
            days = int(args[0])
            if days < 1 or days > 30:
                update.message.reply_text(
                    "❌ Days must be between 1 and 30.",
                    reply_markup=create_dashboard_options_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Generate dashboard
        dashboard_image, message = generate_dashboard_image(days)
        
        if dashboard_image:
            # Send image
            update.message.reply_photo(
                photo=dashboard_image,
                caption=f"📈 Attendance dashboard for the last {days} days",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logging.error(f"Error generating dashboard: {e}")
        update.message.reply_text(
            f"❌ Error generating dashboard: {str(e)}",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def handle_admin_callback(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from admin menu."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Acknowledge the callback
    query.answer()
    
    # Photo messages can't be edited with text - handled by the main callback handler
    if query.message.photo:
        return
    
    # Handle user/record deletion callbacks
    if query.data.startswith("delete_user_"):
        # Extract user ID from callback data
        try:
            target_user_id = int(query.data.split("_")[2])
            user = database.get_user(target_user_id)
            
            if not user:
                query.edit_message_text(
                    "❌ *Error*: User not found.",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Ask for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_user_{target_user_id}"),
                    InlineKeyboardButton("❌ No, Cancel", callback_data="admin_users")
                ]
            ]
            
            query.edit_message_text(
                f"⚠️ *Confirm User Deletion*\n\n"
                f"Are you sure you want to delete the user *{user['first_name']}* (ID: `{target_user_id}`)?\n\n"
                f"This will permanently delete the user and all their attendance records.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Error in delete_user callback: {e}")
            query.edit_message_text(
                "❌ *Error*: Invalid user ID.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith("confirm_delete_user_"):
        # Extract user ID from callback data
        try:
            target_user_id = int(query.data.split("_")[3])
            
            # Delete the user
            success, message = database.delete_user(target_user_id)
            
            if success:
                query.edit_message_text(
                    f"✅ *Success*: {message}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                query.edit_message_text(
                    f"❌ *Error*: {message}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error in confirm_delete_user callback: {e}")
            query.edit_message_text(
                "❌ *Error*: Failed to delete user.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith("clear_attendance_"):
        # Extract user ID from callback data
        try:
            target_user_id = int(query.data.split("_")[2])
            user = database.get_user(target_user_id)
            
            if not user:
                query.edit_message_text(
                    "❌ *Error*: User not found.",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Ask for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Clear All", callback_data=f"confirm_clear_attendance_{target_user_id}"),
                    InlineKeyboardButton("❌ No, Cancel", callback_data=f"userdetails_{target_user_id}")
                ]
            ]
            
            query.edit_message_text(
                f"⚠️ *Confirm Attendance Clearing*\n\n"
                f"Are you sure you want to clear all attendance records for *{user['first_name']}* (ID: `{target_user_id}`)?\n\n"
                f"This will permanently delete all attendance history for this user.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Error in clear_attendance callback: {e}")
            query.edit_message_text(
                "❌ *Error*: Invalid user ID.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith("confirm_clear_attendance_"):
        # Extract user ID from callback data
        try:
            target_user_id = int(query.data.split("_")[3])
            user = database.get_user(target_user_id)
            
            if not user:
                query.edit_message_text(
                    "❌ *Error*: User not found.",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Clear attendance records
            success, message = database.clear_user_attendance(target_user_id)
            
            if success:
                query.edit_message_text(
                    f"✅ *Success*: {message} for user {user['first_name']}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                query.edit_message_text(
                    f"❌ *Error*: {message}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error in confirm_clear_attendance callback: {e}")
            query.edit_message_text(
                "❌ *Error*: Failed to clear attendance records.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith("userdetails_"):
        # Extract user ID from callback data
        try:
            target_user_id = int(query.data.split("_")[1])
            
            # Get the user
            user = database.get_user(target_user_id)
            if not user:
                query.edit_message_text(
                    "❌ *Error*: User not found.",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Get the user's recent attendance history
            history = database.get_user_history(target_user_id, limit=5)
            
            # Create user details message
            message = f"👤 *User Details*\n\n"
            message += f"*ID:* `{user['user_id']}`\n"
            message += f"*Name:* {user['first_name']} {user.get('last_name', '')}\n"
            message += f"*Username:* {f'@{user['username']}' if user.get('username') else 'None'}\n"
            message += f"*Role:* {'Admin' if user.get('is_admin', False) else 'Worker'}\n"
            message += f"*Registered:* {user.get('created_at', 'Unknown').strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Add recent attendance
            if history:
                message += "*Recent Attendance:*\n"
                for record in history:
                    date_str = record["date"].strftime("%Y-%m-%d")
                    check_in = record.get("check_in", "N/A")
                    check_out = record.get("check_out", "N/A")
                    duration = record.get("duration", "N/A")
                    
                    if check_in != "N/A":
                        check_in = check_in.strftime("%H:%M:%S")
                    
                    if check_out != "N/A":
                        check_out = check_out.strftime("%H:%M:%S")
                    
                    message += f"• *{date_str}*: {check_in} → {check_out} ({duration} hours)\n"
            else:
                message += "*No attendance records found.*\n"
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🗑️ Delete User", callback_data=f"delete_user_{target_user_id}"),
                    InlineKeyboardButton("🧹 Clear Attendance", callback_data=f"clear_attendance_{target_user_id}")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_users")]
            ]
            
            query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Error in userdetails callback: {e}")
            query.edit_message_text(
                "❌ *Error*: Failed to get user details.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Default admin menu handlers
    elif query.data == "admin_menu":
        query.edit_message_text(
            "👑 *Admin Panel*\n\n"
            "Please select an option:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "admin_users":
        # Execute users command
        users = database.get_all_users()
        
        if not users:
            query.edit_message_text(
                "❌ No users registered yet.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        messages = ["👥 *Registered Users:*\n"]
        
        for user in users:
            admin_status = "👑 Admin" if user.get("is_admin", False) else "👤 Worker"
            name = f"{user['first_name']} {user.get('last_name', '')}"
            username = f"@{user['username']}" if user.get("username") else "No username"
            
            messages.append(
                f"*ID:* `{user['user_id']}`\n"
                f"*Name:* {name.strip()}\n"
                f"*Username:* {username}\n"
                f"*Role:* {admin_status}\n"
            )
        
        # Join messages with separators
        full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
        
        # Check if message is too long
        if len(full_message) > 4000:
            # Truncate and send as new message
            query.edit_message_text(
                messages[0] + "\n" + "_Showing partial list due to length limitations_",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send the rest as a new message
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="\n➖➖➖➖➖➖➖➖➖➖\n".join(messages[1:10]),
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            query.edit_message_text(
                full_message,
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "admin_attendance":
        # Execute attendance command
        attendance = database.get_today_attendance()
        
        if not attendance:
            query.edit_message_text(
                "❌ No attendance records for today.",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        messages = ["📊 *Today's Attendance:*\n"]
        
        # Sort by check-in time
        attendance.sort(key=lambda x: x.get("check_in", datetime.datetime.max))
        
        for record in attendance:
            user = database.get_user(record["user_id"])
            name = f"{user['first_name']} {user.get('last_name', '')}" if user else f"User {record['user_id']}"
            
            check_in = record.get("check_in", "N/A")
            check_out = record.get("check_out", "N/A")
            duration = record.get("duration", "N/A")
            
            if check_in != "N/A":
                check_in = check_in.strftime("%H:%M:%S")
            
            if check_out != "N/A":
                check_out = check_out.strftime("%H:%M:%S")
                status = "✅ Complete"
            else:
                status = "⏳ In Progress"
            
            messages.append(
                f"*👤 {name.strip()}*\n"
                f"*Status:* {status}\n"
                f"*✅ Check-in:* {check_in}\n"
                f"*🚪 Check-out:* {check_out}\n"
                f"*⏱️ Duration:* {duration} hours\n"
            )
        
        # Join messages with separators
        full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
        
        # Check if message is too long
        if len(full_message) > 4000:
            # Truncate and send as new message
            query.edit_message_text(
                messages[0] + "\n" + "_Showing partial list due to length limitations_",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send the rest as a new message
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="\n➖➖➖➖➖➖➖➖➖➖\n".join(messages[1:10]),
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            query.edit_message_text(
                full_message,
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "admin_report":
        # Show report options
        query.edit_message_text(
            "📝 *Generate Attendance Report*\n\n"
            "Please select a date range:",
            reply_markup=create_date_range_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data.startswith("report_range_"):
        # Handle report date range selection
        _, start_date_str, end_date_str = query.data.split("_")[1:]
        
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Update message to show loading
            query.edit_message_text(
                "📝 *Generating report...*\n\n"
                "_This may take a moment._",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Generate report
            csv_data, message = generate_attendance_report(start_date, end_date)
            
            if csv_data:
                # Send CSV file
                date_range = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
                filename = f"attendance_report_{date_range}.csv"
                
                context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=csv_data.encode(),
                    filename=filename,
                    caption=f"📝 Attendance report for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
                
                # Update original message
                query.message.edit_text(
                    "📝 *Report Generated Successfully*",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                query.edit_message_text(
                    f"❌ {message}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            query.edit_message_text(
                f"❌ Error generating report: {str(e)}",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "admin_dashboard":
        # Show dashboard options
        query.edit_message_text(
            "📈 *Attendance Dashboard*\n\n"
            "Please select a time period:",
            reply_markup=create_dashboard_options_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data.startswith("dashboard_"):
        # Handle dashboard time period selection
        days = int(query.data.split("_")[1])
        
        try:
            # Update message to show loading
            query.edit_message_text(
                "📈 *Generating dashboard...*\n\n"
                "_This may take a moment._",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Generate dashboard
            dashboard_image, message = generate_dashboard_image(days)
            
            if dashboard_image:
                # Send image
                context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=dashboard_image,
                    caption=f"📈 Attendance dashboard for the last {days} days",
                    reply_markup=get_admin_menu_keyboard()
                )
                
                # Update original message
                query.message.edit_text(
                    "📈 *Dashboard Generated Successfully*",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                query.edit_message_text(
                    f"❌ {message}",
                    reply_markup=get_admin_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error generating dashboard: {e}")
            query.edit_message_text(
                f"❌ Error generating dashboard: {str(e)}",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            ) 