# database.py
import logging
import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure
import config

# Initialize MongoDB client
try:
    client = MongoClient(config.MONGODB_URI)
    db = client[config.DB_NAME]
    users_collection = db["users"]
    attendance_collection = db["attendance"]
    
    # Create indexes
    users_collection.create_index("user_id", unique=True)
    attendance_collection.create_index([("user_id", 1), ("date", 1)], unique=True)
    attendance_collection.create_index("date")
    
    logging.info("Connected to MongoDB")
except ConnectionFailure:
    logging.error("Failed to connect to MongoDB")
    raise

def register_user(user_id, first_name, last_name=None, username=None, is_admin=False):
    """Register a new user or update existing user."""
    user_data = {
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "is_admin": is_admin,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    }
    
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": user_data},
            upsert=True
        )
        return True
    except Exception as e:
        logging.error(f"Error registering user: {e}")
        return False

def get_user(user_id):
    """Get user by ID."""
    return users_collection.find_one({"user_id": user_id})

def get_all_users():
    """Get all registered users."""
    return list(users_collection.find())

def check_in(user_id, timestamp=None):
    """Record user check-in with support for multiple check-ins per day."""
    return allow_multiple_check_ins(user_id, timestamp)

def check_out(user_id, timestamp=None):
    """Record user check-out."""
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()
    
    today = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        # Check if there's an existing record for today
        existing = attendance_collection.find_one({
            "user_id": user_id,
            "date": today
        })
        
        if not existing or "check_in" not in existing:
            return False, "You need to check in first"
        
        # Calculate duration based on the most recent check-in
        check_in_time = existing["check_in"]
        duration = (timestamp - check_in_time).total_seconds() / 3600  # hours
        
        # Get first check-in time (for reporting)
        first_check_in = existing.get("first_check_in", check_in_time)
        
        # Handle multiple check-ins - calculate total duration for the day
        total_duration = duration
        if "check_ins" in existing and len(existing["check_ins"]) > 0:
            # If we have previous check-ins/check-outs, add those durations
            if "check_outs" in existing and len(existing["check_outs"]) > 0:
                for checkout in existing["check_outs"]:
                    if "duration" in checkout:
                        total_duration += checkout["duration"]
        
        # For multiple sessions, calculate total span from first check-in to last check-out
        has_multiple_sessions = False
        if "check_ins" in existing and len(existing.get("check_ins", [])) > 1:
            has_multiple_sessions = True
            # Calculate total span from first check-in to now
            total_span = (timestamp - first_check_in).total_seconds() / 3600  # hours
        
        # Record this check-out
        check_outs = existing.get("check_outs", [])
        check_outs.append({
            "time": timestamp,
            "duration": round(duration, 2),
            "created_at": timestamp
        })
        
        # Update the record
        attendance_collection.update_one(
            {"user_id": user_id, "date": today},
            {
                "$set": {
                    "check_out": timestamp,
                    "check_outs": check_outs,
                    "duration": round(total_duration, 2),
                    "updated_at": timestamp
                }
            }
        )
        
        # Prepare the success message, including info about first check-in for multiple sessions
        if has_multiple_sessions:
            first_time_str = first_check_in.strftime("%H:%M:%S")
            last_time_str = timestamp.strftime("%H:%M:%S")
            return True, f"Check-out successful. Session duration: {round(duration, 2)} hours. Total today: {round(total_duration, 2)} hours. (First check-in: {first_time_str}, Last check-out: {last_time_str})"
        else:
            return True, f"Check-out successful. Session duration: {round(duration, 2)} hours. Total today: {round(total_duration, 2)} hours"
    except Exception as e:
        logging.error(f"Error checking out: {e}")
        return False, f"Error: {str(e)}"

def get_user_status(user_id):
    """Get user's current status (checked in/out)."""
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    record = attendance_collection.find_one({
        "user_id": user_id,
        "date": today
    })
    
    if not record:
        return "Not checked in today"
    elif "check_in" in record and "check_out" not in record:
        return f"Checked in at {record['check_in'].strftime('%H:%M:%S')}, not checked out yet"
    else:
        return f"Checked in at {record['check_in'].strftime('%H:%M:%S')}, checked out at {record['check_out'].strftime('%H:%M:%S')}, duration: {record['duration']} hours"

def get_user_history(user_id, limit=10):
    """Get user's attendance history."""
    return list(attendance_collection.find(
        {"user_id": user_id}
    ).sort("date", DESCENDING).limit(limit))

def get_today_attendance():
    """Get today's attendance for all users."""
    # Ensure we have a valid datetime object
    try:
        today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    except Exception as e:
        logging.error(f"Error creating today date: {e}")
        # Use a simpler approach as fallback
        today = datetime.datetime.utcnow().date()
    
    # Query the database
    try:
        records = list(attendance_collection.find({"date": today}))
        # Post-process to ensure all date fields are valid
        for record in records:
            # Ensure check_in is valid
            if 'check_in' in record and record['check_in'] is None:
                record['check_in'] = "N/A"
            # Ensure check_out is valid
            if 'check_out' in record and record['check_out'] is None:
                record['check_out'] = "N/A"
        return records
    except Exception as e:
        logging.error(f"Error fetching today's attendance: {e}")
        return []

