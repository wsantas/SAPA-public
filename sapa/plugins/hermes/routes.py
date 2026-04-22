"""Hermes plugin API routes."""

import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...hermes import hermes

logger = logging.getLogger(__name__)

router = APIRouter()

# Set during plugin startup
tracker: "HermesTracker | None" = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


def _build_messages(req: ChatRequest) -> list[dict]:
    msgs = [m.model_dump() for m in req.history]
    msgs.append({"role": "user", "content": req.message})
    return msgs


@router.get("/health")
async def health():
    online = await hermes.health_check()
    return {
        "online": online,
        "backend": hermes.name,
        "model": hermes.model,
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    """Non-streaming chat. Logs the exchange to history."""
    messages = _build_messages(req)
    start = time.monotonic()
    try:
        response = await hermes.chat(messages)
    except Exception as e:
        logger.exception("Hermes chat failed")
        return {"error": str(e), "online": False}
    latency_ms = int((time.monotonic() - start) * 1000)

    if tracker:
        tracker.log_exchange(
            user_message=req.message,
            assistant_response=response,
            model=hermes.model,
            backend=hermes.name,
            latency_ms=latency_ms,
        )

    return {
        "response": response,
        "model": hermes.model,
        "backend": hermes.name,
        "latency_ms": latency_ms,
    }


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat. Better UX on slow Pi inference."""
    messages = _build_messages(req)
    start = time.monotonic()
    collected: list[str] = []

    async def gen():
        try:
            async for chunk in hermes.chat_stream(messages):
                collected.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            full = "".join(collected)
            latency_ms = int((time.monotonic() - start) * 1000)
            if tracker and full:
                tracker.log_exchange(
                    user_message=req.message,
                    assistant_response=full,
                    model=hermes.model,
                    backend=hermes.name,
                    latency_ms=latency_ms,
                )
            yield f"data: {json.dumps({'done': True, 'latency_ms': latency_ms})}\n\n"
        except Exception as e:
            logger.exception("Hermes stream failed")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/history")
async def get_history(limit: int = 50):
    if not tracker:
        return []
    return tracker.get_recent(limit=limit)


@router.delete("/history")
async def clear_history():
    if not tracker:
        return {"cleared": 0}
    return {"cleared": tracker.clear()}
