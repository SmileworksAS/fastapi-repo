from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import openai
import os
import json
import requests

# ✅ OpenAI setup for SDK < 1.0
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Load system prompt
with open("prompt.json", "r", encoding="utf-8") as f:
    system_prompt = json.load(f).get("system", "")

# ✅ Load Orbdent knowledge
with open("orbdent_knowledge.json", "r", encoding="utf-8") as f:
    orbdent_knowledge = json.load(f)

def format_knowledge(knowledge):
    lines = []
    lines.append(f"Info om Orbdent:\n\n{knowledge.get('about', '')}\n")

    if "services" in knowledge:
        lines.append("Tjenester vi tilbyr:\n" + "\n".join(f"- {s}" for s in knowledge["services"]))

    if "faq" in knowledge:
        lines.append("\nOfte stilte spørsmål:\n")
        for item in knowledge["faq"]:
            lines.append(f"Spørsmål: {item['question']}\nSvar: {item['answer']}\n")

    if "contact" in knowledge:
        contact = knowledge["contact"]
        lines.append("\nKontaktinfo:\n")
        lines.append(f"E-post: {contact.get('email')}")
        lines.append(f"Nettsted: {contact.get('web')}")
        lines.append(f"Organisasjonsnummer: {contact.get('orgnr')}")

    return "\n".join(lines)

# ✅ FastAPI instance
app = FastAPI()

# ✅ CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://branding2025.orbdent.com",
        "https://www.branding2025.orbdent.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Chat model
class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4"

# ✅ OpenAI streaming endpoint
@app.post("/open-ai/stream")
async def stream_chat(req: ChatRequest):
    user_input = req.message
    model_name = req.model if req.model in ["gpt-4", "gpt-3.5-turbo"] else "gpt-4"
    print(f"🔁 Using model: {model_name}")

    def event_stream():
        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": format_knowledge(orbdent_knowledge)},
                    {"role": "user", "content": user_input}
                ]
            )
            for chunk in response:
                delta = chunk['choices'][0]['delta']
                yield delta.get("content", "")
        except Exception as e:
            yield f"[Feil]: {str(e)}"

    return StreamingResponse(event_stream(), media_type="text/plain")


# ✅ Teamtailor: Available Jobs Endpoint
TEAMTAILOR_API_KEY = "vzQXfp3cJwmIuJ0X8iXjmY0hKOB3zqQQHBYAtRPZ"
TEAMTAILOR_API_BASE = "https://api.teamtailor.com/v1"

@app.get("/teamtailor/available-jobs")
def get_jobs_grouped_by_location():
    headers = {
        "Authorization": f"Token token={TEAMTAILOR_API_KEY}",
        "Accept": "application/vnd.api+json",
        "X-Api-Version": "20240404",
        "Content-Type": "application/vnd.api+json"
    }

    # IMPORTANT: Add ?include=locations to get location data
    res = requests.get(f"{TEAMTAILOR_API_BASE}/jobs?include=locations", headers=headers)
    if res.status_code != 200:
        print(f"Teamtailor API error: {res.status_code} - {res.text}")
        return {"error": "Teamtailor API error", "status": res.status_code, "detail": res.text}

    data = res.json()
    jobs_by_location = {}

    # Create a dictionary for quick lookup of included resources (like locations)
    included_resources = {}
    if "included" in data:
        for item in data["included"]:
            if item.get("type") == "locations": # Make sure to handle 'locations' (plural) as per your JSON
                included_resources[item["id"]] = item["attributes"]

    for job in data.get("data", []):
        attrs = job.get("attributes", {})
        title = attrs.get("title")
        url = job.get("links", {}).get("careersite-job-url") # Use careersite-job-url from 'links'

        if not title or not url:
            continue

        # Get location relationship data
        # Check 'relationships.locations.data' for multiple locations, or 'relationships.location.data' for single
        job_locations = job.get("relationships", {}).get("locations", {}).get("data", [])
        if not job_locations: # Fallback to single 'location' if 'locations' is empty or not present
             single_location_data = job.get("relationships", {}).get("location", {}).get("data")
             if single_location_data:
                 job_locations = [single_location_data]

        display_location = "Uten lokasjon"

        if job_locations:
            # For simplicity, let's take the first location if multiple are present
            # You might want to combine them or handle them differently
            first_location_id = job_locations[0]["id"]
            location_info = included_resources.get(first_location_id)
            if location_info:
                display_location = location_info.get("city", location_info.get("name", "Uten lokasjon"))
            else:
                print(f"Warning: Location ID {first_location_id} not found in included resources.")
        else:
            print(f"Job '{title}' has no associated location relationship.")


        if display_location not in jobs_by_location:
            jobs_by_location[display_location] = []

        jobs_by_location[display_location].append({
            "title": title,
            "url": url
        })

    return {"locations": jobs_by_location}

# ✅ Teamtailor: CV Application Endpoint
@app.post("/teamtailor/cv-application/")
async def submit_cv_application(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    message: str = Form(None),
    cv: UploadFile = File(None),
):
    return JSONResponse({
        "status": "received",
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "cv_filename": cv.filename if cv else None
    })
