# routers/teamtailor.py
from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.teamtailor_service import fetch_and_group_jobs_by_location, submit_cv_application

router = APIRouter()

@router.get("/available-jobs")
def get_available_jobs():
    """
    Fetches and returns available jobs grouped by location from Teamtailor.
    """
    jobs_data = fetch_and_group_jobs_by_location()
    
    if "error" in jobs_data:
        # If the service function returned an error, raise an HTTPException
        raise HTTPException(
            status_code=jobs_data.get("status", 500),
            detail=jobs_data.get("detail", "An unexpected error occurred.")
        )
    return JSONResponse(content=jobs_data)

@router.post("/cv-application/")
async def post_cv_application(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    message: str = Form(None),
    cv: UploadFile = File(None),
):
    """
    Endpoint for submitting a CV application (placeholder).
    """
    cv_filename = cv.filename if cv else None
    result = submit_cv_application(name, email, phone, message, cv_filename)
    return JSONResponse(content=result)
