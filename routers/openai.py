# routers/openai.py
from fastapi import APIRouter, StreamingResponse
from models.chat import ChatRequest
from services.openai_service import get_openai_chat_stream

router = APIRouter()

@router.post("/stream")
async def stream_chat(req: ChatRequest):
    """
    Endpoint for streaming chat responses from OpenAI.
    """
    model_name = req.model if req.model in ["gpt-4", "gpt-3.5-turbo"] else "gpt-4"
    return StreamingResponse(get_openai_chat_stream(req.message, model_name), media_type="text/plain")
