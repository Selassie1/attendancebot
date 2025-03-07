# init_db.py
import logging
import config
import database

def init_admin():
    """Initialize admin user in the database."""
    if not config.ADMIN_USER_ID:
        logging.warning("ADMIN_USER_ID not set in .env file. Skipping admin initialization.")
        return False
    
    try:
        # Register admin user
        admin_id = config.ADMIN_USER_ID
        success = database.register_user(
            user_id=admin_id,
            first_name="Admin",
            last_name=None,
            username=None,
            is_admin=True
        )
        
        if success:
            logging.info(f"Admin user initialized with ID: {admin_id}")
            return True
        else:
            logging.error("Failed to initialize admin user")
            return False
    except Exception as e:
        logging.error(f"Error initializing admin user: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    
    print("Initializing database...")
    init_admin()
    print("Done.") 