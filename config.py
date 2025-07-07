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
