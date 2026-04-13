"""Anthropic API wrapper with error handling and retry logic."""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError

from ...config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def add(self, usage) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0)
        self.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def estimate_cost(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * 3.00
        output_cost = (self.output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost

    def __str__(self) -> str:
        return (
            f"Tokens - Input: {self.input_tokens:,}, Output: {self.output_tokens:,}, "
            f"Total: {self.total_tokens:,}, Est. Cost: ${self.estimate_cost():.4f}"
        )


@dataclass
class APIClient:
    model: str = "claude-sonnet-4-20250514"
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    timeout: float = 120.0

    _client: Optional[anthropic.Anthropic] = field(default=None, init=False, repr=False)
    _usage: TokenUsage = field(default_factory=TokenUsage, init=False)

    def __post_init__(self):
        config = get_config()
        if not config.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY in your environment or .env file."
            )
        self._client = anthropic.Anthropic(
            api_key=config.anthropic_api_key,
            timeout=self.timeout,
        )
        logger.info(f"API client initialized with model: {self.model}")

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    def _calculate_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = delay * (0.1 + random.random() * 0.4)
        return delay + jitter

    def chat(self, messages: list[dict], system: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                kwargs = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "messages": messages}
                if system:
                    kwargs["system"] = system
                response = self._client.messages.create(**kwargs)
                self._usage.add(response.usage)
                return self._extract_text(response)
            except RateLimitError as e:
                last_error = e
                time.sleep(self._calculate_delay(attempt))
            except APIConnectionError as e:
                last_error = e
                time.sleep(self._calculate_delay(attempt))
            except APIError as e:
                last_error = e
                if e.status_code and e.status_code >= 500:
                    time.sleep(self._calculate_delay(attempt))
                else:
                    raise
        raise last_error

    def chat_with_web_search(self, messages: list[dict], system: Optional[str] = None, max_tokens: int = 8192, temperature: float = 0.7) -> str:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                kwargs = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "messages": messages, "tools": [{"type": "web_search_20250305"}]}
                if system:
                    kwargs["system"] = system
                response = self._client.messages.create(**kwargs)
                self._usage.add(response.usage)
                return self._extract_text(response)
            except RateLimitError as e:
                last_error = e
                time.sleep(self._calculate_delay(attempt))
            except APIConnectionError as e:
                last_error = e
                time.sleep(self._calculate_delay(attempt))
            except APIError as e:
                last_error = e
                if e.status_code and e.status_code >= 500:
                    time.sleep(self._calculate_delay(attempt))
                else:
                    raise
        raise last_error

    def _extract_text(self, response) -> str:
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)


_client: Optional[APIClient] = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client


def reset_client() -> None:
    global _client
    _client = None
