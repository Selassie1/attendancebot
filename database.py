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
        
        if "check_out" in existing:
            return False, "Already checked out today"
        
        # Calculate duration
        duration = (timestamp - existing["check_in"]).total_seconds() / 3600  # hours
        
        attendance_collection.update_one(
            {"user_id": user_id, "date": today},
            {
                "$set": {
                    "check_out": timestamp,
                    "duration": round(duration, 2),
                    "updated_at": timestamp
                }
            }
        )
        return True, f"Check-out successful. Duration: {round(duration, 2)} hours"
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
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    return list(attendance_collection.find({"date": today}))

def get_date_range_attendance(start_date, end_date):
    """Get attendance within a date range."""
    return list(attendance_collection.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }).sort("date", DESCENDING))

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
    """Get user's full name."""
    user = get_user(user_id)
    if not user:
        return f"User {user_id}"
    
    if user.get("last_name"):
        return f"{user['first_name']} {user.get('last_name')}"
    return user["first_name"]

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
            if "check_out" in existing:
                # User has already checked out, add a new check-in
                check_ins = existing.get("check_ins", [])
                if "check_in" in existing:
                    # Add the original check-in if not already in check_ins
                    if not any(c["time"] == existing["check_in"] for c in check_ins):
                        check_ins.append({
                            "time": existing["check_in"],
                            "created_at": existing.get("created_at", existing["check_in"])
                        })
                
                # Add the new check-in
                check_ins.append({
                    "time": timestamp,
                    "created_at": timestamp
                })
                
                # Update the record
                attendance_collection.update_one(
                    {"user_id": user_id, "date": today},
                    {
                        "$set": {
                            "check_in": timestamp,  # Most recent check-in
                            "check_ins": check_ins,
                            "check_out": None,  # Remove check-out since user is checking in again
                            "duration": None,   # Remove duration as well
                            "updated_at": timestamp
                        }
                    }
                )
                return True, "Check-in successful (additional)"
            else:
                # User has not checked out yet - just store in check_ins array
                check_ins = existing.get("check_ins", [])
                if "check_in" in existing:
                    # Add the original check-in if not already in check_ins
                    if not any(c["time"] == existing["check_in"] for c in check_ins):
                        check_ins.append({
                            "time": existing["check_in"],
                            "created_at": existing.get("created_at", existing["check_in"])
                        })
                
                # Add the new check-in (only if it's significantly different from previous)
                if not check_ins or (timestamp - check_ins[-1]["time"]).total_seconds() > 60:  # More than a minute difference
                    check_ins.append({
                        "time": timestamp,
                        "created_at": timestamp
                    })
                    
                    # Update the record
                    attendance_collection.update_one(
                        {"user_id": user_id, "date": today},
                        {
                            "$set": {
                                "check_in": timestamp,  # Most recent check-in
                                "check_ins": check_ins,
                                "updated_at": timestamp
                            }
                        }
                    )
                    return True, f"Check-in updated ({len(check_ins)} check-ins today)"
                else:
                    return False, "Already checked in recently"
        else:
            # No existing record, create a new one
            attendance_collection.insert_one({
                "user_id": user_id,
                "date": today,
                "check_in": timestamp,
                "check_ins": [{
                    "time": timestamp,
                    "created_at": timestamp
                }],
                "created_at": timestamp,
                "updated_at": timestamp
            })
            return True, "First check-in of the day"
    except Exception as e:
        logging.error(f"Error in multiple check-in: {e}")
        return False, f"Error: {str(e)}" 