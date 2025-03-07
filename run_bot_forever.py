#!/usr/bin/env python3
# run_bot_forever.py

import subprocess
import time
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser('~/bot_monitor.log'))
    ]
)
logger = logging.getLogger(__name__)

def run_bot():
    """Run the bot and restart it if it crashes."""
    consecutive_failures = 0
    max_consecutive_failures = 5
    wait_time = 10  # seconds
    
    while True:
        try:
            logger.info("Starting the bot...")
            # Run the bot process
            process = subprocess.Popen(["python", "bot.py"], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.STDOUT)
            
            # Reset failure counter on successful startup
            consecutive_failures = 0
            
            # Wait for process to complete (or crash)
            stdout, _ = process.communicate()
            exit_code = process.returncode
            
            # If we get here, the bot exited
            logger.warning(f"Bot exited with code {exit_code}")
            if stdout:
                logger.info(f"Output: {stdout.decode('utf-8', errors='replace')}")
            
            # Prevent rapid restarts - wait a bit
            time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            consecutive_failures += 1
            
            # If we have too many consecutive failures, wait longer before retrying
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"Too many consecutive failures ({consecutive_failures}). Waiting longer...")
                time.sleep(wait_time * 6)  # Wait 1 minute
            else:
                time.sleep(wait_time)

if __name__ == "__main__":
    logger.info("Bot monitor started")
    run_bot()