# reminders.py
import logging
import datetime
import threading
import time
import pytz
from telegram import ParseMode
import database
import config

class ReminderScheduler:
    """Scheduler for sending reminders to users."""
    
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.thread = None
        self.morning_shift_end = datetime.time(20, 0)  # 8:00 PM
        self.evening_shift_end = datetime.time(23, 0)  # 11:00 PM
        self.night_shift_end = datetime.time(3, 0)     # 3:00 AM next day
        
        # Get timezone
        self.timezone = pytz.timezone(config.TIMEZONE)
        
        logging.info(f"Reminder scheduler initialized with timezone: {config.TIMEZONE}")
    
    def start(self):
        """Start the reminder scheduler."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logging.info("Reminder scheduler started")
    
    def stop(self):
        """Stop the reminder scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logging.info("Reminder scheduler stopped")
    
    def _run(self):
        """Main loop for the reminder scheduler."""
        while self.running:
            try:
                self._check_for_reminders()
            except Exception as e:
                logging.error(f"Error in reminder scheduler: {e}")
            
            # Sleep for 15 minutes before checking again
            time.sleep(15 * 60)
    
    def _check_for_reminders(self):
        """Check for users who need reminders."""
        now = datetime.datetime.now(self.timezone)
        current_time = now.time()
        
        # Determine which shift is ending now
        shift_ending = None
        if (
            (current_time.hour == self.morning_shift_end.hour and current_time.minute >= self.morning_shift_end.minute) or
            (current_time.hour == self.morning_shift_end.hour + 1 and current_time.minute < 15)
        ):
            shift_ending = "morning"
        elif (
            (current_time.hour == self.evening_shift_end.hour and current_time.minute >= self.evening_shift_end.minute) or
            (current_time.hour == self.evening_shift_end.hour + 1 and current_time.minute < 15)
        ):
            shift_ending = "evening"
        elif (
            (current_time.hour == self.night_shift_end.hour and current_time.minute >= self.night_shift_end.minute) or
            (current_time.hour == self.night_shift_end.hour + 1 and current_time.minute < 15)
        ):
            shift_ending = "night"
        
        if not shift_ending:
            return
        
        # Get all users who are currently checked in but not checked out
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        attendance = database.get_today_attendance()
        
        pending_checkouts = []
        for record in attendance:
            if "check_in" in record and ("check_out" not in record or record["check_out"] is None):
                user_id = record["user_id"]
                user = database.get_user(user_id)
                
                if user:
                    pending_checkouts.append({
                        "user_id": user_id,
                        "name": f"{user['first_name']} {user.get('last_name', '')}".strip(),
                        "check_in_time": record["check_in"]
                    })
        
        # Send reminders
        shift_names = {
            "morning": "morning shift (8:00 PM)",
            "evening": "evening shift (11:00 PM)",
            "night": "night shift (3:00 AM)"
        }
        
        for user in pending_checkouts:
            try:
                self.bot.send_message(
                    chat_id=user["user_id"],
                    text=(
                        f"⏰ *Checkout Reminder*\n\n"
                        f"Hi {user['name']}, it looks like you're still checked in from {user['check_in_time'].strftime('%H:%M:%S')}.\n\n"
                        f"The {shift_names[shift_ending]} is ending. If you're done with your shift, please don't forget to check out."
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=database.get_user_menu_keyboard(False)
                )
                logging.info(f"Sent checkout reminder to user {user['user_id']} ({user['name']})")
            except Exception as e:
                logging.error(f"Failed to send reminder to user {user['user_id']}: {e}")
        
        # Also inform admins about users who haven't checked out
        if pending_checkouts:
            admin_users = database.get_admin_users()
            
            admin_message = (
                f"⚠️ *Checkout Alert*\n\n"
                f"The {shift_names[shift_ending]} has ended, but the following users have not checked out:\n\n"
            )
            
            for user in pending_checkouts:
                admin_message += f"• {user['name']} (checked in at {user['check_in_time'].strftime('%H:%M:%S')})\n"
            
            for admin in admin_users:
                try:
                    self.bot.send_message(
                        chat_id=admin["user_id"],
                        text=admin_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logging.info(f"Sent checkout alert to admin {admin['user_id']}")
                except Exception as e:
                    logging.error(f"Failed to send alert to admin {admin['user_id']}: {e}")

def setup_reminders(bot):
    """Set up the reminder scheduler."""
    scheduler = ReminderScheduler(bot)
    scheduler.start()
    return scheduler 