def get_date_range_attendance(start_date, end_date):
    """Get attendance within a date range."""
    try:
        # Validate date objects
        if not isinstance(start_date, (datetime.datetime, datetime.date)):
            if isinstance(start_date, str):
                try:
                    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                except (ValueError, TypeError, AttributeError):
                    # Default to one week ago if parsing fails
                    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=7)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Default to one week ago
                start_date = datetime.datetime.utcnow() - datetime.timedelta(days=7)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                
        if not isinstance(end_date, (datetime.datetime, datetime.date)):
            if isinstance(end_date, str):
                try:
                    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                except (ValueError, TypeError, AttributeError):
                    # Default to today if parsing fails
                    end_date = datetime.datetime.utcnow()
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                # Default to today
                end_date = datetime.datetime.utcnow()
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Query database
        records = list(attendance_collection.find({
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date", DESCENDING))
        
        # Post-process to ensure all date fields are valid
        for record in records:
            # Ensure check_in is valid
            if 'check_in' in record and record['check_in'] is None:
                record['check_in'] = "N/A"
            # Ensure check_out is valid
            if 'check_out' in record and record['check_out'] is None:
                record['check_out'] = "N/A"
                
        return records
    except Exception as e:
        logging.error(f"Error fetching date range attendance: {e}")
        return []

def get_user_history_by_date(user_id, target_date):
    """Get user's attendance history for a specific date."""
    # Convert string date to datetime if needed
    if isinstance(target_date, str):
        try:
            target_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except ValueError:
            return None, "Invalid date format. Please use YYYY-MM-DD format."
    
    record = attendance_collection.find_one({
        "user_id": user_id,
        "date": target_date
    })
    
    return record, "Success" if record else "No record found for this date"

def get_user_history_date_range(user_id, start_date, end_date):
    """Get user's attendance history within a date range."""
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        try:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except ValueError:
            return None, "Invalid start date format. Please use YYYY-MM-DD format."
    
    if isinstance(end_date, str):
        try:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except ValueError:
            return None, "Invalid end date format. Please use YYYY-MM-DD format."
    
    records = list(attendance_collection.find({
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }).sort("date", DESCENDING))
    
    return records, "Success" if records else "No records found for this date range"

def get_admin_users():
    """Get all admin users for notifications."""
    try:
        admin_users = list(users_collection.find({"is_admin": True}))
        if not admin_users and config.ADMIN_USER_ID:
            # If no admins found but we have an admin ID in config, try to find that user
            admin = users_collection.find_one({"user_id": config.ADMIN_USER_ID})
            if admin:
                admin_users = [admin]
            else:
                # The admin hasn't interacted with the bot yet, create a placeholder
                admin = {
                    "user_id": config.ADMIN_USER_ID,
                    "first_name": "Admin",
                    "is_admin": True
                }
                users_collection.insert_one(admin)
                admin_users = [admin]
        
        logging.info(f"Found {len(admin_users)} admin users")
        return admin_users
    except Exception as e:
        logging.error(f"Error getting admin users: {e}")
        # Fallback to config admin
        if config.ADMIN_USER_ID:
            return [{"user_id": config.ADMIN_USER_ID, "first_name": "Admin", "is_admin": True}]
        return []

def get_user_name(user_id):
    """Get user's full name without 'None' appearing for missing last names."""
    user = get_user(user_id)
    if not user:
        return f"User {user_id}"
    
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    
    if last_name:
        return f"{first_name} {last_name}"
    else:
        return first_name

def get_month_attendance(year, month):
    """Get attendance for a specific month."""
    start_date = datetime.datetime(year, month, 1, 0, 0, 0, 0)
    if month == 12:
        end_date = datetime.datetime(year + 1, 1, 1, 0, 0, 0, 0) - datetime.timedelta(days=1)
    else:
        end_date = datetime.datetime(year, month + 1, 1, 0, 0, 0, 0) - datetime.timedelta(days=1)
    
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return list(attendance_collection.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }).sort("date", DESCENDING))

def delete_user(user_id):
    """Delete a user and all their attendance records."""
    try:
        # Delete user's attendance records
        attendance_result = attendance_collection.delete_many({"user_id": user_id})
        
        # Delete user
        user_result = users_collection.delete_one({"user_id": user_id})
        
        if user_result.deleted_count > 0:
            logging.info(f"Deleted user {user_id} and {attendance_result.deleted_count} attendance records")
            return True, f"User deleted successfully along with {attendance_result.deleted_count} attendance records"
        else:
            logging.warning(f"User {user_id} not found for deletion")
            return False, "User not found"
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        return False, f"Error: {str(e)}"

def delete_attendance_record(user_id, date):
    """Delete a specific attendance record."""
    try:
        # Convert string date to datetime if needed
        if isinstance(date, str):
            try:
                date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            except ValueError:
                return False, "Invalid date format. Please use YYYY-MM-DD format."
        
        result = attendance_collection.delete_one({"user_id": user_id, "date": date})
        
        if result.deleted_count > 0:
            logging.info(f"Deleted attendance record for user {user_id} on {date.strftime('%Y-%m-%d')}")
            return True, "Attendance record deleted successfully"
        else:
            logging.warning(f"Attendance record not found for user {user_id} on {date.strftime('%Y-%m-%d')}")
            return False, "Attendance record not found"
    except Exception as e:
        logging.error(f"Error deleting attendance record: {e}")
        return False, f"Error: {str(e)}"

def update_attendance_record(user_id, date, update_data):
    """Update a specific attendance record."""
    try:
        # Convert string date to datetime if needed
        if isinstance(date, str):
            try:
                date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            except ValueError:
                return False, "Invalid date format. Please use YYYY-MM-DD format."
        
        # Ensure updated_at field is set
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.datetime.utcnow()
        
        result = attendance_collection.update_one(
            {"user_id": user_id, "date": date},
            {"$set": update_data}
        )
        
        if result.matched_count > 0:
            logging.info(f"Updated attendance record for user {user_id} on {date.strftime('%Y-%m-%d')}")
            return True, "Attendance record updated successfully"
        else:
            logging.warning(f"Attendance record not found for user {user_id} on {date.strftime('%Y-%m-%d')}")
            return False, "Attendance record not found"
    except Exception as e:
        logging.error(f"Error updating attendance record: {e}")
        return False, f"Error: {str(e)}"

def clear_user_attendance(user_id):
    """Delete all attendance records for a user."""
    try:
        result = attendance_collection.delete_many({"user_id": user_id})
        
        if result.deleted_count > 0:
            logging.info(f"Deleted {result.deleted_count} attendance records for user {user_id}")
            return True, f"Deleted {result.deleted_count} attendance records"
        else:
            logging.warning(f"No attendance records found for user {user_id}")
            return False, "No attendance records found"
    except Exception as e:
        logging.error(f"Error clearing user attendance: {e}")
        return False, f"Error: {str(e)}"

def allow_multiple_check_ins(user_id, timestamp=None):
    """Add a new check-in entry without overriding previous ones for the same day."""
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()
    
    today = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        # Find existing record for today
        existing = attendance_collection.find_one({
            "user_id": user_id,
            "date": today
        })
        
        if existing:
            # If there's an existing record, update it
            check_ins = existing.get("check_ins", [])
            
            # Add the original check-in if not already in check_ins
            if "check_in" in existing and not any(c.get("time") == existing["check_in"] for c in check_ins):
                check_ins.append({
                    "time": existing["check_in"],
                    "created_at": existing.get("created_at", existing["check_in"])
                })
            
            # Add the new check-in
            check_ins.append({
                "time": timestamp,
                "created_at": timestamp
            })
            
            # Get the first check-in time (for history)
            first_check_in = None
            if check_ins:
                # Sort check-ins by time
                sorted_check_ins = sorted(check_ins, key=lambda x: x["time"])
                if sorted_check_ins:
                    first_check_in = sorted_check_ins[0]["time"]
            
            if not first_check_in:
                first_check_in = timestamp
            
            # Reset checkout if it exists - we're starting a new session
            update_data = {
                "first_check_in": first_check_in,  # First check-in of the day
                "check_in": timestamp,  # Most recent check-in
                "check_ins": check_ins,
                "updated_at": timestamp
            }
            
            # If there was a previous checkout, save it to history
            if "check_out" in existing and existing["check_out"] is not None:
                check_outs = existing.get("check_outs", [])
                if not any(c.get("time") == existing["check_out"] for c in check_outs):
                    # Calculate duration for the previous session if not recorded
                    last_checkin = None
                    for checkin in reversed(check_ins[:-1]):  # Skip the newest check-in
                        if "time" in checkin:
                            last_checkin = checkin["time"]
                            break
                    
                    if last_checkin:
                        session_duration = (existing["check_out"] - last_checkin).total_seconds() / 3600
                        check_outs.append({
                            "time": existing["check_out"],
                            "duration": round(session_duration, 2),
                            "created_at": existing.get("updated_at", existing["check_out"])
                        })
                        update_data["check_outs"] = check_outs
            
            # Update the record
            attendance_collection.update_one(
                {"user_id": user_id, "date": today},
                {"$set": update_data}
            )
            
            return True, "Check-in successful (additional session)"
        else:
            # First check-in of the day
            attendance_collection.insert_one({
                "user_id": user_id,
                "date": today,
                "first_check_in": timestamp,  # Add first check-in field
                "check_in": timestamp,
                "check_ins": [{
                    "time": timestamp,
                    "created_at": timestamp
                }],
                "created_at": timestamp,
                "updated_at": timestamp
            })
            
            return True, "Check-in successful"
    except Exception as e:
        logging.error(f"Error checking in: {e}")
        return False, f"Error: {str(e)}" 