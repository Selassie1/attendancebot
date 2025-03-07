# telegram_patch.py
import sys
import os
import logging
import importlib.util
import site
import glob

def find_telegram_package():
    """Find the telegram package path."""
    # Try to find the telegram package in site-packages
    site_packages = site.getsitepackages()
    user_site = site.getusersitepackages()
    
    all_paths = site_packages + [user_site]
    
    for path in all_paths:
        telegram_path = os.path.join(path, 'telegram')
        if os.path.exists(telegram_path) and os.path.isdir(telegram_path):
            return telegram_path
        
        # Try to find using glob pattern
        for site_path in glob.glob(os.path.join(path, '**/telegram'), recursive=True):
            if os.path.isdir(site_path):
                return site_path
    
    return None

def patch_telegram_bot():
    """
    Patch the python-telegram-bot library to work with Python 3.13
    which removed the imghdr module.
    """
    try:
        # Find the telegram package
        telegram_path = find_telegram_package()
        
        if not telegram_path:
            logging.error("Could not find telegram package")
            return False
        
        inputfile_path = os.path.join(telegram_path, 'files', 'inputfile.py')
        
        if not os.path.exists(inputfile_path):
            logging.error(f"Could not find {inputfile_path}")
            return False
        
        # Read the file
        with open(inputfile_path, 'r') as f:
            content = f.read()
        
        # Check if the file already contains our patch
        if "# Patched for Python 3.13" in content:
            logging.info("Telegram bot library already patched")
            return True
        
        # Replace the imghdr import with our custom implementation
        patched_content = content.replace(
            "import imghdr",
            """# Patched for Python 3.13
try:
    import imghdr
except ImportError:
    # Simple replacement for imghdr.what() function
    # This is a simplified version that only checks for common image formats
    def what(file, h=None):
        if h is None:
            with open(file, 'rb') as f:
                h = f.read(32)
        
        # Check for PNG
        if h.startswith(b'\\x89PNG\\r\\n\\x1a\\n'):
            return 'png'
        # Check for JPEG
        elif h.startswith(b'\\xff\\xd8'):
            return 'jpeg'
        # Check for GIF
        elif h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
            return 'gif'
        # Check for BMP
        elif h.startswith(b'BM'):
            return 'bmp'
        # Check for WEBP
        elif h.startswith(b'RIFF') and h[8:12] == b'WEBP':
            return 'webp'
        return None
    
    # Create a mock imghdr module
    class ImghdrMock:
        @staticmethod
        def what(file, h=None):
            return what(file, h)
    
    imghdr = ImghdrMock()"""
        )
        
        # Write the patched file
        with open(inputfile_path, 'w') as f:
            f.write(patched_content)
        
        logging.info(f"Successfully patched telegram bot library at {inputfile_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error patching telegram bot library: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = patch_telegram_bot()
    sys.exit(0 if success else 1) 