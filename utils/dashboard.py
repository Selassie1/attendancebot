# utils/dashboard.py
import io
import logging
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid GUI dependencies
import database
from database import get_date_range_attendance, get_user, get_all_users
import pytz
import config

def get_user_name(user_id):
    """Get user's full name."""
    user = get_user(user_id)
    if not user:
        return f"User {user_id}"
    
    if user["last_name"]:
        return f"{user['first_name']} {user['last_name']}"
    return user["first_name"]

def generate_attendance_report(start_date, end_date):
    """Generate an attendance report for a date range."""
    try:
        # Ensure start_date and end_date are datetime objects
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
        
        # Validate dates
        if not start_date or not end_date:
            return None, "Invalid date range: Start date or end date is missing."
        
        # Get attendance data
        records = get_date_range_attendance(start_date, end_date)
        
        if not records:
            return None, "No attendance records found for the specified date range."
        
        # Convert to pandas DataFrame
        data = []
        for record in records:
            user_name = get_user_name(record["user_id"])
            check_in = record.get("check_in")
            check_out = record.get("check_out")
            duration = record.get("duration", 0)
            
            check_in_str = "N/A"
            if check_in:
                try:
                    check_in_str = check_in.strftime("%H:%M:%S")
                except AttributeError:
                    check_in_str = "Invalid format"
            
            check_out_str = "N/A"
            if check_out:
                try:
                    check_out_str = check_out.strftime("%H:%M:%S")
                except AttributeError:
                    check_out_str = "Invalid format"
            
            data.append({
                "Date": record["date"].strftime("%Y-%m-%d"),
                "User": user_name,
                "Check In": check_in_str,
                "Check Out": check_out_str,
                "Duration (hours)": duration
            })
        
        df = pd.DataFrame(data)
        
        # Create CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        return csv_data, "Attendance report generated successfully."
    except Exception as e:
        logging.error(f"Error generating attendance report: {e}")
        return None, f"Error generating report: {str(e)}"

def generate_dashboard_image(days=7):
    """Generate a dashboard image with attendance statistics."""
    try:
        # Calculate date range
        end_date = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - datetime.timedelta(days=days-1)
        
        # Get attendance data
        records = get_date_range_attendance(start_date, end_date)
        
        if not records:
            return None, "No attendance records found for generating dashboard."
        
        # Convert to pandas DataFrame
        data = []
        for record in records:
            # Skip records with missing or invalid date
            if not record.get("date"):
                continue
                
            try:
                user_name = get_user_name(record["user_id"])
                check_in = record.get("check_in")
                check_out = record.get("check_out")
                duration = record.get("duration", 0)
                
                # Ensure date is valid for DataFrame
                record_date = record["date"]
                if not isinstance(record_date, (datetime.datetime, datetime.date)):
                    try:
                        record_date = datetime.datetime.strptime(str(record_date), "%Y-%m-%d")
                    except (ValueError, TypeError):
                        # Skip this record if date can't be parsed
                        continue
                
                if check_in:
                    data.append({
                        "date": record_date,
                        "user": user_name,
                        "duration": duration if check_out else 0,
                        "status": "Complete" if check_out else "Incomplete"
                    })
            except Exception as record_error:
                # Log and skip problematic records
                logging.error(f"Error processing record: {record_error}")
                continue
        
        # Check if we have any valid data after filtering
        if not data:
            return None, "No valid attendance records found for generating dashboard."
            
        df = pd.DataFrame(data)
        
        # Create figure with subplots
        plt.figure(figsize=(12, 10))
        
        # 1. Daily attendance count
        plt.subplot(2, 2, 1)
        try:
            daily_counts = df.groupby("date").size()
            daily_counts.plot(kind="bar")
            plt.title("Daily Attendance Count")
            plt.xlabel("Date")
            plt.ylabel("Number of Check-ins")
            plt.xticks(rotation=45)
        except Exception as e:
            logging.error(f"Error creating daily attendance chart: {e}")
            plt.text(0.5, 0.5, "Error generating chart", ha="center", va="center")
            plt.title("Daily Attendance Count")
        
        # 2. User attendance frequency
        plt.subplot(2, 2, 2)
        try:
            user_counts = df.groupby("user").size().sort_values(ascending=False)
            user_counts.plot(kind="bar")
            plt.title("Attendance by User")
            plt.xlabel("User")
            plt.ylabel("Number of Check-ins")
            plt.xticks(rotation=45)
        except Exception as e:
            logging.error(f"Error creating user attendance chart: {e}")
            plt.text(0.5, 0.5, "Error generating chart", ha="center", va="center")
            plt.title("Attendance by User")
        
        # 3. Average duration by user
        plt.subplot(2, 2, 3)
        try:
            # Filter out incomplete records
            complete_records = df[df["status"] == "Complete"]
            if not complete_records.empty:
                avg_duration = complete_records.groupby("user")["duration"].mean().sort_values(ascending=False)
                avg_duration.plot(kind="bar")
                plt.title("Average Work Duration by User")
                plt.xlabel("User")
                plt.ylabel("Average Hours")
                plt.xticks(rotation=45)
            else:
                plt.text(0.5, 0.5, "No complete records", ha="center", va="center")
                plt.title("Average Work Duration by User")
        except Exception as e:
            logging.error(f"Error creating duration chart: {e}")
            plt.text(0.5, 0.5, "Error generating chart", ha="center", va="center")
            plt.title("Average Work Duration by User")
        
        # 4. Complete vs Incomplete check-ins
        plt.subplot(2, 2, 4)
        try:
            status_counts = df["status"].value_counts()
            status_counts.plot(kind="pie", autopct="%1.1f%%")
            plt.title("Complete vs. Incomplete Check-ins")
            plt.ylabel("")
        except Exception as e:
            logging.error(f"Error creating status chart: {e}")
            plt.text(0.5, 0.5, "Error generating chart", ha="center", va="center")
            plt.title("Complete vs. Incomplete Check-ins")
        
        plt.tight_layout()
        
        # Save figure to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        
        plt.close()
        
        return buf, "Dashboard generated successfully."
    except Exception as e:
        logging.error(f"Error generating dashboard: {e}")
        return None, f"Error generating dashboard: {str(e)}" 