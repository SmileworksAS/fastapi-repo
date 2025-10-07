# main.py
from fastapi import FastAPI, Request, HTTPException
import json, os
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, ADMIN_API_TOKEN
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


PROMPTS_DIR = "/chat-prompts"

@app.get("/chat-prompts/{filename}")
async def get_prompt(filename: str):
    filepath = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    with open(filepath, "r", encoding="utf-8") as f:
        content = json.load(f)
    return JSONResponse(content)

@app.post("/chat-prompts/{filename}")
async def update_prompt(filename: str, data: dict):
    filepath = os.path.join(PROMPTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "file": filename}


API_TOKEN = ADMIN_API_TOKEN

@app.post("/admin/update-prompt")
async def update_prompt(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

    data = await request.json()
    with open("prompt.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"status": "ok", "message": "Prompt updated successfully"}


