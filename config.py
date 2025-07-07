# config.py
import os
import json

# API Keys and Base URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEAMTAILOR_API_KEY = "vzQXfp3cJwmIuJ0X8iXjmY0hKOB3zqQQHBYAtRPZ" # Consider moving this to an environment variable as well
TEAMTAILOR_API_BASE = "https://api.teamtailor.com/v1"

# CORS Settings
CORS_ORIGINS = [
    "https://branding2025.orbdent.com",
    "https://www.branding2025.orbdent.com"
]

# --- UPDATED PATHS FOR PROMPT FILES ---
PROMPT_DIR = "chat-prompts" # Define the directory for prompts

# Load system prompt
try:
    with open(os.path.join(PROMPT_DIR, "prompt.json"), "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = json.load(f).get("system", "")
except FileNotFoundError:
    SYSTEM_PROMPT = "Error: prompt.json not found. Check file path."
    print(f"Warning: {PROMPT_DIR}/prompt.json not found. Check file path.")

# Load Orbdent knowledge
try:
    with open(os.path.join(PROMPT_DIR, "orbdent_knowledge.json"), "r", encoding="utf-8") as f:
        ORBDENT_KNOWLEDGE = json.load(f)
except FileNotFoundError:
    ORBDENT_KNOWLEDGE = {}
    print(f"Warning: {PROMPT_DIR}/orbdent_knowledge.json not found. Check file path.")
# --- END UPDATED PATHS ---

def format_knowledge(knowledge: dict) -> str:
    """Formats the Orbdent knowledge into a string for the AI prompt."""
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

FORMATTED_ORBDENT_KNOWLEDGE = format_knowledge(ORBDENT_KNOWLEDGE)


# --- Google Calendar API Settings ---
# Replace with the actual email of the calendar you want to check availability for
GOOGLE_CALENDAR_ID = "smileworks.dev@gmail.com"

# Path to your downloaded service account JSON key file
# Ensure this path is correct relative to your /app directory on Fly.io
GOOGLE_SERVICE_ACCOUNT_FILE = os.path.join("secrets", "google-service-account.json")

# --- Calendar Availability Logic Settings ---
MIN_SLOT_DURATION_MINUTES = 30 # Minimum length of an available time slot
LOOK_AHEAD_DAYS = 60 # How many days into the future to look for availability (e.g., 2 months)
# Define the standard business hours for each day of the week
# Use 24-hour format (HH:MM)
# Set to None or omit a day if no business hours are available on that day
BUSINESS_HOURS = {
    "monday": {"start": "09:00", "end": "17:00"},
    "tuesday": {"start": "09:00", "end": "17:00"},
    "wednesday": {"start": "09:00", "end": "17:00"},
    "thursday": {"start": "09:00", "end": "17:00"},
    "friday": {"start": "09:00", "end": "17:00"},
    "saturday": None, # Example: No work on Saturday
    "sunday": None    # Example: No work on Sunday
}

# Timezone for calendar calculations. Important for accurate local time.
# Use an IANA timezone name, e.g., 'Europe/Oslo', 'America/New_York'
# Based on your location (Holmestrand, Norway), 'Europe/Oslo' is appropriate.
CALENDAR_TIMEZONE = 'Europe/Oslo'

# Caching for Calendar Data (availability doesn't change by the second)
CALENDAR_CACHE_DURATION = 15 * 60 # Cache for 15 minutes in seconds

# You generally don't filter free/busy by event title. The free/busy API tells you
# when the calendar is busy, not *why*. If you need to filter *events* by title
# for other purposes, that's a different API call.
# TARGET_EVENT_SUMMARY_FILTER = "Visuelt møte" # Not used for free/busy
