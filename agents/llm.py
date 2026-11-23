"""LLM gateway: one place for the client, JSON-mode calls, validation and retry."""
import json
from typing import Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

import config

T = TypeVar("T", bound=BaseModel)
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def structured_call(system: str, user: str, schema: Type[T], client=None, max_retries: int = 2) -> T:
    """Ask the model for JSON, validate it with Pydantic, and retry with the error message if invalid."""
    client = client or get_client()
    messages = [
        {
            "role": "system",
            "content": system + "\n\nReturn ONLY a JSON object that matches this JSON schema:\n" + json.dumps(schema.model_json_schema()),
        },
        {"role": "user", "content": user},
    ]
    last_error = None
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=config.TEMPERATURE,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        try:
            return schema.model_validate_json(raw)
        except ValidationError as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": f"Your JSON was invalid: {e}. Return corrected JSON only."})
    raise ValueError(f"Model output failed validation after {max_retries + 1} attempts: {last_error}")
