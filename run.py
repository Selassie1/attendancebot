# run.py
import logging
import bot
from init_db import init_admin

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    
    # Initialize admin user
    init_admin()
    
    # Start the bot
    bot.main() 