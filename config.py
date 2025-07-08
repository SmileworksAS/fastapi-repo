# config.py
import os
import json

# --- API Keys and Base URLs ---
# OpenAI API Key: Loaded from environment variable for security.
# Ensure you set this in your Fly.io secrets: fly secrets set OPENAI_API_KEY="your_openai_key_here"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Teamtailor API Key: Currently hardcoded, but consider moving to environment variable for production.
# Example for Fly.io secrets: fly secrets set TEAMTAILOR_API_KEY="your_teamtailor_key_here"
TEAMTAILOR_API_KEY = "vzQXfp3cJwmIuJ0X8iXjmY0hKOB3zqQQHBYAtRPZ" 
TEAMTAILOR_API_BASE = "https://api.teamtailor.com/v1"

# --- CORS Settings ---
# List of origins allowed to access your FastAPI application.
CORS_ORIGINS = [
    "https://branding2025.orbdent.com",
    "https://www.branding2025.orbdent.com"
    # Add any other domains your frontend will be deployed on,
    # or "http://localhost:port" for local development.
]

# --- Prompt Files and Knowledge Loading ---
# Directory where chat prompt and knowledge JSON files are located.
PROMPT_DIR = "chat-prompts"

# Load system prompt for OpenAI
try:
    with open(os.path.join(PROMPT_DIR, "prompt.json"), "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = json.load(f).get("system", "")
except FileNotFoundError:
    SYSTEM_PROMPT = "Error: prompt.json not found. Please ensure 'prompt.json' is in the 'chat-prompts/' directory."
    print(f"Warning: {PROMPT_DIR}/prompt.json not found. Check file path.")

# Load Orbdent knowledge base for OpenAI
try:
    with open(os.path.join(PROMPT_DIR, "orbdent_knowledge.json"), "r", encoding="utf-8") as f:
        ORBDENT_KNOWLEDGE = json.load(f)
except FileNotFoundError:
    ORBDENT_KNOWLEDGE = {}
    print(f"Warning: {PROMPT_DIR}/orbdent_knowledge.json not found. Check file path.")

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
# ID of the Google Calendar to fetch availability from.
# This is usually the email address associated with the calendar.
GOOGLE_CALENDAR_ID = "smileworks.dev@gmail.com"

# The Google Service Account key is loaded directly from a Fly.io secret.
# Set this secret using: flyctl secrets set GOOGLE_SERVICE_ACCOUNT_KEY_JSON="$(cat your-key-file.json)" -a your-app-name
# (No need for GOOGLE_SERVICE_ACCOUNT_FILE path anymore in the code)

# Timezone for all calendar calculations. Crucial for accurate local time.
# Use an IANA timezone name, e.g., 'Europe/Oslo', 'America/New_York'.
# Holmestrand, Norway is in 'Europe/Oslo' timezone.
CALENDAR_TIMEZONE = 'Europe/Oslo'

# --- Calendar Availability Logic Settings ---
# Minimum duration for a time slot (e.g., if you only offer 30-minute meetings).
# This is less critical for listing existing events, but good to keep.
MIN_SLOT_DURATION_MINUTES = 30

# How many days into the future to look for events/availability.
LOOK_AHEAD_DAYS = 60

# Define standard business hours for each day of the week (24-hour format HH:MM).
# Events outside these hours will not be considered "available" slots.
# Set to None or omit a day if no business hours are available (e.g., weekends).
BUSINESS_HOURS = {
    "monday": {"start": "09:00", "end": "17:00"},
    "tuesday": {"start": "09:00", "end": "17:00"},
    "wednesday": {"start": "09:00", "end": "17:00"},
    "thursday": {"start": "09:00", "end": "17:00"},
    "friday": {"start": "09:00", "end": "17:00"},
    "saturday": None,
    "sunday": None
}

# Target event summary (title) to filter by when fetching events from Google Calendar.
# Only events with this exact summary will be fetched and displayed.
TARGET_EVENT_SUMMARY_FILTER = "Visuelt møte"

# --- Caching Durations ---
# Cache duration for Teamtailor job data (10 hours).
TEAMTAILOR_CACHE_DURATION = 10 * 60 * 60

# Cache duration for Google Calendar data (15 minutes).
CALENDAR_CACHE_DURATION = 15 * 60
