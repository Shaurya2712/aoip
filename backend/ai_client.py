# STATUS: COMPLETE
# ai_client.py
import json
import asyncio
from google import genai
from google.genai import types
from config import (
    GEMINI_API_KEY,
    GEMMA_MODEL_BULK,
    GEMMA_MODEL_ANALYZE,
    GEMMA_MAX_OUTPUT_TOKENS,
)

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a JSON-only responder. "
    "Always return valid JSON. "
    "Never include markdown code fences, preamble, or explanation. "
    "Your entire response must be parseable by json.loads()."
)

_GENERATE_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    max_output_tokens=GEMMA_MAX_OUTPUT_TOKENS,
    temperature=0.2,
)


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _generate_sync(model_name: str, prompt: str) -> dict:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=_GENERATE_CONFIG,
    )
    return _parse_json_response(response.text)


async def ai_bulk(prompt: str) -> dict:
    """
    Fast bulk tasks: keyword expansion, trend scoring, opportunity scoring.
    Model: gemma-4-26b-a4b-it (Gemma 4 26B MoE, 256K context).
    Always returns parsed JSON dict.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _generate_sync(GEMMA_MODEL_BULK, prompt),
    )


async def ai_analyze(prompt: str) -> dict:
    """
    Detailed analysis: product concepts, review mining, community insights.
    Model: gemma-4-31b-it (Gemma 4 31B dense, 256K context).
    Always returns parsed JSON dict.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _generate_sync(GEMMA_MODEL_ANALYZE, prompt),
    )
