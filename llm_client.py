"""
llm_client.py — Unified async LLM client for OpenRouter and Ollama.

Both providers expose an OpenAI-compatible /v1/chat/completions endpoint,
so the same HTTP call works for both — only the base URL and auth differ.
"""
import asyncio
import json
from typing import AsyncIterator, Optional
import httpx
import config


class LLMClient:
    """
    Async LLM client with streaming support.

    Usage:
        client = LLMClient()
        # Full response
        text = await client.complete("system prompt", "user message")
        # Streaming (yields chunks)
        async for chunk in client.stream("system prompt", "user message"):
            print(chunk, end="", flush=True)
    """

    def __init__(self):
        self.provider  = config.LLM_PROVIDER
        self.model     = config.get_active_model()
        self.max_tokens = config.MAX_TOKENS
        self.temperature = config.TEMPERATURE
        self._build_headers_and_url()

    # ──────────────────────────────────────────────────────────────────────────
    def _build_headers_and_url(self):
        if self.provider == "ollama":
            self.base_url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1"
            self.headers  = {"Content-Type": "application/json"}
        else:
            self.base_url = config.OPENROUTER_BASE_URL.rstrip("/")
            self.headers  = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer":  "https://morph.local",
                "X-Title":       "Morph",
            }

    def _payload(self, system: str, user: str, stream: bool = False) -> dict:
        return {
            "model":       self.model,
            "max_tokens":  self.max_tokens,
            "temperature": self.temperature,
            "stream":      stream,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }

    # ── Non-streaming ─────────────────────────────────────────────────────────
    async def complete(
        self,
        system: str,
        user: str,
        timeout: float = 120.0,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url, headers=self.headers, json=self._payload(system, user)
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ── Streaming ─────────────────────────────────────────────────────────────
    async def stream(
        self,
        system: str,
        user: str,
        timeout: float = 180.0,
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/chat/completions"
        payload = self._payload(system, user, stream=True)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", url, headers=self.headers, json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        chunk = json.loads(line)
                        delta = chunk["choices"][0].get("delta", {})
                        if text := delta.get("content", ""):
                            yield text
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    # ── Convenience: stream → collect full text + call a progress callback ────
    async def stream_collect(
        self,
        system: str,
        user: str,
        on_token: Optional[callable] = None,
    ) -> str:
        parts: list[str] = []
        async for chunk in self.stream(system, user):
            parts.append(chunk)
            if on_token:
                await on_token(chunk)
        return "".join(parts)
