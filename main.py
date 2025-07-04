from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai
import os
import json

# OpenAI Client (new SDK style, for openai>=1.0.0)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load system prompt
with open("prompt.json", "r", encoding="utf-8") as f:
    system_prompt = json.load(f).get("system", "")

# Load knowledge base
with open("orbdent_knowledge.json", "r", encoding="utf-8") as f:
    orbdent_knowledge = json.load(f)

# Format knowledge into a readable plain-text block
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

# FastAPI app
app = FastAPI()

# Allow frontend from WordPress domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://branding2025.orbdent.com",  # your frontend domain
        "https://www.branding2025.orbdent.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data model
class ChatRequest(BaseModel):
    message: str

# Streaming AI endpoint
@app.post("/stream")
async def stream_chat(req: ChatRequest):
    user_input = req.message

    def event_stream():
        response = client.chat.completions.create(
            model="gpt-4",
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

    return StreamingResponse(event_stream(), media_type="text/plain")
