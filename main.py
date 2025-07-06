from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import openai
import os
import json
import requests
import time

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
job_data_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 10 * 60 * 60  # 10 hours in seconds

@app.get("/teamtailor/available-jobs")
def get_jobs_grouped_by_location():
    current_time = time.time()

    # Check if cache is valid and relatively fresh
    if job_data_cache["data"] and (current_time - job_data_cache["timestamp"] < CACHE_DURATION):
        print("💡 Returning jobs from cache.")
        return job_data_cache["data"]

    print("🔄 Cache miss or expired. Fetching fresh data from Teamtailor...")

    headers = {
        "Authorization": f"Token token={TEAMTAILOR_API_KEY}",
        "Accept": "application/vnd.api+json",
        "X-Api-Version": "20240404",
        "Content-Type": "application/vnd.api+json"
    }

    # Step 1: Fetch all available locations
    print(f"Fetching locations from: {TEAMTAILOR_API_BASE}/locations?page[size]=100")
    locations_response = requests.get(f"{TEAMTAILOR_API_BASE}/locations?page[size]=100", headers=headers)
    
    if locations_response.status_code != 200:
        print(f"ERROR: Teamtailor API error fetching locations. Status: {locations_response.status_code}, Response: {locations_response.text}")
        return JSONResponse(
            status_code=locations_response.status_code,
            content={"error": "Teamtailor API error fetching locations", "status": locations_response.status_code, "detail": locations_response.text}
        )
    
    locations_data = locations_response.json()
    print(f"Successfully fetched locations. Found {len(locations_data.get('data', []))} raw locations.")

    locations_map = {}
    if "data" in locations_data:
        for loc in locations_data["data"]:
            if loc.get("type") == "locations":
                loc_id = loc.get("id")
                loc_name = loc.get("attributes", {}).get("city") or loc.get("attributes", {}).get("name")
                if loc_id and loc_name:
                    locations_map[loc_id] = loc_name
    
    if not locations_map:
        print("WARN: No locations with valid IDs and names found after processing Teamtailor locations response.")
        # If no locations, there will be no jobs to fetch by location, so return early
        final_result_empty = {"locations": {}}
        job_data_cache["data"] = final_result_empty
        job_data_cache["timestamp"] = current_time
        return final_result_empty

    print(f"Processed {len(locations_map)} unique locations: {locations_map}")
    
    jobs_by_location = {}

    # Step 2: Fetch jobs for each location
    total_jobs_fetched = 0
    for loc_id, loc_name in locations_map.items():
        jobs_url = f"{TEAMTAILOR_API_BASE}/jobs?filter%5Blocations%5D={loc_id}&include=department&page[size]=100"
        print(f"Fetching jobs for location '{loc_name}' (ID: {loc_id}) from: {jobs_url}")
        jobs_response = requests.get(jobs_url, headers=headers)
        
        if jobs_response.status_code != 200:
            print(f"ERROR: Teamtailor API error fetching jobs for '{loc_name}' ({loc_id}). Status: {jobs_response.status_code}, Response: {jobs_response.text}")
            # Continue to next location even if one fails
            continue

        jobs_data = jobs_response.json()
        raw_jobs_count = len(jobs_data.get("data", []))
        print(f"  Found {raw_jobs_count} raw jobs for '{loc_name}'.")

        if raw_jobs_count == 0:
            continue # No jobs for this location, move to the next

        # Prepare included departments for lookup within this jobs batch
        included_departments = {}
        if "included" in jobs_data:
            for item in jobs_data["included"]:
                if item.get("type") == "departments":
                    included_departments[item["id"]] = item["attributes"]

        for job in jobs_data.get("data", []):
            attrs = job.get("attributes", {})
            title = attrs.get("title")
            body = attrs.get("body", "")
            url = job.get("links", {}).get("careersite-job-url")
            human_status = attrs.get("human-status")

            # Only process jobs that are published and have a title/url
            if not title or not url or human_status != "published":
                print(f"    Skipping job '{title}' (ID: {job.get('id')}) due to missing title/URL or status '{human_status}'.")
                continue

            if loc_name not in jobs_by_location:
                jobs_by_location[loc_name] = []

            jobs_by_location[loc_name].append({
                "title": title,
                "url": url,
                "body": body
            })
            total_jobs_fetched += 1
            print(f"    Added job: '{title}' under '{loc_name}'.")
    
    if total_jobs_fetched == 0:
        print("WARN: No published jobs found across all fetched locations.")
        
    final_result = {"locations": jobs_by_location}
    
    # Cache the result
    job_data_cache["data"] = final_result
    job_data_cache["timestamp"] = current_time
    print(f"✅ Jobs fetched and cached by location. Total jobs processed: {total_jobs_fetched}")

    return final_result

# ✅ Teamtailor: CV Application Endpoint (unchanged)
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
