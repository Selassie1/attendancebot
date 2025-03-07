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
            InlineKeyboardButton("🔧 User Management", callback_data="admin_user_management")
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
        try:
            admin_status = "👑 Admin" if user.get("is_admin", False) else "👤 Worker"
            
            # Escape Markdown characters in names
            first_name = user['first_name'].replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            last_name = user.get('last_name', '') 
            if last_name:
                last_name = last_name.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            name = f"{first_name} {last_name}".strip()
            
            # Safe username handling
            username_str = user.get("username", "")
            if username_str:
                username = f"@{username_str}"
            else:
                username = "No username"
            
            messages.append(
                f"*ID:* `{user['user_id']}`\n"
                f"*Name:* {name}\n"
                f"*Username:* {username}\n"
                f"*Role:* {admin_status}\n"
            )
        except Exception as e:
            logging.error(f"Error processing user: {e}")
            continue
    
    # Send in chunks to avoid message too long error
    full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
    max_length = 4000
    
    try:
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
    except Exception as e:
        logging.error(f"Error sending users message: {e}")
        update.message.reply_text(
            "❌ Error displaying user data. Please try again.",
            reply_markup=get_admin_menu_keyboard(),
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
        try:
            user = database.get_user(record["user_id"])
            
            if user:
                # Escape Markdown characters in names
                first_name = user['first_name'].replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                last_name = user.get('last_name', '').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                name = f"{first_name} {last_name}".strip()
            else:
                name = f"User {record['user_id']}"
            
            # Get time info with safe string conversion
            check_in = record.get("check_in", "N/A")
            check_in_str = "N/A"
            if check_in != "N/A" and check_in is not None:
                try:
                    check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                except:
                    check_in_str = str(check_in)
            
            # Get first check-in time for multiple sessions
            first_check_in = record.get("first_check_in", check_in)
            first_check_in_str = "N/A"
            if first_check_in != "N/A" and first_check_in is not None:
                try:
                    first_check_in_str = first_check_in.strftime("%H:%M:%S") if hasattr(first_check_in, "strftime") else str(first_check_in)
                except:
                    first_check_in_str = str(first_check_in)
            
            check_out = record.get("check_out", "N/A")
            check_out_str = "N/A"
            if check_out != "N/A" and check_out is not None:
                try:
                    check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                    status = "✅ Complete"
                except:
                    check_out_str = str(check_out)
                    status = "⚠️ Error"
            else:
                status = "⏳ In Progress"
            
            duration = record.get("duration", "N/A")
            
            entry = f"👤 {name}\n"
            entry += f"Status: {status}\n"
            
            if record.get("check_ins", []) > 1:
                entry += f"First Check-in: {first_check_in_str}\n"
                entry += f"Last Check-out: {check_out_str}\n"
                entry += f"⏱️ Total Duration: {duration} hours\n"
                entry += f"(Multiple check-ins/outs today)\n"
            else:
                entry += f"✅ Check-in: {check_in_str}\n"
                entry += f"🚪 Check-out: {check_out_str}\n"
                entry += f"⏱️ Duration: {duration} hours\n"
            
            messages.append(entry)
        except Exception as e:
            logging.error(f"Error processing attendance record: {e}")
            continue
    
    # Send in chunks to avoid message too long error
    full_message = "\n➖➖➖➖➖➖➖➖➖➖\n".join(messages)
    max_length = 4000
    
    try:
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
    except Exception as e:
        logging.error(f"Error sending attendance message: {e}")
        update.message.reply_text(
            "❌ Error displaying attendance data. Please try again.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

def create_date_range_keyboard():
    """Create a keyboard for selecting date ranges for reports."""
    try:
        now = datetime.datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Safely format dates for callbacks
        try:
            today_str = today.strftime('%Y-%m-%d')
            week_ago_str = (today - datetime.timedelta(days=6)).strftime('%Y-%m-%d')
            month_ago_str = (today - datetime.timedelta(days=29)).strftime('%Y-%m-%d')
            month_start_str = today.replace(day=1).strftime('%Y-%m-%d')
        except Exception as e:
            logging.error(f"Error formatting dates for keyboard: {e}")
            # Use hardcoded date format as fallback
            today_str = now.strftime('%Y-%m-%d')
            week_ago_str = (now - datetime.timedelta(days=6)).strftime('%Y-%m-%d')
            month_ago_str = (now - datetime.timedelta(days=29)).strftime('%Y-%m-%d')
            month_start_str = now.strftime('%Y-%m') + '-01'
        
        keyboard = [
            [InlineKeyboardButton("Today", callback_data=f"report_range_{today_str}_{today_str}")],
            [InlineKeyboardButton("Last 7 Days", callback_data=f"report_range_{week_ago_str}_{today_str}")],
            [InlineKeyboardButton("Last 30 Days", callback_data=f"report_range_{month_ago_str}_{today_str}")],
            [InlineKeyboardButton("This Month", callback_data=f"report_range_{month_start_str}_{today_str}")],
            [InlineKeyboardButton("Custom Range", callback_data="report_custom")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logging.error(f"Error creating date range keyboard: {e}")
        # Fallback to a simpler keyboard
        keyboard = [
            [InlineKeyboardButton("Last 7 Days", callback_data="report_range_7")],
            [InlineKeyboardButton("Last 30 Days", callback_data="report_range_30")],
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
    """
    Handle callback queries from admin menu and actions.
    
    This is the central handler for all admin-related callback queries, 
    including user management, attendance management, and reports.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Acknowledge the callback
    query.answer()
    
    # Photo messages can't be edited with text - handled by the main callback handler
    if query.message.photo:
        return
    
    # Handle user/record deletion callbacks
    try:
        # ============================================================================
        # MAIN ADMIN MENU HANDLERS
        # ============================================================================
        
        # Default admin menu handlers
        if query.data == "admin_menu":
            query.edit_message_text(
                "👑 *Admin Panel*\n\n"
                "Please select an option:",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "admin_user_management":
            # Show a simplified version of user management options
            keyboard = [
                [InlineKeyboardButton("👥 List All Users", callback_data="admin_users")],
                [
                    InlineKeyboardButton("🗑️ Delete User", callback_data="prompt_delete_user"),
                    InlineKeyboardButton("🧹 Clear Attendance", callback_data="prompt_clear_attendance")
                ],
                [
                    InlineKeyboardButton("👤 User Details", callback_data="prompt_user_details"),
                    InlineKeyboardButton("📅 Delete Attendance", callback_data="prompt_delete_attendance")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
            ]
            
            # Use a simpler approach without complex formatting
            simple_text = "🔧 User Management\n\nSelect an action to manage users:"
            
            try:
                query.edit_message_text(
                    simple_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                # If editing fails, send a new message
                logging.error(f"Error editing message: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text=simple_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif query.data == "admin_users":
            # Get all users from database
            try:
                users = database.get_all_users()
                
                if not users:
                    query.edit_message_text(
                        "❌ No users registered yet.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Create a simple text representation without Markdown
                user_texts = ["👥 Registered Users:\n"]
                
                for user in users:
                    try:
                        admin_status = "👑 Admin" if user.get("is_admin", False) else "👤 Worker"
                        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                        username = f"@{user.get('username', '')}" if user.get("username") else "No username"
                        
                        user_texts.append(
                            f"ID: {user.get('user_id', 'Unknown')}\n"
                            f"Name: {name}\n"
                            f"Username: {username}\n"
                            f"Role: {admin_status}\n"
                        )
                    except Exception as user_error:
                        logging.error(f"Error formatting user: {user_error}")
                        continue
                
                # Send in chunks to avoid message too long error
                full_message = "\n-------------\n".join(user_texts)
                max_length = 4000
                
                if len(full_message) <= max_length:
                    query.edit_message_text(
                        full_message,
                        reply_markup=get_admin_menu_keyboard()
                    )
                else:
                    # Just show first few users with a note
                    query.edit_message_text(
                        "\n-------------\n".join(user_texts[:5]) + "\n\n(Only showing first 5 users due to length limits)",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error displaying users: {e}")
                query.edit_message_text(
                    "❌ Error retrieving user list. Please try again.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        elif query.data == "admin_attendance":
            # Get attendance records for today
            try:
                attendance = database.get_today_attendance()
                
                if not attendance:
                    query.edit_message_text(
                        "❌ No attendance records for today.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Create a simple text representation without Markdown
                attendance_texts = ["📊 Today's Attendance:\n"]
                
                # Sort records if possible
                try:
                    attendance.sort(key=lambda x: x.get("check_in", datetime.datetime.max))
                except Exception:
                    # Skip sorting if it fails
                    pass
                
                for record in attendance:
                    try:
                        # Get user info
                        user_id = record.get("user_id")
                        user = database.get_user(user_id)
                        name = f"{user.get('first_name', '')} {user.get('last_name', '')}" if user else f"User {user_id}"
                        name = name.strip()
                        
                        # Check for multiple check-ins
                        multiple_sessions = False
                        check_ins = record.get("check_ins", [])
                        if len(check_ins) > 1:
                            multiple_sessions = True
                        
                        # Get time info with safe string conversion
                        check_in = record.get("check_in", "N/A")
                        check_in_str = "N/A"
                        if check_in != "N/A" and check_in is not None:
                            try:
                                check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                            except:
                                check_in_str = str(check_in)
                        
                        # Get first check-in time for multiple sessions
                        first_check_in = record.get("first_check_in", check_in)
                        first_check_in_str = "N/A"
                        if first_check_in != "N/A" and first_check_in is not None:
                            try:
                                first_check_in_str = first_check_in.strftime("%H:%M:%S") if hasattr(first_check_in, "strftime") else str(first_check_in)
                            except:
                                first_check_in_str = str(first_check_in)
                        
                        check_out = record.get("check_out", "N/A")
                        check_out_str = "N/A"
                        if check_out != "N/A" and check_out is not None:
                            try:
                                check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                                status = "✅ Complete"
                            except:
                                check_out_str = str(check_out)
                                status = "⚠️ Error"
                        else:
                            status = "⏳ In Progress"
                        
                        duration = record.get("duration", "N/A")
                        
                        entry = f"👤 {name}\n"
                        entry += f"Status: {status}\n"
                        
                        if multiple_sessions:
                            entry += f"First Check-in: {first_check_in_str}\n"
                            entry += f"Last Check-out: {check_out_str}\n"
                            entry += f"⏱️ Total Duration: {duration} hours\n"
                            entry += f"(Multiple check-ins/outs today)\n"
                        else:
                            entry += f"✅ Check-in: {check_in_str}\n"
                            entry += f"🚪 Check-out: {check_out_str}\n"
                            entry += f"⏱️ Duration: {duration} hours\n"
                        
                        attendance_texts.append(entry)
                    except Exception as record_error:
                        logging.error(f"Error formatting attendance record: {record_error}")
                        continue
                
                # Send in chunks to avoid message too long error
                full_message = "\n-------------\n".join(attendance_texts)
                max_length = 4000
                
                if len(full_message) <= max_length:
                    query.edit_message_text(
                        full_message,
                        reply_markup=get_admin_menu_keyboard()
                    )
                else:
                    # Just show first few records with a note
                    query.edit_message_text(
                        "\n-------------\n".join(attendance_texts[:5]) + "\n\n(Only showing first 5 records due to length limits)",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error displaying attendance: {e}")
                query.edit_message_text(
                    "❌ Error retrieving attendance data. Please try again.",
                    reply_markup=get_admin_menu_keyboard()
                )
                
        elif query.data == "admin_report":
            # Show report options
            try:
                query.edit_message_text(
                    "📝 Generate Attendance Report\n\n"
                    "Please select a date range:",
                    reply_markup=create_date_range_keyboard()
                )
            except Exception as e:
                logging.error(f"Error showing report options: {e}")
                # If editing fails, send a new message
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📝 Generate Attendance Report\n\n"
                         "Please select a date range:",
                    reply_markup=create_date_range_keyboard()
                )
        
        elif query.data == "admin_dashboard":
            # Show dashboard options
            query.edit_message_text(
                "📈 Attendance Dashboard\n\n"
                "Please select a time period:",
                reply_markup=create_dashboard_options_keyboard()
            )
            
        elif query.data.startswith("report_range_"):
            # Handle report date range selection
            try:
                parts = query.data.split("_")
                if len(parts) >= 3:
                    start_date_str = parts[2]
                    end_date_str = parts[3] if len(parts) > 3 else None
                else:
                    # Default to last 7 days if parsing fails
                    end_date = datetime.datetime.utcnow()
                    start_date = end_date - datetime.timedelta(days=6)
                    start_date_str = start_date.strftime("%Y-%m-%d")
                    end_date_str = end_date.strftime("%Y-%m-%d")
                
                # Update message to show loading
                try:
                    query.edit_message_text(
                        "📝 Generating report...\n\n"
                        "This may take a moment.",
                        reply_markup=None
                    )
                except Exception as edit_error:
                    logging.error(f"Error updating message: {edit_error}")
                
                # Generate report
                try:
                    # Safe parsing of dates
                    if start_date_str and end_date_str:
                        try:
                            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        except (ValueError, TypeError, AttributeError):
                            # Default to 7 days ago if parsing fails
                            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=6)
                            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                            
                        try:
                            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        except (ValueError, TypeError, AttributeError):
                            # Default to today if parsing fails
                            end_date = datetime.datetime.utcnow()
                            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    else:
                        # Default to last 7 days
                        end_date = datetime.datetime.utcnow()
                        end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        start_date = end_date - datetime.timedelta(days=6)
                    
                    csv_data, message = generate_attendance_report(start_date, end_date)
                    
                    if csv_data:
                        # Format dates for filenames and messages
                        try:
                            start_date_fmt = start_date.strftime('%Y-%m-%d')
                            end_date_fmt = end_date.strftime('%Y-%m-%d')
                        except AttributeError:
                            # Fallback if date is None or not a datetime
                            start_date_fmt = start_date_str or "unknown"
                            end_date_fmt = end_date_str or "unknown"
                            
                        date_range = f"{start_date_fmt}_{end_date_fmt}"
                        filename = f"attendance_report_{date_range}.csv"
                        
                        context.bot.send_document(
                            chat_id=query.message.chat_id,
                            document=csv_data.encode(),
                            filename=filename,
                            caption=f"📝 Attendance report for {start_date_fmt} to {end_date_fmt}"
                        )
                        
                        # Update original message
                        try:
                            query.message.edit_text(
                                "📝 Report Generated Successfully",
                                reply_markup=get_admin_menu_keyboard()
                            )
                        except Exception as edit_error:
                            logging.error(f"Error updating message: {edit_error}")
                    else:
                        query.edit_message_text(
                            f"❌ {message}",
                            reply_markup=get_admin_menu_keyboard()
                        )
                except Exception as report_error:
                    logging.error(f"Error generating report: {report_error}")
                    query.edit_message_text(
                        "❌ Error Generating Report\n\n"
                        "There was a problem generating the report. Please try again later.",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error in report callback: {e}")
                try:
                    query.edit_message_text(
                        "❌ Error\n\n"
                        "There was a problem processing your request. Please try again.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                except Exception:
                    # Send a new message if editing fails
                    context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="❌ Error\n\n"
                             "There was a problem processing your request. Please try again.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    
        elif query.data == "report_custom":
            # Handle custom report range request
            try:
                keyboard = [
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_report")]
                ]
                
                query.edit_message_text(
                    "📝 Custom Date Range Report\n\n"
                    "Please use the /report command with two dates in YYYY-MM-DD format:\n\n"
                    "/report 2023-01-01 2023-01-31\n\n"
                    "This will generate a report for the specified date range.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logging.error(f"Error handling custom report request: {e}")
                query.edit_message_text(
                    "❌ Error\n\n"
                    "There was a problem processing your request. Please try again.",
                    reply_markup=get_admin_menu_keyboard()
                )
                
        elif query.data.startswith("dashboard_"):
            # Handle dashboard time period selection
            try:
                # Get days parameter from callback data
                try:
                    days_str = query.data.split("_")[1]
                    days = int(days_str) if days_str.isdigit() else 7
                    # Limit to reasonable values
                    days = max(1, min(days, 30))
                except (IndexError, ValueError):
                    days = 7  # Default to 7 days if parsing fails
                
                # Update message to show loading
                try:
                    query.edit_message_text(
                        "📈 Generating dashboard...\n\n"
                        "This may take a moment.",
                        reply_markup=None
                    )
                except Exception as edit_error:
                    logging.error(f"Error updating message: {edit_error}")
                
                # Generate dashboard
                try:
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
                        try:
                            query.message.edit_text(
                                "📈 Dashboard Generated Successfully",
                                reply_markup=get_admin_menu_keyboard()
                            )
                        except Exception as edit_error:
                            logging.error(f"Error updating message: {edit_error}")
                    else:
                        query.edit_message_text(
                            f"❌ {message}",
                            reply_markup=get_admin_menu_keyboard()
                        )
                except Exception as dashboard_error:
                    logging.error(f"Error generating dashboard: {dashboard_error}")
                    query.edit_message_text(
                        "❌ Error Generating Dashboard\n\n"
                        "There was a problem generating the dashboard. Please try again later.",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error in dashboard callback: {e}")
                try:
                    query.edit_message_text(
                        "❌ Error\n\n"
                        "There was a problem processing your request. Please try again.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                except Exception:
                    # Send a new message if editing fails
                    context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="❌ Error\n\n"
                             "There was a problem processing your request. Please try again.",
                        reply_markup=get_admin_menu_keyboard()
                    )
        
        # ============================================================================
        # COMMAND PROMPT HANDLERS
        # ============================================================================
                
        elif query.data == "prompt_delete_user":
            # Show a prompt to enter user ID
            try:
                query.edit_message_text(
                    "🗑️ Delete User\n\n"
                    "Please use the command:\n"
                    "/deleteuser USER_ID\n\n"
                    "Replace USER_ID with the ID of the user you want to delete.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
            except Exception as e:
                # If editing fails, send a new message
                logging.error(f"Error editing message: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text="🗑️ Delete User\n\n"
                         "Please use the command:\n"
                         "/deleteuser USER_ID\n\n"
                         "Replace USER_ID with the ID of the user you want to delete.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
        
        elif query.data == "prompt_clear_attendance":
            # Show a prompt to enter user ID
            try:
                query.edit_message_text(
                    "🧹 Clear Attendance\n\n"
                    "Please use the command:\n"
                    "/clearattendance USER_ID\n\n"
                    "Replace USER_ID with the ID of the user whose attendance records you want to clear.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
            except Exception as e:
                # If editing fails, send a new message
                logging.error(f"Error editing message: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text="🧹 Clear Attendance\n\n"
                         "Please use the command:\n"
                         "/clearattendance USER_ID\n\n"
                         "Replace USER_ID with the ID of the user whose attendance records you want to clear.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
        
        elif query.data == "prompt_user_details":
            # Show a prompt to enter user ID
            try:
                query.edit_message_text(
                    "👤 User Details\n\n"
                    "Please use the command:\n"
                    "/userdetails USER_ID\n\n"
                    "Replace USER_ID with the ID of the user whose details you want to view.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
            except Exception as e:
                # If editing fails, send a new message
                logging.error(f"Error editing message: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text="👤 User Details\n\n"
                         "Please use the command:\n"
                         "/userdetails USER_ID\n\n"
                         "Replace USER_ID with the ID of the user whose details you want to view.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
        
        elif query.data == "prompt_delete_attendance":
            # Show a prompt to enter user ID
            try:
                query.edit_message_text(
                    "📅 Delete Attendance\n\n"
                    "Please use the command:\n"
                    "/deleteattendance USER_ID YYYY-MM-DD\n\n"
                    "Replace USER_ID with the ID of the user whose attendance record you want to delete.\n"
                    "Replace YYYY-MM-DD with the date of the attendance record you want to delete.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
            except Exception as e:
                # If editing fails, send a new message
                logging.error(f"Error editing message: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text="📅 Delete Attendance\n\n"
                         "Please use the command:\n"
                         "/deleteattendance USER_ID YYYY-MM-DD\n\n"
                         "Replace USER_ID with the ID of the user whose attendance record you want to delete.\n"
                         "Replace YYYY-MM-DD with the date of the attendance record you want to delete.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")]])
                )
        
        # ============================================================================
        # USER DELETION HANDLERS
        # ============================================================================
        
        if query.data.startswith("delete_user_"):
            # Direct button for deleting a specific user
            try:
                # Extract user ID from callback data
                parts = query.data.split("_")
                if len(parts) >= 3:
                    target_user_id = int(parts[2])
                else:
                    query.edit_message_text(
                        "❌ Error: Invalid user ID.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user and check if they exist
                user = database.get_user(target_user_id)
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user's name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Create confirmation keyboard
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_user_{target_user_id}")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
                ]
                
                query.edit_message_text(
                    f"⚠️ Delete User Confirmation\n\n"
                    f"Are you sure you want to delete the user {name} (ID: {target_user_id})?\n\n"
                    f"This will permanently delete the user and all their attendance records.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logging.error(f"Error preparing delete user confirmation: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to prepare confirmation.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        elif query.data.startswith("confirm_delete_user_"):
            # Confirm delete user action
            try:
                # Extract user ID from callback data
                target_user_id = int(query.data.split("_")[3])
                
                # Delete the user
                success, message = database.delete_user(target_user_id)
                
                if success:
                    query.edit_message_text(
                        f"✅ Success: {message}",
                        reply_markup=get_admin_menu_keyboard()
                    )
                else:
                    query.edit_message_text(
                        f"❌ Error: {message}",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error in confirm_delete_user callback: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to delete user.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        # ============================================================================
        # ATTENDANCE CLEARING HANDLERS
        # ============================================================================
        
        elif query.data.startswith("clear_attendance_"):
            # Direct button for clearing all attendance for a specific user
            try:
                # Extract user ID from callback data
                parts = query.data.split("_")
                if len(parts) >= 3:
                    target_user_id = int(parts[2])
                else:
                    query.edit_message_text(
                        "❌ Error: Invalid user ID.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user and check if they exist
                user = database.get_user(target_user_id)
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user's name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Show recent attendance records
                history = database.get_user_history(target_user_id, limit=5)
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
                
                # Create confirmation keyboard
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Clear All", callback_data=f"confirm_clear_attendance_{target_user_id}")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
                ]
                
                query.edit_message_text(
                    f"⚠️ Clear Attendance Confirmation\n\n"
                    f"Are you sure you want to clear all attendance records for {name} (ID: {target_user_id})?\n\n"
                    f"This will permanently delete all attendance history for this user.{history_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logging.error(f"Error preparing clear attendance confirmation: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to prepare confirmation.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        elif query.data.startswith("confirm_clear_attendance_"):
            # Confirm clear attendance action
            try:
                # Extract user ID from callback data
                target_user_id = int(query.data.split("_")[3])
                user = database.get_user(target_user_id)
                
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get user name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Clear attendance records
                success, message = database.clear_user_attendance(target_user_id)
                
                if success:
                    query.edit_message_text(
                        f"✅ Success: {message} for user {name}",
                        reply_markup=get_admin_menu_keyboard()
                    )
                else:
                    query.edit_message_text(
                        f"❌ Error: {message}",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error in confirm_clear_attendance callback: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to clear attendance records.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        # ============================================================================
        # SPECIFIC DATE ATTENDANCE DELETION HANDLERS
        # ============================================================================
        
        elif query.data.startswith("delete_specific_date_"):
            # Direct button for deleting attendance on a specific date
            try:
                # Extract user ID from callback data
                parts = query.data.split("_")
                if len(parts) >= 4:
                    target_user_id = int(parts[3])
                else:
                    query.edit_message_text(
                        "❌ Error: Invalid user ID.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user and check if they exist
                user = database.get_user(target_user_id)
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user's name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Show recent attendance records to help admin choose a date
                history = database.get_user_history(target_user_id, limit=10)
                history_text = ""
                
                if history:
                    history_text = "\nRecent attendance records:\n"
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
                            
                            # Generate a quick delete button for this date
                            history_text += f"{date_str}: {check_in_str} → {check_out_str}\n"
                        except Exception:
                            continue
                    
                    # Create a keyboard with direct date options
                    keyboard = []
                    date_buttons = []
                    
                    # Add up to 5 most recent dates as buttons
                    for i, record in enumerate(history[:5]):
                        try:
                            date_str = record.get("date").strftime("%Y-%m-%d")
                            date_buttons.append(
                                InlineKeyboardButton(date_str, callback_data=f"prepare_delete_record_{target_user_id}_{date_str}")
                            )
                            
                            # Add 2 buttons per row
                            if len(date_buttons) == 2 or i == len(history[:5]) - 1:
                                keyboard.append(date_buttons)
                                date_buttons = []
                        except Exception:
                            continue
                    
                    # Add back button
                    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_user_management")])
                    
                    query.edit_message_text(
                        f"📅 Delete Attendance Record\n\n"
                        f"Select a date to delete attendance record for {name} (ID: {target_user_id}):\n"
                        f"{history_text}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    query.edit_message_text(
                        f"❌ No attendance records found for {name}.",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error preparing date selection: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to prepare date selection.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        elif query.data.startswith("prepare_delete_record_"):
            # Handler for when a specific date is selected for deletion
            try:
                # Extract user ID and date from callback data
                parts = query.data.split("_")
                target_user_id = int(parts[3])
                date_str = parts[4]
                
                # Format the date string as a date object
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Get the user
                user = database.get_user(target_user_id)
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user's name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Get record details for the date
                record, message = database.get_user_history_by_date(target_user_id, date_obj)
                
                if not record:
                    query.edit_message_text(
                        f"❌ No attendance record found for {name} on {date_str}.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Format the record details
                check_in = record.get("check_in", "N/A")
                check_out = record.get("check_out", "N/A")
                
                check_in_str = "N/A"
                if check_in != "N/A" and check_in is not None:
                    check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
                
                check_out_str = "N/A"
                if check_out != "N/A" and check_out is not None:
                    check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
                
                record_details = f"Date: {date_str}\nCheck-in: {check_in_str}\nCheck-out: {check_out_str}"
                
                # Create keyboard for confirmation
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_record_{target_user_id}_{date_str}")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
                ]
                
                query.edit_message_text(
                    f"⚠️ Delete Attendance Record Confirmation\n\n"
                    f"Are you sure you want to delete the following attendance record for {name}?\n\n"
                    f"{record_details}\n\n"
                    f"This action cannot be undone.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logging.error(f"Error preparing record deletion: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to prepare record deletion.",
                    reply_markup=get_admin_menu_keyboard()
                )
        
        elif query.data.startswith("confirm_delete_record_"):
            # Confirmation for deleting a specific attendance record
            try:
                # Extract user ID and date from callback data
                parts = query.data.split("_")
                target_user_id = int(parts[3])
                date_str = parts[4]
                
                # Format the date string as a date object
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Get the user
                user = database.get_user(target_user_id)
                if not user:
                    query.edit_message_text(
                        "❌ Error: User not found.",
                        reply_markup=get_admin_menu_keyboard()
                    )
                    return
                
                # Get the user's name safely
                name = user.get('first_name', '')
                if user.get('last_name'):
                    name += f" {user.get('last_name')}"
                
                # Delete the attendance record
                success, message = database.delete_attendance_record(target_user_id, date_obj)
                
                if success:
                    query.edit_message_text(
                        f"✅ Success: {message}",
                        reply_markup=get_admin_menu_keyboard()
                    )
                else:
                    query.edit_message_text(
                        f"❌ Error: {message}",
                        reply_markup=get_admin_menu_keyboard()
                    )
            except Exception as e:
                logging.error(f"Error deleting attendance record: {e}")
                query.edit_message_text(
                    "❌ Error: Failed to delete attendance record.",
                    reply_markup=get_admin_menu_keyboard()
                )
    
    except Exception as e:
        logging.error(f"Error in admin callback: {e}")
        try:
            # Send a fallback message if anything goes wrong
            context.bot.send_message(
                chat_id=user_id,
                text="Sorry, an error occurred. Please try again.",
                reply_markup=get_admin_menu_keyboard()
            )
        except:
            pass

@admin_required
def delete_user_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /deleteuser command."""
    args = context.args
    
    if not args or len(args) == 0:
        update.message.reply_text(
            "❌ Error: You must provide a user ID.\n\n"
            "Usage: /deleteuser USER_ID",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Try to get the user ID from the arguments
    try:
        user_id = int(args[0])
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    
    # Confirm operation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_user_{user_id}"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")
        ]
    ]
    
    update.message.reply_text(
        f"⚠️ Delete User Confirmation\n\n"
        f"Are you sure you want to delete the user {name} (ID: {user_id})?\n\n"
        f"This will permanently delete the user and all their attendance records.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_required
def delete_record_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /deleterecord command."""
    args = context.args
    
    if not args or len(args) < 2:
        update.message.reply_text(
            "❌ *Error*: You must provide a user ID and date.\n\n"
            "Usage: `/deleterecord USER_ID YYYY-MM-DD`",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Try to get the user ID and date from the arguments
    try:
        user_id = int(args[0])
        date = args[1]
    except ValueError:
        update.message.reply_text(
            "❌ *Error*: User ID must be a number.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ *Error*: User not found.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Delete the attendance record
    success, message = database.delete_attendance_record(user_id, date)
    
    if success:
        update.message.reply_text(
            f"✅ *Success*: {message} for user {user['first_name']} on {date}",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text(
            f"❌ *Error*: {message}",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

@admin_required
def clear_attendance_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /clearattendance command."""
    args = context.args
    
    if not args or len(args) == 0:
        update.message.reply_text(
            "❌ Error: You must provide a user ID.\n\n"
            "Usage: /clearattendance USER_ID",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Try to get the user ID from the arguments
    try:
        user_id = int(args[0])
    except ValueError:
        update.message.reply_text(
            "❌ Error: User ID must be a number.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
        
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    
    # Confirm operation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Clear All", callback_data=f"confirm_clear_attendance_{user_id}"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")
        ]
    ]
    
    update.message.reply_text(
        f"⚠️ Clear Attendance Confirmation\n\n"
        f"Are you sure you want to clear all attendance records for {name} (ID: {user_id})?\n\n"
        f"This will permanently delete all attendance history for this user.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_required
def user_details_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /userdetails command."""
    args = context.args
    
    if not args or len(args) == 0:
        update.message.reply_text(
            "❌ *Error*: You must provide a user ID.\n\n"
            "Usage: `/userdetails USER_ID`",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Try to get the user ID from the arguments
    try:
        user_id = int(args[0])
    except ValueError:
        update.message.reply_text(
            "❌ *Error*: User ID must be a number.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get the user
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ *Error*: User not found.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get the user's recent attendance history
    history = database.get_user_history(user_id, limit=5)
    
    # Create user details message
    message = f"👤 *User Details*\n\n"
    message += f"*ID:* `{user['user_id']}`\n"
    
    # Escape Markdown characters in names
    first_name = user['first_name'].replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
    last_name = user.get('last_name', '').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
    name = f"{first_name} {last_name}".strip()
    
    message += f"*Name:* {name}\n"
    message += f"*Username:* {f'@{user['username']}' if user.get('username') else 'None'}\n"
    message += f"*Role:* {'Admin' if user.get('is_admin', False) else 'Worker'}\n"
    
    # Safe handling of dates
    registration_date = user.get('created_at')
    if registration_date:
        try:
            date_str = registration_date.strftime('%Y-%m-%d %H:%M:%S')
        except AttributeError:
            date_str = str(registration_date)
    else:
        date_str = 'Unknown'
    
    message += f"*Registered:* {date_str}\n\n"
    
    # Add recent attendance
    if history:
        message += "*Recent Attendance:*\n"
        for record in history:
            try:
                date_str = record["date"].strftime("%Y-%m-%d")
            except Exception:
                date_str = str(record.get("date", "Unknown date"))
            
            check_in = record.get("check_in", "N/A")
            check_out = record.get("check_out", "N/A")
            duration = record.get("duration", "N/A")
            
            check_in_str = "N/A"
            if check_in != "N/A" and check_in is not None:
                try:
                    check_in_str = check_in.strftime("%H:%M:%S")
                except Exception:
                    check_in_str = str(check_in)
            
            check_out_str = "N/A"
            if check_out != "N/A" and check_out is not None:
                try:
                    check_out_str = check_out.strftime("%H:%M:%S")
                except Exception:
                    check_out_str = str(check_out)
            
            message += f"• *{date_str}*: {check_in_str} → {check_out_str} ({duration} hours)\n"
    else:
        message += "*No attendance records found.*\n"
    
    # Add action buttons
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
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

@admin_required
def delete_attendance_command(update: Update, context: CallbackContext) -> None:
    """Handler for the /deleteattendance command."""
    args = context.args
    
    if not args or len(args) < 2:
        update.message.reply_text(
            "❌ Error: You must provide a user ID and date.\n\n"
            "Usage: /deleteattendance USER_ID YYYY-MM-DD",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Try to get the user ID and date from the arguments
    try:
        user_id = int(args[0])
        date_str = args[1]
        
        # Format the date string as a date object
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        update.message.reply_text(
            "❌ Error: Invalid format. User ID must be a number and date must be in YYYY-MM-DD format.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Check if the user exists
    user = database.get_user(user_id)
    if not user:
        update.message.reply_text(
            "❌ Error: User not found.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Get the user's name safely
    name = user.get('first_name', '')
    if user.get('last_name'):
        name += f" {user.get('last_name')}"
    
    # Check if there's a record for this date
    record, message = database.get_user_history_by_date(user_id, date_obj)
    
    if not record:
        update.message.reply_text(
            f"❌ No attendance record found for {name} on {date_str}.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Format the record details
    check_in = record.get("check_in", "N/A")
    check_out = record.get("check_out", "N/A")
    
    check_in_str = "N/A"
    if check_in != "N/A" and check_in is not None:
        check_in_str = check_in.strftime("%H:%M:%S") if hasattr(check_in, "strftime") else str(check_in)
    
    check_out_str = "N/A"
    if check_out != "N/A" and check_out is not None:
        check_out_str = check_out.strftime("%H:%M:%S") if hasattr(check_out, "strftime") else str(check_out)
    
    record_details = f"Date: {date_str}\nCheck-in: {check_in_str}\nCheck-out: {check_out_str}"
    
    # Create keyboard for confirmation
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_record_{user_id}_{date_str}")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="admin_user_management")]
    ]
    
    update.message.reply_text(
        f"⚠️ Delete Attendance Record Confirmation\n\n"
        f"Are you sure you want to delete the following attendance record for {name}?\n\n"
        f"{record_details}\n\n"
        f"This action cannot be undone.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    ) 