from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os
from fastapi.middleware.cors import CORSMiddleware  # <-- Add this

openai.api_key = os.getenv("OPENAI_API_KEY")
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://branding2025.orbdent.com",  # Your WordPress frontend
        "https://www.branding2025.orbdent.com"  # Optional www version
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask(req: ChatRequest):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": req.message}],
    )
    return {"reply": response.choices[0].message["content"]}
