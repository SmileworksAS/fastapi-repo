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
    MIN_SLOT_DURATION_MINUTES, LOOK_AHEAD_DAYS, BUSINESS_HOURS, # Keep for potential future use or context
    CALENDAR_CACHE_DURATION, TARGET_EVENT_SUMMARY_FILTER # NEW: Import the event filter
)

# Cache for available timeslots (now, specific events)
calendar_cache = {"data": None, "timestamp": 0}

# Initialize Google Calendar API service
def get_calendar_service():
    try:
        service_account_info_str = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_JSON')
        if not service_account_info_str:
            print("ERROR: GOOGLE_SERVICE_ACCOUNT_KEY_JSON environment variable not found. Set it via 'flyctl secrets set'.")
            return None

        service_account_data = json.loads(service_account_info_str)

        # --- VERY DETAILED DEBUG LOGGING START (Keep these for now) ---
        print("DEBUG: Google Service Account data parsed successfully.")
        print(f"DEBUG: Project ID: {service_account_data.get('project_id', 'N/A')}")
        print(f"DEBUG: Client Email: {service_account_data.get('client_email', 'N/A')}")
        print(f"DEBUG: Private Key ID: {service_account_data.get('private_key_id', 'N/A')}")
        
        private_key_content = service_account_data.get('private_key')
        if private_key_content:
            print(f"DEBUG: Private Key (first 20 chars): {private_key_content[:20]}...")
            print(f"DEBUG: Private Key (last 20 chars): ...{private_key_content[-20:]}")
            print(f"DEBUG: Private Key Length: {len(private_key_content)} characters")
            print(f"DEBUG: Private Key Newline Count: {private_key_content.count('\\n')}") # This line caused previous SyntaxError, now fixed.
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

def get_available_timeslots(): # Function name remains the same for frontend compatibility
    """
    Fetches and returns specific events (e.g., "Visuelt møte") from Google Calendar.
    """
    current_time = time.time()

    # Check if cache is valid and relatively fresh
    if calendar_cache["data"] and (current_time - calendar_cache["timestamp"] < CALENDAR_CACHE_DURATION):
        print("💡 Returning calendar events from cache.")
        return calendar_cache["data"]

    print("🔄 Cache miss or expired. Fetching fresh calendar events from Google Calendar API...")

    service = get_calendar_service()
    if not service:
        return {"error": "Failed to initialize Google Calendar service. Check credentials and file path."}

    try:
        timezone = pytz.timezone(CALENDAR_TIMEZONE)

        now = datetime.datetime.now(timezone)
        time_min = now.isoformat()
        time_max = (now + datetime.timedelta(days=LOOK_AHEAD_DAYS)).isoformat()

        # --- MODIFIED: Use events().list() instead of freebusy().query() ---
        # Fetch events from the calendar
        events_result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True, # Expand recurring events
            orderBy='startTime',
            q=TARGET_EVENT_SUMMARY_FILTER, # Filter by event summary (title)
            maxResults=100 # Adjust as needed, or implement pagination if many events
        ).execute()
        
        events = events_result.get('items', [])
        
        available_events = {}

        if not events:
            print(f"WARN: No events found with summary '{TARGET_EVENT_SUMMARY_FILTER}' in the specified date range.")
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                summary = event.get('summary', 'No Title')

                # Ensure it's a datetime event, not an all-day event, and has a summary
                if 'dateTime' in event['start'] and summary == TARGET_EVENT_SUMMARY_FILTER:
                    try:
                        event_start_dt = datetime.datetime.fromisoformat(start).astimezone(timezone)
                        event_end_dt = datetime.datetime.fromisoformat(end).astimezone(timezone)

                        # Only include events in the future
                        if event_start_dt > now:
                            date_key = event_start_dt.strftime('%Y-%m-%d')
                            if date_key not in available_events:
                                available_events[date_key] = []
                            
                            available_events[date_key].append({
                                'start': event_start_dt.strftime('%H:%M'),
                                'end': event_end_dt.strftime('%H:%M'),
                                'summary': summary # Include summary for debugging if needed
                            })
                    except ValueError as e:
                        print(f"WARN: Could not parse event timestamp for event '{summary}': {start} or {end} - {e}")
        # --- END MODIFIED ---

        print(f"✅ Found {sum(len(v) for v in available_events.values())} total specific events matching '{TARGET_EVENT_SUMMARY_FILTER}'.")
        final_result = {"timeslots": available_events} # Keep 'timeslots' key for frontend compatibility
        calendar_cache["data"] = final_result
        calendar_cache["timestamp"] = current_time
        return final_result

    except HttpError as e:
        print(f"ERROR: Google Calendar API HTTP error (status {e.resp.status}): {e.content.decode()}")
        return {"error": f"Google Calendar API Error: {e.resp.status}", "detail": e.content.decode()}
    except Exception as e:
        print(f"ERROR: Unexpected error in Google Calendar service: {e}")
        return {"error": "Failed to fetch timeslots due to an unexpected error", "detail": str(e)}
