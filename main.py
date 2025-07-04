from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for your WordPress frontend domain
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

# Define expected request format
class ChatRequest(BaseModel):
    message: str

# POST endpoint: /ask
@app.post("/ask")
async def ask(req: ChatRequest):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": req.message}],
        )
        return {"reply": response.choices[0].message["content"]}
    except Exception as e:
        # Catch and return error as JSON
        return {"error": str(e)}
