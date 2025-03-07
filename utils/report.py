from datetime import datetime, timedelta
import csv
import logging
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import attendance_collection, get_user

def generate_attendance_report(start_date, end_date, filename="attendance_report.csv"):
    """Generate a CSV report of attendance between the given dates."""
    try:
        # Validate dates
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
        # Add one day to end_date to include records from that day
        end_date = end_date + timedelta(days=1)
        
        # Ensure start_date has time set to 00:00:00
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        # Ensure end_date has time set to 00:00:00 of the next day
        end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get attendance records in date range
        attendance_records = attendance_collection.find({
            "date": {"$gte": start_date, "$lt": end_date}
        }).sort("date", 1)
        
        # Open CSV file for writing
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Date', 'User ID', 'Name', 'First Check-in', 'Last Check-out', 'Total Hours', 'Sessions']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write each record
            for record in attendance_records:
                user_id = record.get('user_id')
                user = get_user(user_id)
                user_name = user.get('name', 'Unknown') if user else 'Unknown'
                
                # Get first check-in time (either explicitly stored or the regular check-in)
                first_check_in = record.get('first_check_in', record.get('check_in'))
                first_check_in_str = first_check_in.strftime("%H:%M:%S") if first_check_in else "N/A"
                
                # Get the last check-out time
                check_out = record.get('check_out')
                check_out_str = check_out.strftime("%H:%M:%S") if check_out else "N/A"
                
                # Format date
                date_str = record.get('date').strftime("%Y-%m-%d")
                
                # Get duration (total hours)
                duration = record.get('duration', 0)
                
                # Count number of sessions
                sessions = len(record.get('check_ins', [])) if 'check_ins' in record else 1
                if sessions == 0 and 'check_in' in record:
                    sessions = 1
                
                # Write to CSV
                writer.writerow({
                    'Date': date_str,
                    'User ID': user_id,
                    'Name': user_name,
                    'First Check-in': first_check_in_str,
                    'Last Check-out': check_out_str,
                    'Total Hours': round(duration, 2) if duration else 0,
                    'Sessions': sessions
                })
        
        return True, filename
    except Exception as e:
        logging.error(f"Error generating attendance report: {e}")
        return False, str(e) 