# config.py
import os
import logging
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/attendance_bot")
# Extract database name from URI
match = re.search(r'/([^/?]+)(\?|$)', MONGODB_URI)
if match:
    DB_NAME = match.group(1)
else:
    DB_NAME = "attendance_bot"

# Admin configuration
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
if ADMIN_USER_ID:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID)
    except ValueError:
        logging.warning("ADMIN_USER_ID must be an integer. Using None instead.")
        ADMIN_USER_ID = None
else:
    ADMIN_USER_ID = None

# Timezone configuration
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
) 