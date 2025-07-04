from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import openai

# Init OpenAI client (new API structure)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# CORS
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

# Request model
class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask(req: ChatRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": req.message}
            ]
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
