from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import openai
import os
import requests

app = FastAPI()

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://branding2025.orbdent.com"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OpenAI setup ---
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Chat assistant endpoint (/stream) ---

class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4"

@app.post("/stream")
async def ask_stream(req: ChatRequest):
    def generate():
        try:
            completion = openai.ChatCompletion.create(
                model=req.model,
                messages=[
                    {"role": "system", "content": "Du er en hjelpsom og profesjonell AI-assistent for Orbdent, et selskap innen tannhelse og rekruttering."},
                    {"role": "user", "content": req.message}
                ],
                stream=True,
                temperature=0.7,
                max_tokens=800,
            )
            for chunk in completion:
                content = chunk['choices'][0]['delta'].get('content', '')
                yield content
        except Exception as e:
            yield f"\n\n[Feil: {str(e)}]"

    return StreamingResponse(generate(), media_type="text/plain")

# --- Teamtailor job listing (/teamtailor/available-jobs) ---

TEAMTAILOR_API_KEY = "vzQXfp3cJwmIuJ0X8iXjmY0hKOB3zqQQHBYAtRPZ"
TEAMTAILOR_API_BASE = "https://api.teamtailor.com/v1"

@app.get("/teamtailor/available-jobs")
def get_jobs_grouped_by_location():
    headers = {
        "Authorization": f"Token token={TEAMTAILOR_API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    res = requests.get(f"{TEAMTAILOR_API_BASE}/jobs", headers=headers)
    if res.status_code != 200:
        return {"error": "Teamtailor API error", "status": res.status_code}

    data = res.json()
    jobs_by_location = {}

    for job in data.get("data", []):
        attrs = job.get("attributes", {})
        title = attrs.get("title")
        location = attrs.get("location", {}).get("city", "Uten lokasjon")
        url = attrs.get("career-site-url")

        if not title or not url:
            continue

        if location not in jobs_by_location:
            jobs_by_location[location] = []

        jobs_by_location[location].append({
            "title": title,
            "url": url
        })

    return {"locations": jobs_by_location}

# --- Teamtailor CV application form (/teamtailor/cv-application) ---

@app.post("/teamtailor/cv-application/")
async def submit_cv_application(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    message: str = Form(None),
    cv: UploadFile = File(None),
):
    # Logging / placeholder for now
    return JSONResponse({
        "status": "received",
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "cv_filename": cv.filename if cv else None
    })
