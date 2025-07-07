# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS
# Import the new google_calendar router
from routers import openai, teamtailor, google_calendar

app = FastAPI()

# ✅ CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include your routers
app.include_router(openai.router, prefix="/open-ai", tags=["OpenAI"])
app.include_router(teamtailor.router, prefix="/teamtailor", tags=["Teamtailor"])
# Include the new Google Calendar router
app.include_router(google_calendar.router, prefix="/google-calendar", tags=["Google Calendar"])

# You can add a simple root endpoint for health check if you like
@app.get("/")
def read_root():
    return {"message": "Orbdent AI Assistant API is running!"}
