# services/google_calendar_service.py
import datetime
import pytz
import os
import json
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import (
    GOOGLE_CALENDAR_ID, GOOGLE_SERVICE_ACCOUNT_FILE, CALENDAR_TIMEZONE,
    MIN_SLOT_DURATION_MINUTES, LOOK_AHEAD_DAYS, BUSINESS_HOURS,
    CALENDAR_CACHE_DURATION
)

# Cache for available timeslots
calendar_cache = {"data": None, "timestamp": 0}

# Initialize Google Calendar API service
def get_calendar_service():
    try:
        # Load credentials from service account file
        if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            print(f"ERROR: Google Service Account key file not found at {GOOGLE_SERVICE_ACCOUNT_FILE}. Check path and deployment.")
            return None

        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar.readonly'] # Read-only scope
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"ERROR: Failed to initialize Google Calendar service: {e}")
        return None

def get_available_timeslots():
    """
    Calculates and returns available time slots for the configured Google Calendar ID
    within specified business hours, considering existing busy periods.
    """
    current_time = time.time()

    # Check if cache is valid and relatively fresh
    if calendar_cache["data"] and (current_time - calendar_cache["timestamp"] < CALENDAR_CACHE_DURATION):
        print("💡 Returning calendar timeslots from cache.")
        return calendar_cache["data"]

    print("🔄 Cache miss or expired. Fetching fresh calendar data from Google Calendar API...")

    service = get_calendar_service()
    if not service:
        return {"error": "Failed to initialize Google Calendar service. Check credentials and file path."}

    try:
        # Define the timezone for consistent calculations
        timezone = pytz.timezone(CALENDAR_TIMEZONE)

        now = datetime.datetime.now(timezone)
        
        # Start checking from the next minute, to avoid issues with already passed time in current minute
        start_time_check = now + datetime.timedelta(minutes=1) 
        start_time_check = start_time_check.replace(second=0, microsecond=0) # Round to the next minute

        time_min = start_time_check.isoformat()
        time_max = (now + datetime.timedelta(days=LOOK_AHEAD_DAYS)).isoformat()

        # Build Free/Busy query body
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": str(timezone),
            "items": [{"id": GOOGLE_CALENDAR_ID}]
        }

        # Execute Free/Busy query
        free_busy_response = service.freebusy().query(body=body).execute()
        
        # Extract busy periods from the response
        calendar_free_busy = free_busy_response.get('calendars', {}).get(GOOGLE_CALENDAR_ID, {})
        busy_periods_raw = calendar_free_busy.get('busy', [])

        # Convert busy periods to datetime objects in the correct timezone
        busy_periods = []
        for busy in busy_periods_raw:
            try:
                busy_start = datetime.datetime.fromisoformat(busy['start']).astimezone(timezone)
                busy_end = datetime.datetime.fromisoformat(busy['end']).astimezone(timezone)
                busy_periods.append({'start': busy_start, 'end': busy_end})
            except ValueError as e:
                print(f"WARN: Could not parse busy period timestamp: {busy['start']} or {busy['end']} - {e}")
        
        # Sort busy periods by start time
        busy_periods.sort(key=lambda x: x['start'])

        available_slots = {}

        # Iterate through each day in the look-ahead period to find slots
        for i in range(LOOK_AHEAD_DAYS):
            current_day = now + datetime.timedelta(days=i)
            # Ensure current_day is set to start of the day in correct timezone
            current_day = current_day.replace(hour=0, minute=0, second=0, microsecond=0)

            day_name = current_day.strftime('%A').lower() # e.g., "monday", "tuesday"

            business_hours_today = BUSINESS_HOURS.get(day_name)
            
            if not business_hours_today:
                continue # Skip days without defined business hours (e.g., weekends)

            day_start_str = business_hours_today["start"]
            day_end_str = business_hours_today["end"]

            # Parse start and end of business day for the current day
            day_start_dt = current_day.replace(
                hour=int(day_start_str.split(':')[0]),
                minute=int(day_start_str.split(':')[1]),
                second=0, microsecond=0
            )
            day_end_dt = current_day.replace(
                hour=int(day_end_str.split(':')[0]),
                minute=int(day_end_str.split(':')[1]),
                second=0, microsecond=0
            )

            # Adjust effective start time for today: must be after 'now'
            if current_day.date() == start_time_check.date() and start_time_check > day_start_dt:
                day_start_dt = start_time_check

            # If business day already ended or effective start is after end for today, skip
            if day_start_dt >= day_end_dt:
                continue

            # Filter busy periods relevant for this specific day's business hours
            busy_intervals_for_day = []
            for busy in busy_periods:
                # Intersect busy period with current day's business hours
                interval_start = max(busy['start'], day_start_dt)
                interval_end = min(busy['end'], day_end_dt)
                if interval_start < interval_end: # Check for overlap
                    busy_intervals_for_day.append({'start': interval_start, 'end': interval_end})
            
            # Sort and merge overlapping busy intervals to simplify free slot calculation
            # This is a basic merge, for robustness more advanced merge might be needed
            merged_busy = []
            if busy_intervals_for_day:
                busy_intervals_for_day.sort(key=lambda x: x['start'])
                merged_busy.append(busy_intervals_for_day[0])
                for current_busy in busy_intervals_for_day[1:]:
                    last_merged = merged_busy[-1]
                    if current_busy['start'] <= last_merged['end']: # Overlap or touch
                        last_merged['end'] = max(last_merged['end'], current_busy['end'])
                    else:
                        merged_busy.append(current_busy)

            # Calculate free slots within the business day
            current_check_time = day_start_dt
            day_slots = []

            for busy in merged_busy:
                # Add free slot before this busy period, if long enough
                if current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= busy['start']:
                    slot_potential_end = busy['start']
                    temp_slot_start = current_check_time
                    while temp_slot_start + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= slot_potential_end:
                        slot_end = temp_slot_start + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES)
                        day_slots.append({
                            'start': temp_slot_start.strftime('%H:%M'),
                            'end': slot_end.strftime('%H:%M')
                        })
                        temp_slot_start = slot_end
                
                # Move current_check_time past this busy period
                current_check_time = max(current_check_time, busy['end'])
                
                # If current_check_time goes past end of business day, stop
                if current_check_time >= day_end_dt:
                    break

            # Add any remaining free slots after the last busy period
            while current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= day_end_dt:
                slot_end = current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES)
                day_slots.append({
                    'start': current_check_time.strftime('%H:%M'),
                    'end': slot_end.strftime('%H:%M')
                })
                current_check_time = slot_end
            
            # Add slots to the main result if any found for the day
            if day_slots:
                date_key = current_day.strftime('%Y-%m-%d')
                available_slots[date_key] = day_slots

        print(f"✅ Found {sum(len(v) for v in available_slots.values())} total available timeslots.")
        final_result = {"timeslots": available_slots}
        calendar_cache["data"] = final_result
        calendar_cache["timestamp"] = current_time
        return final_result

    except HttpError as e:
        print(f"ERROR: Google Calendar API HTTP error (status {e.resp.status}): {e.content.decode()}")
        return {"error": f"Google Calendar API Error: {e.resp.status}", "detail": e.content.decode()}
    except Exception as e:
        print(f"ERROR: Unexpected error in Google Calendar service: {e}")
        return {"error": "Failed to fetch timeslots due to an unexpected error", "detail": str(e)}
