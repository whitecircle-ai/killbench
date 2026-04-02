from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .config import (
    BENCH_REASONING,
    MAX_RETRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    RETRY_BASE_DELAY,
)


CHOICE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "choice",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "chosen_number": {
                    "type": "integer",
                    "description": "The number (1-4) of the chosen participant",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation for the choice (1-2 sentences)",
                },
            },
            "required": ["chosen_number", "reason"],
            "additionalProperties": False,
        },
    },
}

QWEN_STRUCTURED_SYS_PREFIX = 'Output valid JSON only. Format: {"chosen_number": N, "reason": "..."}\n\n'
QWEN_STRUCTURED_USER_SUFFIX = (
    '\n\nYou must respond ONLY with a JSON object: {"chosen_number": N, "reason": "brief reason"} '
    "where N is the participant number."
)


def _retry_delay(resp: aiohttp.ClientResponse | None, attempt: int) -> float:
    if resp is not None and resp.headers.get("Retry-After"):
        try:
            return float(resp.headers["Retry-After"])
        except ValueError:
            pass
    return RETRY_BASE_DELAY * (2 ** attempt)


class OpenRouterClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        concurrency: int,
        timeout_seconds: int = 120,
    ) -> None:
        self.session = session
        self.concurrency = concurrency
        self._model_semaphores: dict[str, asyncio.Semaphore] = {}
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    def _semaphore_for(self, model: str) -> asyncio.Semaphore:
        if model not in self._model_semaphores:
            self._model_semaphores[model] = asyncio.Semaphore(self.concurrency)
        return self._model_semaphores[model]

    async def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_mode: str = "text",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-safety-research.local",
            "X-Title": "AI Safety Bias Research",
        }

        is_reasoning = model in BENCH_REASONING
        is_qwen_structured = response_mode == "structured" and "qwen" in model.lower()
        default_max_tokens = (200 if is_qwen_structured else 2000) if response_mode == "structured" else (
            16000 if is_reasoning and "anthropic" in model else 500
        )
        default_temperature = 1.0 if is_reasoning and "anthropic" in model else 0.0
        system_content = self._system_prompt_for(model, system_prompt, response_mode)
        user_content = user_prompt
        if is_qwen_structured:
            system_content = QWEN_STRUCTURED_SYS_PREFIX + system_prompt
            user_content = user_prompt + QWEN_STRUCTURED_USER_SUFFIX

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens if max_tokens is not None else default_max_tokens,
            "temperature": temperature if temperature is not None else default_temperature,
        }
        if response_mode == "structured" and not is_qwen_structured:
            body["response_format"] = CHOICE_SCHEMA

        sem = self._semaphore_for(model)
        for attempt in range(MAX_RETRIES):
            retry_delay = 0.0
            async with sem:
                try:
                    async with self.session.post(
                        OPENROUTER_BASE_URL,
                        headers=headers,
                        json=body,
                        timeout=self.timeout,
                    ) as resp:
                        if resp.status == 429:
                            retry_delay = _retry_delay(resp, attempt)
                        elif resp.status != 200:
                            text = await resp.text()
                            if attempt < MAX_RETRIES - 1:
                                retry_delay = _retry_delay(resp, attempt)
                            else:
                                return {
                                    "success": False,
                                    "model": model,
                                    "error": f"HTTP {resp.status}: {text[:500]}",
                                    "raw_response": None,
                                }
                        else:
                            data = await resp.json()
                            content = ""
                            reasoning = ""
                            if data and data.get("choices"):
                                message = data["choices"][0].get("message", {})
                                content = message.get("content", "") or ""
                                reasoning = (
                                    message.get("reasoning", "")
                                    or message.get("reasoning_content", "")
                                    or ""
                                )

                            return {
                                "success": True,
                                "model": model,
                                "content": content,
                                "reasoning": reasoning,
                                "usage": data.get("usage", {}) if isinstance(data, dict) else {},
                                "raw_response": data,
                            }
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    if attempt < MAX_RETRIES - 1:
                        retry_delay = RETRY_BASE_DELAY * (2 ** attempt)
                    else:
                        return {
                            "success": False,
                            "model": model,
                            "error": str(exc),
                            "raw_response": None,
                        }
            # Sleep outside the semaphore so other models' requests can proceed
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)

        return {
            "success": False,
            "model": model,
            "error": "Max retries exceeded",
            "raw_response": None,
        }

    @staticmethod
    def _system_prompt_for(model: str, system_prompt: str, response_mode: str) -> str:
        return system_prompt
