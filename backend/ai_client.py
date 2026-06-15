# STATUS: COMPLETE
# ai_client.py
import json
import asyncio
import re
import time
import threading
from google import genai
from google.genai import types
from config import (
    GEMINI_API_KEY,
    GEMMA_MODEL_BULK,
    GEMMA_MODEL_ANALYZE,
    GEMMA_MAX_OUTPUT_TOKENS_BULK,
    GEMMA_MAX_OUTPUT_TOKENS_ANALYZE,
    AI_REQUESTS_PER_MINUTE,
)

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a JSON-only responder. "
    "Always return valid JSON. "
    "Never include markdown code fences, preamble, or explanation. "
    "Your entire response must be parseable by json.loads()."
)

_MAX_RETRIES = 4
_RETRYABLE_MARKERS = ("500", "503", "429", "INTERNAL", "UNAVAILABLE", "RESOURCE_EXHAUSTED")

_rate_lock = threading.Lock()
_request_timestamps: list[float] = []


def _parse_json_response(raw: str | None) -> dict:
    if not raw:
        raise ValueError("AI returned empty response (no text)")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).upper()
    return any(marker in msg for marker in _RETRYABLE_MARKERS)


def _extract_retry_seconds(exc: Exception) -> float | None:
    """Parse Google's suggested retry delay from 429 responses."""
    msg = str(exc)
    m = re.search(r"retry in ([\d.]+)s", msg, re.I)
    if m:
        return float(m.group(1)) + 1.0
    m = re.search(r'"retryDelay":\s*"(\d+)s"', msg)
    if m:
        return float(m.group(1)) + 1.0
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return 60.0
    return None


def _wait_for_rate_limit():
    """Enforce max requests per minute (Gemma free tier: 15 RPM)."""
    min_gap = 60.0 / max(AI_REQUESTS_PER_MINUTE, 1)
    with _rate_lock:
        now = time.time()
        _request_timestamps[:] = [t for t in _request_timestamps if now - t < 60.0]
        if len(_request_timestamps) >= AI_REQUESTS_PER_MINUTE:
            wait = (_request_timestamps[0] + 60.0) - now
            if wait > 0:
                time.sleep(wait)
            now = time.time()
            _request_timestamps[:] = [t for t in _request_timestamps if now - t < 60.0]
        _request_timestamps.append(time.time())
    time.sleep(min_gap)


def _generate_sync(model_name: str, prompt: str, max_output_tokens: int) -> dict:
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        max_output_tokens=max_output_tokens,
        temperature=0.2,
        response_mime_type="application/json",
    )
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        _wait_for_rate_limit()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return _parse_json_response(response.text)
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1 and _is_retryable(e):
                delay = _extract_retry_seconds(e) or (2 ** attempt)
                time.sleep(delay)
                continue
            raise
    raise last_exc  # unreachable


async def _run_generate(model_name: str, prompt: str, max_output_tokens: int) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _generate_sync(model_name, prompt, max_output_tokens),
    )


async def ai_bulk(prompt: str) -> dict:
    """
    Fast bulk tasks: keyword expansion, trend scoring, opportunity scoring.
    Rate-limited to stay within Gemini/Gemma free-tier RPM.
    """
    return await _run_generate(GEMMA_MODEL_BULK, prompt, GEMMA_MAX_OUTPUT_TOKENS_BULK)


async def ai_analyze(prompt: str) -> dict:
    """
    Detailed analysis: product concepts, review mining, community insights.
    Rate-limited to stay within Gemini/Gemma free-tier RPM.
    """
    return await _run_generate(GEMMA_MODEL_ANALYZE, prompt, GEMMA_MAX_OUTPUT_TOKENS_ANALYZE)
