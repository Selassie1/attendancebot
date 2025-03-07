# handlers/attendance.py
import logging
import calendar
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler
import database
import config

# Constants for callback data
CALENDAR_CALLBACK = "cal"
HISTORY_DATE_CALLBACK = "hist_date"
HISTORY_MONTH_CALLBACK = "hist_month"
HISTORY_RANGE_CALLBACK = "hist_range"

def get_user_menu_keyboard(is_admin=False):
    """Create an inline keyboard with user commands."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Check In", callback_data="cmd_checkin"),
            InlineKeyboardButton("🚪 Check Out", callback_data="cmd_checkout")
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="cmd_status"),
            InlineKeyboardButton("📆 History", callback_data="cmd_history")
        ]
    ]
    
    # Add admin panel button if the user is an admin
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("👑 Admin Dashboard", callback_data="show_admin_menu")
        ])
        
    return InlineKeyboardMarkup(keyboard)

def format_attendance_record(record, include_user=False):
    """Format an attendance record as a markdown message."""
    if not record:
        return "No record found."
    
    date_str = record["date"].strftime("%A, %B %d, %Y")
    check_in_str = record.get("check_in", "N/A")
    check_out_str = record.get("check_out", "N/A")
    duration = record.get("duration", "N/A")
    
    if check_in_str != "N/A":
        check_in_str = check_in_str.strftime("%H:%M:%S")
    
    if check_out_str != "N/A":
        check_out_str = check_out_str.strftime("%H:%M:%S")
    
    message = f"*📅 Date: {date_str}*\n"
    
    if include_user:
        user_name = database.get_user_name(record["user_id"])
        message += f"*👤 User: {user_name}*\n"
    
    message += f"*✅ Check-in:* {check_in_str}\n"
    message += f"*🚪 Check-out:* {check_out_str}\n"
    
    if duration != "N/A":
        # Add emoji based on duration
        emoji = "⏱️"
        if duration > 8:
            emoji = "🔥"  # Worked overtime
        elif duration < 4:
            emoji = "⚠️"  # Short day
        
        message += f"*{emoji} Duration:* {duration} hours\n"
    
    return message

def check_in_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /checkin command."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    success, message = database.check_in(user_id)
    
    # Format the message
    if success:
        formatted_message = f"✅ *{user_name}*, you have successfully checked in!\n\n"
        formatted_message += f"_Time: {datetime.now().strftime('%H:%M:%S')}_"
        
        # Notify admins
        admin_users = database.get_admin_users()
        if admin_users:  # Check if there are any admins
            for admin in admin_users:
                if admin["user_id"] != user_id:  # Don't notify the user if they're an admin
                    try:
                        admin_message = f"👤 *{database.get_user_name(user_id)}* has checked in at _{datetime.now().strftime('%H:%M:%S')}_"
                        context.bot.send_message(
                            chat_id=admin["user_id"],
                            text=admin_message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        logging.info(f"Sent check-in notification to admin {admin['user_id']}")
                    except Exception as e:
                        logging.error(f"Failed to send admin notification: {e}")
        else:
            logging.warning("No admin users found for notifications")
    else:
        formatted_message = f"❌ *{user_name}*, {message}"
    
    # Add keyboard (with admin button if applicable)
    keyboard = get_user_menu_keyboard(is_admin)
    
    # Send the message
    update.message.reply_text(
        formatted_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

def check_out_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /checkout command."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    success, message = database.check_out(user_id)
    
    # Format the message
    if success:
        # Get duration from the message
        import re
        duration_match = re.search(r"Duration: ([\d.]+) hours", message)
        duration = duration_match.group(1) if duration_match else "unknown"
        
        formatted_message = f"🚪 *{user_name}*, you have successfully checked out!\n\n"
        formatted_message += f"_Time: {datetime.now().strftime('%H:%M:%S')}_\n"
        formatted_message += f"_Duration: {duration} hours_"
        
        # Notify admins
        admin_users = database.get_admin_users()
        if admin_users:  # Check if there are any admins
            for admin in admin_users:
                if admin["user_id"] != user_id:  # Don't notify the user if they're an admin
                    try:
                        admin_message = f"👤 *{database.get_user_name(user_id)}* has checked out at _{datetime.now().strftime('%H:%M:%S')}_\n"
                        admin_message += f"_Duration: {duration} hours_"
                        context.bot.send_message(
                            chat_id=admin["user_id"],
                            text=admin_message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        logging.info(f"Sent check-out notification to admin {admin['user_id']}")
                    except Exception as e:
                        logging.error(f"Failed to send admin notification: {e}")
        else:
            logging.warning("No admin users found for notifications")
    else:
        formatted_message = f"❌ *{user_name}*, {message}"
    
    # Add keyboard (with admin button if applicable)
    keyboard = get_user_menu_keyboard(is_admin)
    
    # Send the message
    update.message.reply_text(
        formatted_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

def status_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /status command."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    status = database.get_user_status(user_id)
    
    # Format the message
    formatted_message = f"📊 *{user_name}'s Status*\n\n"
    formatted_message += f"_{status}_"
    
    # Add keyboard (with admin button if applicable)
    keyboard = get_user_menu_keyboard(is_admin)
    
    # Send the message
    update.message.reply_text(
        formatted_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

def create_month_selector():
    """Create a month selector keyboard."""
    now = datetime.now()
    keyboard = []
    
    # Add buttons for the last 6 months
    row = []
    for i in range(5, -1, -1):
        month_date = now.replace(day=1) - timedelta(days=1)
        for _ in range(i):
            month_date = month_date.replace(day=1) - timedelta(days=1)
        
        month_name = month_date.strftime("%b %Y")
        callback_data = f"{HISTORY_MONTH_CALLBACK}_{month_date.year}_{month_date.month}"
        
        row.append(InlineKeyboardButton(month_name, callback_data=callback_data))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:  # Add any remaining buttons
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="cmd_history")])
    
    return InlineKeyboardMarkup(keyboard)

def create_date_selector(year, month):
    """Create a date selector keyboard for a specific month."""
    keyboard = []
    
    # Add month name as header
    month_name = datetime(year, month, 1).strftime("%B %Y")
    keyboard.append([InlineKeyboardButton(f"📅 {month_name}", callback_data="header")])
    
    # Add weekday headers
    weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    keyboard.append([InlineKeyboardButton(day, callback_data=f"weekday_{i}") for i, day in enumerate(weekdays)])
    
    # Get the calendar for the month
    cal = calendar.monthcalendar(year, month)
    
    # Add day buttons
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                # Empty cell
                row.append(InlineKeyboardButton(" ", callback_data="empty"))
            else:
                # Day button
                date_str = f"{year}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(str(day), callback_data=f"{HISTORY_DATE_CALLBACK}_{date_str}"))
        keyboard.append(row)
    
    # Add navigation buttons
    nav_row = []
    
    # Previous month
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    nav_row.append(InlineKeyboardButton("◀️", callback_data=f"{CALENDAR_CALLBACK}_{prev_year}_{prev_month}"))
    
    # Back to history
    nav_row.append(InlineKeyboardButton("🔙 Back", callback_data="cmd_history"))
    
    # Next month
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    nav_row.append(InlineKeyboardButton("▶️", callback_data=f"{CALENDAR_CALLBACK}_{next_year}_{next_month}"))
    
    keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard)

def history_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /history command."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    # Check if a date was provided
    args = context.args
    if args and len(args) > 0:
        try:
            # Try to parse as a specific date
            target_date = args[0]
            record, message = database.get_user_history_by_date(user_id, target_date)
            
            if record:
                formatted_record = format_attendance_record(record)
                update.message.reply_text(
                    f"📆 *{user_name}'s Attendance*\n\n{formatted_record}",
                    reply_markup=get_user_menu_keyboard(is_admin),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                update.message.reply_text(
                    f"❌ *{user_name}*, {message}",
                    reply_markup=get_user_menu_keyboard(is_admin),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        except ValueError:
            pass  # Ignore and continue to show main history menu
    
    # Show history options
    keyboard = [
        [InlineKeyboardButton("📅 Select Date", callback_data=f"{CALENDAR_CALLBACK}_{datetime.now().year}_{datetime.now().month}")],
        [InlineKeyboardButton("📊 View Recent History", callback_data="cmd_recent_history")],
        [InlineKeyboardButton("📋 Monthly Report", callback_data="cmd_monthly_history")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="cmd_main_menu")]
    ]
    
    # Add admin button if the user is an admin
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Dashboard", callback_data="show_admin_menu")])
    
    update.message.reply_text(
        f"📆 *{user_name}'s Attendance History*\n\n"
        "Please select an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

def handle_history_callback(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from history menu."""
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user = database.get_user(user_id)
    is_admin = user and user.get("is_admin", False)
    
    # Acknowledge the callback
    query.answer()
    
    # Check for month selection
    if query.data.startswith(f"{HISTORY_MONTH_CALLBACK}_"):
        # Handle month selection
        try:
            # Split correctly and make sure we have enough parts
            parts = query.data.split("_")
            if len(parts) == 3:  # Format: hist_month_YEAR_MONTH
                year_str, month_str = parts[1], parts[2]
                year, month = int(year_str), int(month_str)
                
                # Get attendance for this month
                attendance = database.get_month_attendance(year, month)
                
                # Filter for this user
                user_attendance = [record for record in attendance if record["user_id"] == user_id]
                
                if not user_attendance:
                    query.edit_message_text(
                        f"❌ *{user_name}*, you don't have any attendance records for {datetime(year, month, 1).strftime('%B %Y')}.",
                        reply_markup=create_month_selector(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Calculate statistics
                total_days = len(user_attendance)
                complete_days = sum(1 for record in user_attendance if "check_out" in record)
                total_hours = sum(record.get("duration", 0) for record in user_attendance if "duration" in record)
                avg_hours = total_hours / complete_days if complete_days > 0 else 0
                
                # Create summary message
                month_name = datetime(year, month, 1).strftime("%B %Y")
                message = f"📊 *{user_name}'s Attendance for {month_name}*\n\n"
                message += f"*🗓️ Total Days:* {total_days}\n"
                message += f"*✅ Complete Days:* {complete_days}\n"
                message += f"*⚠️ Incomplete Days:* {total_days - complete_days}\n"
                message += f"*⏱️ Total Hours:* {total_hours:.2f}\n"
                message += f"*📈 Average Hours/Day:* {avg_hours:.2f}\n\n"
                
                message += "*📅 Daily Breakdown:*\n"
                
                # Add records (limit to first 10 to avoid message too long)
                for i, record in enumerate(user_attendance[:10]):
                    date_str = record["date"].strftime("%d %b")
                    check_in = record.get("check_in", "N/A")
                    check_out = record.get("check_out", "N/A")
                    duration = record.get("duration", "N/A")
                    
                    if check_in != "N/A":
                        check_in = check_in.strftime("%H:%M")
                    
                    if check_out != "N/A":
                        check_out = check_out.strftime("%H:%M")
                        duration_str = f"{duration} hrs"
                    else:
                        duration_str = "Incomplete"
                    
                    message += f"*{date_str}:* {check_in} → {check_out} ({duration_str})\n"
                
                if len(user_attendance) > 10:
                    message += "_(Showing first 10 days only)_\n"
                
                query.edit_message_text(
                    message,
                    reply_markup=create_month_selector(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Invalid callback data format
                logging.error(f"Invalid month callback format: {query.data}")
                query.edit_message_text(
                    f"❌ *{user_name}*, there was an error processing your request.",
                    reply_markup=create_month_selector(),
                    parse_mode=ParseMode.MARKDOWN
                )
        except ValueError as e:
            logging.error(f"Error in month selection: {e}")
            query.edit_message_text(
                f"❌ *{user_name}*, there was an error processing your request.",
                reply_markup=create_month_selector(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Unexpected error in month selection: {e}")
            query.edit_message_text(
                f"❌ *{user_name}*, there was an error processing your request.",
                reply_markup=create_month_selector(),
                parse_mode=ParseMode.MARKDOWN
            )
    elif query.data.startswith(CALENDAR_CALLBACK):
        # Handle calendar navigation
        try:
            parts = query.data.split("_")
            if len(parts) >= 3:
                year_str, month_str = parts[1], parts[2]
                year, month = int(year_str), int(month_str)
                
                query.edit_message_text(
                    f"📅 *{user_name}'s Attendance*\n\n"
                    f"Please select a date from {datetime(year, month, 1).strftime('%B %Y')}:",
                    reply_markup=create_date_selector(year, month),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Handle malformed data
                query.edit_message_text(
                    f"❌ *{user_name}*, there was an error with the calendar.",
                    reply_markup=get_user_menu_keyboard(is_admin),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error in calendar navigation: {e}")
            query.edit_message_text(
                f"❌ *{user_name}*, there was an error with the calendar.",
                reply_markup=get_user_menu_keyboard(is_admin),
                parse_mode=ParseMode.MARKDOWN
            )
    elif query.data.startswith(HISTORY_DATE_CALLBACK):
        # Handle date selection
        try:
            parts = query.data.split("_", 2)  # Split into max 3 parts
            if len(parts) >= 3:
                date_str = parts[2]  # Get the date part
                
                record, message = database.get_user_history_by_date(user_id, date_str)
                
                if record:
                    formatted_record = format_attendance_record(record)
                    query.edit_message_text(
                        f"📆 *{user_name}'s Attendance*\n\n{formatted_record}",
                        reply_markup=get_user_menu_keyboard(is_admin),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    query.edit_message_text(
                        f"❌ *{user_name}*, no attendance record found for {date_str}.",
                        reply_markup=get_user_menu_keyboard(is_admin),
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                # Handle malformed data
                query.edit_message_text(
                    f"❌ *{user_name}*, there was an error processing your request.",
                    reply_markup=get_user_menu_keyboard(is_admin),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logging.error(f"Error in date selection: {e}")
            query.edit_message_text(
                f"❌ *{user_name}*, there was an error processing your request.",
                reply_markup=get_user_menu_keyboard(is_admin),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cmd_main_menu":
        # Go back to main menu
        query.edit_message_text(
            f"👋 Hello *{user_name}*!\n\n"
            "What would you like to do?",
            reply_markup=get_user_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Handle other commands
    elif query.data == "cmd_checkin":
        # Execute check-in
        success, message = database.check_in(user_id)
        
        # Format the message
        if success:
            formatted_message = f"✅ *{user_name}*, you have successfully checked in!\n\n"
            formatted_message += f"_Time: {datetime.now().strftime('%H:%M:%S')}_"
            
            # Notify admins
            admin_users = database.get_admin_users()
            if admin_users:  # Check if there are any admins
                for admin in admin_users:
                    if admin["user_id"] != user_id:  # Don't notify the user if they're an admin
                        try:
                            admin_message = f"👤 *{database.get_user_name(user_id)}* has checked in at _{datetime.now().strftime('%H:%M:%S')}_"
                            context.bot.send_message(
                                chat_id=admin["user_id"],
                                text=admin_message,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            logging.info(f"Sent check-in notification to admin {admin['user_id']}")
                        except Exception as e:
                            logging.error(f"Failed to send admin notification: {e}")
            else:
                logging.warning("No admin users found for notifications")
        else:
            formatted_message = f"❌ *{user_name}*, {message}"
        
        query.edit_message_text(
            formatted_message,
            reply_markup=get_user_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "cmd_checkout":
        # Execute check-out
        success, message = database.check_out(user_id)
        
        # Format the message
        if success:
            # Get duration from the message
            import re
            duration_match = re.search(r"Duration: ([\d.]+) hours", message)
            duration = duration_match.group(1) if duration_match else "unknown"
            
            formatted_message = f"🚪 *{user_name}*, you have successfully checked out!\n\n"
            formatted_message += f"_Time: {datetime.now().strftime('%H:%M:%S')}_\n"
            formatted_message += f"_Duration: {duration} hours_"
            
            # Notify admins
            admin_users = database.get_admin_users()
            if admin_users:  # Check if there are any admins
                for admin in admin_users:
                    if admin["user_id"] != user_id:  # Don't notify the user if they're an admin
                        try:
                            admin_message = f"👤 *{database.get_user_name(user_id)}* has checked out at _{datetime.now().strftime('%H:%M:%S')}_\n"
                            admin_message += f"_Duration: {duration} hours_"
                            context.bot.send_message(
                                chat_id=admin["user_id"],
                                text=admin_message,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            logging.info(f"Sent check-out notification to admin {admin['user_id']}")
                        except Exception as e:
                            logging.error(f"Failed to send admin notification: {e}")
            else:
                logging.warning("No admin users found for notifications")
        else:
            formatted_message = f"❌ *{user_name}*, {message}"
        
        query.edit_message_text(
            formatted_message,
            reply_markup=get_user_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "cmd_status":
        # Execute status check
        status = database.get_user_status(user_id)
        
        # Format the message
        formatted_message = f"📊 *{user_name}'s Status*\n\n"
        formatted_message += f"_{status}_"
        
        query.edit_message_text(
            formatted_message,
            reply_markup=get_user_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "cmd_history":
        # Show history options
        keyboard = [
            [InlineKeyboardButton("📅 Select Date", callback_data=f"{CALENDAR_CALLBACK}_{datetime.now().year}_{datetime.now().month}")],
            [InlineKeyboardButton("📊 View Recent History", callback_data="cmd_recent_history")],
            [InlineKeyboardButton("📋 Monthly Report", callback_data="cmd_monthly_history")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="cmd_main_menu")]
        ]
        
        query.edit_message_text(
            f"📆 *{user_name}'s Attendance History*\n\n"
            "Please select an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        ) 