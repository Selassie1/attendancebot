# config.py
import os
import logging
from dotenv import load_dotenv
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables from .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Also try loading from home directory for PythonAnywhere
home_env_path = os.path.expanduser('~/.env')
if os.path.exists(home_env_path):
    load_dotenv(home_env_path)

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No Telegram bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("No MongoDB URI provided. Set MONGODB_URI environment variable.")

# Extract database name from URI
match = re.search(r'/([^/?]+)(\?|$)', MONGODB_URI)
if match:
    DB_NAME = match.group(1)
else:
    DB_NAME = "attendance_bot"

# Admin user ID
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
if not ADMIN_USER_ID:
    logging.warning("No admin user ID provided. Set ADMIN_USER_ID environment variable.")

# Timezone configuration
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Bot name (optional)
BOT_NAME = os.getenv("BOT_NAME", "Attendance Bot")

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
) 