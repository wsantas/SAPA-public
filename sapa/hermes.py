"""Hermes inference framework module.

Provides a pluggable LLM backend so the same plugin/feature code runs against
local Ollama (Pi deployment) or a cloud API (Vercel demo deployment) without
branching in feature code.

Backend selection is driven by the SAPA_INFERENCE env var:
    SAPA_INFERENCE=ollama  (default) -> OllamaBackend at localhost:11434
    SAPA_INFERENCE=cloud             -> CloudBackend (Groq / Together / etc.)
"""

import os
import json
import logging
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("HERMES_MODEL", "hermes3:8b")


class HermesBackend:
    """Abstract inference backend."""

    name: str = "abstract"
    model: str = ""

    async def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def health_check(self) -> bool:
        raise NotImplementedError

    async def close(self) -> None:
        pass


class OllamaBackend(HermesBackend):
    """Local Ollama backend. Default for Pi deployment."""

    name = "ollama"

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))

    def _payload(self, messages: list[dict], stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {"num_ctx": 4096, "temperature": 0.3},
        }

    async def chat(self, messages: list[dict]) -> str:
        r = await self.client.post(
            f"{self.base_url}/api/chat",
            json=self._payload(messages, stream=False),
        )
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=self._payload(messages, stream=True),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = chunk.get("message", {})
                content = msg.get("content")
                if content:
                    yield content
                if chunk.get("done"):
                    return

    async def health_check(self) -> bool:
        try:
            r = await self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self.client.aclose()


def _build_backend() -> HermesBackend:
    mode = os.environ.get("SAPA_INFERENCE", "ollama").lower()
    if mode == "cloud":
        # Placeholder for future CloudBackend (Groq/Together/Claude API).
        # Falls back to Ollama until implemented so dev environments don't crash.
        logger.warning("SAPA_INFERENCE=cloud requested but CloudBackend not implemented; using Ollama")
    return OllamaBackend()


# Module-level singleton — imported by plugins and feature code
hermes: HermesBackend = _build_backend()
