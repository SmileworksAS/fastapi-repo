from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import openai
import os
import json
import requests
import time # Import time for caching

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

# --- Caching Mechanism ---
# Simple in-memory cache
job_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 10 * 60 * 60  # 10 hours in seconds

@app.get("/teamtailor/available-jobs")
def get_jobs_grouped_by_department(): # Changed function name to reflect new grouping
    current_time = time.time()

    # Check if cache is valid and relatively fresh
    if job_cache["data"] and (current_time - job_cache["timestamp"] < CACHE_DURATION):
        print("💡 Returning jobs from cache.")
        return job_cache["data"]

    headers = {
        "Authorization": f"Token token={TEAMTAILOR_API_KEY}",
        "Accept": "application/vnd.api+json",
        "X-Api-Version": "20240404",
        "Content-Type": "application/vnd.api+json"
    }

    # IMPORTANT: Include 'department' instead of 'locations'
    # Also added page[size]=100 to attempt to get more results if available,
    # as default might be less than total jobs.
    # For full pagination, you'd need a loop.
    res = requests.get(f"{TEAMTAILOR_API_BASE}/jobs?include=department&page[size]=100", headers=headers)
    if res.status_code != 200:
        print(f"Teamtailor API error: {res.status_code} - {res.text}")
        return JSONResponse(
            status_code=res.status_code,
            content={"error": "Teamtailor API error", "status": res.status_code, "detail": res.text}
        )

    data = res.json()
    jobs_by_category = {} # Changed variable name to be more generic

    # Create a dictionary for quick lookup of included resources (like departments)
    included_resources = {}
    if "included" in data:
        for item in data["included"]:
            if item.get("type") == "departments": # Teamtailor uses 'departments' plural for included resources
                included_resources[item["id"]] = item["attributes"]

    for job in data.get("data", []):
        attrs = job.get("attributes", {})
        title = attrs.get("title")
        body = attrs.get("body", "")
        url = job.get("links", {}).get("careersite-job-url")

        # Only process jobs that are published and have a title/url
        if not title or not url or attrs.get("human-status") != "published":
            continue

        # Get department relationship data
        # Note: relationships.department.data refers to the singular department associated with the job
        department_data = job.get("relationships", {}).get("department", {}).get("data")
        
        display_category = "Uten kategori" # Default for jobs without a department

        if department_data and department_data.get("id") and department_data.get("type") == "departments":
            department_id = department_data["id"]
            department_info = included_resources.get(department_id)
            if department_info:
                display_category = department_info.get("name", "Uten kategori")
            else:
                print(f"Warning: Department ID {department_id} not found in included resources for job '{title}'.")
        else:
            print(f"Job '{title}' has no associated department relationship or invalid department data.")

        if display_category not in jobs_by_category:
            jobs_by_category[display_category] = []

        jobs_by_category[display_category].append({
            "title": title,
            "url": url,
            "body": body
        })

    result = {"categories": jobs_by_category} # Changed key to 'categories'
    
    # Cache the result
    job_cache["data"] = result
    job_cache["timestamp"] = current_time
    print("✅ Jobs fetched and cached.")

    return result

# ✅ Teamtailor: CV Application Endpoint
@app.post("/teamtailor/cv-application/")
async def submit_cv_application(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    message: str = Form(None),
    cv: UploadFile = File(None),
):
    # This endpoint is unchanged, but ensuring it's here for completeness
    # In a real application, you'd likely integrate with Teamtailor's application API
    # using requests.post to submit the data and CV file.
    # This is currently just returning the received data.
    return JSONResponse({
        "status": "received",
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "cv_filename": cv.filename if cv else None
    })
