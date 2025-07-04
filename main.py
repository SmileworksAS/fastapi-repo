from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai
import os
import json

# Load OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load prompt from JSON file
with open("prompt.json", "r", encoding="utf-8") as f:
    system_prompt = json.load(f).get("system", "")

app = FastAPI()

# CORS for your WordPress domain
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

class ChatRequest(BaseModel):
    message: str

@app.post("/stream")
async def stream_chat(req: ChatRequest):
    user_input = req.message

    def event_stream():
        response = client.chat.completions.create(
            model="gpt-4",
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            yield delta.content or ""

    return StreamingResponse(event_stream(), media_type="text/plain")
