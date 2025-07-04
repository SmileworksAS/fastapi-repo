from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai
import os
import json

# OpenAI Client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load system prompt
with open("prompt.json", "r", encoding="utf-8") as f:
    system_prompt = json.load(f).get("system", "")

# Load knowledge
with open("orbdent_knowledge.json", "r", encoding="utf-8") as f:
    orbdent_knowledge = json.load(f)

# Format knowledge for injection
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

# FastAPI
app = FastAPI()

# CORS setup
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

# Data model
class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4"  # Optional: "gpt-4" or "gpt-3.5-turbo"

# Streaming endpoint with model switch
@app.post("/stream")
async def stream_chat(req: ChatRequest):
    user_input = req.message
    model_name = req.model if req.model in ["gpt-4", "gpt-3.5-turbo"] else "gpt-4"
    print(f"🔁 Using model: {model_name}")

    def event_stream():
        try:
            response = client.chat.completions.create(
                model=model_name,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": format_knowledge(orbdent_knowledge)},
                    {"role": "user", "content": user_input}
                ]
            )

            for chunk in response:
                delta = chunk.choices[0].delta
                yield delta.content or ""

        except Exception as e:
            yield f"[Feil]: {str(e)}"

    return StreamingResponse(event_stream(), media_type="text/plain")
