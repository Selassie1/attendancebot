# utils/time_utils.py
import datetime
import pytz
import config

def get_current_time():
    """Get current time in the configured timezone."""
    utc_now = datetime.datetime.utcnow()
    if config.TIMEZONE == "UTC":
        return utc_now
    
    try:
        timezone = pytz.timezone(config.TIMEZONE)
        return pytz.utc.localize(utc_now).astimezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        # Fallback to UTC if timezone is invalid
        return utc_now

def format_datetime(dt, format_str="%Y-%m-%d %H:%M:%S"):
    """Format datetime object to string."""
    if dt is None:
        return "N/A"
    
    return dt.strftime(format_str)

def parse_date(date_str, format_str="%Y-%m-%d"):
    """Parse date string to datetime object."""
    try:
        return datetime.datetime.strptime(date_str, format_str)
    except ValueError:
        raise ValueError(f"Invalid date format. Expected {format_str}")

def get_date_range(days=7):
    """Get date range for the last N days."""
    end_date = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - datetime.timedelta(days=days-1)
    return start_date, end_date 