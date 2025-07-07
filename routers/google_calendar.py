# routers/google_calendar.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.google_calendar_service import get_available_timeslots

router = APIRouter()

@router.get("/available-timeslots")
def get_google_calendar_timeslots():
    """
    Endpoint to retrieve available time slots from Google Calendar.
    """
    timeslots_data = get_available_timeslots()
    
    if "error" in timeslots_data:
        # Return 500 for internal server errors related to calendar fetching
        raise HTTPException(
            status_code=500,
            detail=timeslots_data.get("detail", "Failed to get available timeslots.")
        )
    return JSONResponse(content=timeslots_data)
