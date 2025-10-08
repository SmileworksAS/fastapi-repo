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
PROMPTS_DIR = "/data/chat-prompts"

if not os.path.exists(PROMPTS_DIR):
    os.makedirs(PROMPTS_DIR, exist_ok=True)

# Sørg for at filene finnes
for fname in ["prompt.json", "orbdent_knowledge.json"]:
    fpath = os.path.join(PROMPTS_DIR, fname)
    if not os.path.exists(fpath):
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump({"system": "New prompt file"}, f, indent=2)



# === Helper: auth check ===
def check_auth(request: Request):
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header.replace("Bearer ", "").strip()
    if token != ADMIN_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# === GET: hent prompt-fil ===
@app.get("/chat-prompts/{filename}")
async def get_prompt(filename: str):
    filepath = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # 🚫 Ikke hold noe i minne – les alltid rett fra disk
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            content = json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON file")
    
    response = JSONResponse(content)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Data-Source"] = "disk"  # nyttig for testing
    return response




# === POST: oppdater prompt-fil ===
@app.post("/chat-prompts/{filename}")
async def update_prompt(filename: str, data: dict):
    filepath = os.path.join(PROMPTS_DIR, filename)
    print("📝 Writing prompt file:", filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.sync()  # <- sørger for at alt flushes til disk
    return {"status": "success", "file": filename}
