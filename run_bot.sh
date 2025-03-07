#!/bin/bash
# run_bot.sh

# Activate virtual environment
source ~/telegramattendancebot/venv/bin/activate

# Navigate to project directory
cd ~/telegramattendancebot

# Run the bot with the wrapper script for auto-restart
python run_bot_forever.py 