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
    GOOGLE_CALENDAR_ID, CALENDAR_TIMEZONE,
    MIN_SLOT_DURATION_MINUTES, LOOK_AHEAD_DAYS, BUSINESS_HOURS,
    CALENDAR_CACHE_DURATION
)

# Cache for available timeslots
calendar_cache = {"data": None, "timestamp": 0}

# Initialize Google Calendar API service
def get_calendar_service():
    try:
        service_account_info_str = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_JSON')
        if not service_account_info_str:
            print("ERROR: GOOGLE_SERVICE_ACCOUNT_KEY_JSON environment variable not found. Set it via 'flyctl secrets set'.")
            return None

        # Parse the JSON string from the env var
        service_account_data = json.loads(service_account_info_str)

        # --- VERY DETAILED DEBUG LOGGING START ---
        print("DEBUG: Google Service Account data parsed successfully.")
        print(f"DEBUG: Project ID: {service_account_data.get('project_id', 'N/A')}")
        print(f"DEBUG: Client Email: {service_account_data.get('client_email', 'N/A')}")
        print(f"DEBUG: Private Key ID: {service_account_data.get('private_key_id', 'N/A')}")
        
        # Check if private_key exists and is not empty
        private_key_content = service_account_data.get('private_key')
        if private_key_content:
            print(f"DEBUG: Private Key (first 20 chars): {private_key_content[:20]}...")
            print(f"DEBUG: Private Key (last 20 chars): ...{private_key_content[-20:]}")
            print(f"DEBUG: Private Key Length: {len(private_key_content)} characters")
            # --- CORRECTED LINE 45 BELOW ---
            print(f"DEBUG: Private Key Newline Count: {private_key_content.count('\n')}") # FIXED: '\n' instead of '\\n'
            # --- END CORRECTED LINE 45 ---
        else:
            print("DEBUG: Private Key field is missing or empty.")
        # --- VERY DETAILED DEBUG LOGGING END ---

        creds = service_account.Credentials.from_service_account_info(
            service_account_data,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        return build('calendar', 'v3', credentials=creds)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse GOOGLE_SERVICE_ACCOUNT_KEY_JSON. Invalid JSON format: {e}")
        print(f"Raw secret string (first 100 chars): {service_account_info_str[:100]}...")
        return None
    except Exception as e:
        print(f"ERROR: Failed to initialize Google Calendar service in get_calendar_service: {e}")
        return None

def get_available_timeslots():
    current_time = time.time()
    if calendar_cache["data"] and (current_time - calendar_cache["timestamp"] < CALENDAR_CACHE_DURATION):
        print("💡 Returning calendar timeslots from cache.")
        return calendar_cache["data"]

    print("🔄 Cache miss or expired. Fetching fresh calendar data from Google Calendar API...")

    service = get_calendar_service()
    if not service:
        # get_calendar_service already printed an error, so just return
        return {"error": "Failed to initialize Google Calendar service. Check credentials and file path."}

    try:
        timezone = pytz.timezone(CALENDAR_TIMEZONE)

        now = datetime.datetime.now(timezone)
        start_time_check = now + datetime.timedelta(minutes=1) 
        start_time_check = start_time_check.replace(second=0, microsecond=0)

        time_min = start_time_check.isoformat()
        time_max = (now + datetime.timedelta(days=LOOK_AHEAD_DAYS)).isoformat()

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": str(timezone),
            "items": [{"id": GOOGLE_CALENDAR_ID}]
        }

        free_busy_response = service.freebusy().query(body=body).execute()
        
        calendar_free_busy = free_busy_response.get('calendars', {}).get(GOOGLE_CALENDAR_ID, {})
        busy_periods_raw = calendar_free_busy.get('busy', [])

        busy_periods = []
        for busy in busy_periods_raw:
            try:
                busy_start = datetime.datetime.fromisoformat(busy['start']).astimezone(timezone)
                busy_end = datetime.datetime.fromisoformat(busy['end']).astimezone(timezone)
                busy_periods.append({'start': busy_start, 'end': busy_end})
            except ValueError as e:
                print(f"WARN: Could not parse busy period timestamp: {busy['start']} or {busy['end']} - {e}")
        
        busy_periods.sort(key=lambda x: x['start'])

        available_slots = {}

        for i in range(LOOK_AHEAD_DAYS):
            current_day = now + datetime.timedelta(days=i)
            current_day = current_day.replace(hour=0, minute=0, second=0, microsecond=0)

            day_name = current_day.strftime('%A').lower()

            business_hours_today = BUSINESS_HOURS.get(day_name)
            
            if not business_hours_today:
                continue

            day_start_str = business_hours_today["start"]
            day_end_str = business_hours_today["end"]

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

            if current_day.date() == start_time_check.date() and start_time_check > day_start_dt:
                day_start_dt = start_time_check

            if day_start_dt >= day_end_dt:
                continue

            busy_intervals_for_day = []
            for busy in busy_periods:
                interval_start = max(busy['start'], day_start_dt)
                interval_end = min(busy['end'], day_end_dt)
                if interval_start < interval_end:
                    busy_intervals_for_day.append({'start': interval_start, 'end': interval_end})
            
            merged_busy = []
            if busy_intervals_for_day:
                busy_intervals_for_day.sort(key=lambda x: x['start'])
                merged_busy.append(busy_intervals_for_day[0])
                for current_busy in busy_intervals_for_day[1:]:
                    last_merged = merged_busy[-1]
                    if current_busy['start'] <= last_merged['end']:
                        last_merged['end'] = max(last_merged['end'], current_busy['end'])
                    else:
                        merged_busy.append(current_busy)

            current_check_time = day_start_dt
            day_slots = []

            for busy in merged_busy:
                if current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= busy['start']:
                    slot_potential_end = busy['start']
                    temp_slot_start = current_check_time
                    while temp_slot_start + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= slot_potential_end:
                        slot_end = temp_slot_start + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES)
                        day_slots.append({
                            'start': temp_slot_start.strftime('%H:%M'),
                            'end': slot_end.strftime('%H:%M')
                        })
                        temp_slot_start = slot_slot_end
                
                current_check_time = max(current_check_time, busy['end'])
                
                if current_check_time >= day_end_dt:
                    break

            while current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES) <= day_end_dt:
                slot_end = current_check_time + datetime.timedelta(minutes=MIN_SLOT_DURATION_MINUTES)
                day_slots.append({
                    'start': current_check_time.strftime('%H:%M'),
                    'end': slot_end.strftime('%H:%M')
                })
                current_check_time = slot_end
            
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
