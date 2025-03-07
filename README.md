# Telegram Attendance Bot

A Telegram bot for tracking employee attendance. Workers can mark attendance (check-in) and close shifts (check-out) directly through Telegram. Managers can view attendance records and access a dashboard with attendance statistics.

## Features

- Check-in and check-out functionality for workers
- Attendance history for individual workers
- Admin dashboard with attendance statistics
- Export attendance data

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   MONGODB_URI=your_mongodb_connection_string
   ADMIN_USER_ID=your_telegram_user_id
   ```
4. Run the bot:
   ```
   python bot.py
   ```

## Usage

### Worker Commands

- `/start` - Start the bot and register
- `/checkin` - Check in for work
- `/checkout` - Check out after work
- `/status` - Check your current status
- `/history` - View your attendance history

### Admin Commands

- `/users` - List all registered users
- `/attendance` - View today's attendance
- `/report` - Generate attendance report
- `/dashboard` - View attendance dashboard

## Technology Stack

- Python
- python-telegram-bot
- MongoDB
- pandas (for data analysis)
- matplotlib (for dashboard visualization)
