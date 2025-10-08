from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json

from config import CORS_ORIGINS, ADMIN_API_TOKEN
from routers import openai, teamtailor, google_calendar

app = FastAPI()

# === Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Include routers ===
app.include_router(openai.router, prefix="/open-ai", tags=["OpenAI"])
app.include_router(teamtailor.router, prefix="/teamtailor", tags=["Teamtailor"])
app.include_router(google_calendar.router, prefix="/google-calendar", tags=["Google Calendar"])


# === Root for sanity check ===
@app.get("/")
def read_root():
    return {"message": "Orbdent AI Assistant API is running!"}


# === Path to prompt folder ===
# Bruk dynamisk sti slik at det fungerer både lokalt og i Fly.io
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "chat-prompts")

if not os.path.exists(PROMPTS_DIR):
    os.makedirs(PROMPTS_DIR, exist_ok=True)


# === Helper: auth check ===
def check_auth(request: Request):
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header.replace("Bearer ", "").strip()
    if token != ADMIN_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# === GET: hent prompt-fil ===
@app.get("/chat-prompts/{filename}")
async def get_prompt(filename: str, request: Request):
    check_auth(request)
    filepath = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = json.load(f)
        return JSONResponse(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# === POST: oppdater prompt-fil ===
@app.post("/chat-prompts/{filename}")
async def update_prompt(filename: str, request: Request):
    check_auth(request)
    filepath = os.path.join(PROMPTS_DIR, filename)

    try:
        data = await request.json()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"status": "success", "file": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")
