# main.py
from fastapi import FastAPI, Request, HTTPException
import json, os
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



API_TOKEN = os.getenv("ADMIN_API_TOKEN", "ep4NjKM6DbdxPGqD86Ay")

@app.post("/admin/update-prompt")
async def update_prompt(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

    data = await request.json()
    with open("prompt.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"status": "ok", "message": "Prompt updated successfully"}
