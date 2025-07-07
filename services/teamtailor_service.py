# services/teamtailor_service.py
import requests
import time
from config import TEAMTAILOR_API_KEY, TEAMTAILOR_API_BASE

# Simple in-memory cache for the final aggregated job data
job_data_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 10 * 60 * 60  # 10 hours in seconds

def fetch_and_group_jobs_by_location():
    """
    Fetches jobs from Teamtailor API, groups them by location, and caches the result.
    """
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
    locations_response = requests.get(f"{TEAMTAILOR_API_BASE}/locations?page[size]=30", headers=headers)
    
    if locations_response.status_code != 200:
        print(f"ERROR: Teamtailor API error fetching locations. Status: {locations_response.status_code}, Response: {locations_response.text}")
        return {"error": "Teamtailor API error fetching locations", "status": locations_response.status_code, "detail": locations_response.text}
    
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
        print("WARN: No locations with valid IDs and names found after processing Teamtailor locations response. Returning empty job list.")
        final_result_empty = {"locations": {}}
        job_data_cache["data"] = final_result_empty
        job_data_cache["timestamp"] = current_time
        return final_result_empty

    print(f"Processed {len(locations_map)} unique locations: {locations_map}")
    
    jobs_by_location = {}

    # Step 2: Fetch jobs for each location
    total_jobs_fetched_count = 0
    for loc_id, loc_name in locations_map.items():
        jobs_url = f"{TEAMTAILOR_API_BASE}/jobs?filter%5Blocations%5D={loc_id}&include=department&page[size]=30"
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

        # Prepare included departments for lookup within this jobs batch (if needed in future, currently not used)
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
                "id": job.get("id"), 
                "title": title,
                "url": url,
                "body": body
            })
            total_jobs_fetched_count += 1
            print(f"    Added job: '{title}' under '{loc_name}'.")
    
    if total_jobs_fetched_count == 0:
        print("WARN: No published jobs found across all fetched locations.")
        
    final_result = {"locations": jobs_by_location}
    
    # Cache the result
    job_data_cache["data"] = final_result
    job_data_cache["timestamp"] = current_time
    print(f"✅ Jobs fetched and cached by location. Total jobs processed: {total_jobs_fetched_count}")

    return final_result

def submit_cv_application(name: str, email: str, phone: str = None, message: str = None, cv_filename: str = None):
    """
    Placeholder for submitting CV application logic.
    In a real application, this would interact with the Teamtailor API to create an application.
    """
    print(f"Received CV application: Name={name}, Email={email}, CV={cv_filename}")
    # Here you would typically make a POST request to Teamtailor's application API
    # Example (simplified, actual implementation would be more complex with file handling):
    # data = {
    #     "data": {
    #         "type": "applications",
    #         "attributes": {
    #             "first-name": name.split(' ')[0],
    #             "last-name": ' '.join(name.split(' ')[1:]) if ' ' in name else '',
    #             "email": email,
    #             "phone": phone,
    #             "message": message
    #         },
    #         "relationships": {
    #             "job": {
    #                 "data": {
    #                     "type": "jobs",
    #                     "id": "JOB_ID_HERE" # You'd need to pass the job ID from the frontend
    #                 }
    #             }
    #         }
    #     }
    # }
    # try:
    #     response = requests.post(f"{TEAMTAILOR_API_BASE}/applications", headers=headers, json=data)
    #     response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    #     return {"status": "success", "detail": response.json()}
    # except requests.exceptions.RequestException as e:
    #     return {"status": "error", "detail": str(e)}

    # For now, return a success status as per original main.py
    return {
        "status": "received",
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "cv_filename": cv_filename
    }
