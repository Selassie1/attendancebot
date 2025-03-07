# DEPLOYMENT_GUIDE.md

# Deploying Telegram Attendance Bot to PythonAnywhere

This guide will walk you through deploying the Telegram Attendance Bot to PythonAnywhere, ensuring it stays running continuously.

## 1. Create a PythonAnywhere Account

1. Go to [PythonAnywhere](https://www.pythonanywhere.com/registration/register/beginner/) and sign up for an account
2. The free tier has limitations, but for a Telegram bot with moderate usage, it should be sufficient
3. Consider upgrading to a paid plan if you need more resources or always-on task hours

## 2. Set Up Your Environment

### Clone Your Repository

1. Log in to PythonAnywhere and open a Bash console
2. Clone your repository:
   ```bash
   cd ~
   git clone https://github.com/yourusername/telegramattendancebot.git
   cd telegramattendancebot
   ```

### Create a Virtual Environment

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Set Up Environment Variables

1. Create an environment file in your home directory:

   ```bash
   nano ~/.env
   ```

2. Add your environment variables (same as in your local .env file):

   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   MONGODB_URI=your_mongodb_uri_here
   ADMIN_USER_ID=your_admin_id_here
   TIMEZONE=UTC
   ```

3. Save and exit (Ctrl+X, then Y, then Enter)

4. Make sure your config.py is set up to read from this location (already updated in this repository)

## 3. Set Up an Always-On Task

To keep your bot running continuously, you'll need to set up a scheduled task:

1. Go to the "Tasks" tab in PythonAnywhere
2. Under "Always-on tasks" (or "Scheduled tasks" on free tier), create a new task
3. Set it to run daily (or more frequently if needed)
4. Enter the command:
   ```
   ~/telegramattendancebot/run_bot.sh
   ```
5. Save the task

### For Free Accounts

Free accounts don't have "Always-on tasks", so you'll need to:

1. Schedule the task to run every 24 hours
2. Set up your wrapper script (run_bot_forever.py) to keep the bot running in between scheduled restarts
3. Consider upgrading to a paid account if you need guaranteed uptime

## 4. Testing Your Deployment

1. Manually run your bot first to test:

   ```bash
   cd ~/telegramattendancebot
   source venv/bin/activate
   python bot.py
   ```

2. If it works, stop the bot (Ctrl+C) and run it through the wrapper:

   ```bash
   python run_bot_forever.py
   ```

3. Send a message to your bot to confirm it's working

## 5. Monitoring and Maintenance

### Check Logs

1. Bot logs: Check the output of your bot process
2. Wrapper logs: Check ~/bot_monitor.log for information about crashes and restarts

### Update Your Bot

When you need to update your bot:

1. SSH into your PythonAnywhere account
2. Navigate to your project directory:
   ```bash
   cd ~/telegramattendancebot
   ```
3. Pull the latest changes:
   ```bash
   git pull
   ```
4. Restart your bot by stopping the current process and letting the task scheduler restart it

## 6. Troubleshooting

### Bot Crashes or Doesn't Respond

1. Check the logs (~/bot_monitor.log)
2. Verify your environment variables are set correctly
3. Check if your MongoDB connection is working
4. Ensure your bot token is valid

### MongoDB Connection Issues

1. Ensure your MongoDB Atlas IP whitelist includes PythonAnywhere's IP addresses
2. Test your connection string manually:
   ```python
   python -c "from pymongo import MongoClient; client = MongoClient('your_uri_here'); print(client.server_info())"
   ```

### Telegram API Rate Limits

If you encounter rate limiting from Telegram:

1. Implement exponential backoff in your bot code
2. Avoid sending too many messages in a short period

## 7. Upgrading to a Paid Plan

If you need more resources or guaranteed uptime:

1. Consider upgrading to a PythonAnywhere paid plan
2. With a paid plan, you get:
   - True "Always-on tasks" that don't require daily restarts
   - More CPU and memory resources
   - Better performance and reliability
