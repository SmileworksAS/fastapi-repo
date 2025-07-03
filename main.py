from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")
app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask(req: ChatRequest):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": req.message}],
    )
    return {"reply": response.choices[0].message["content"]}
