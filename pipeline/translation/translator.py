"""
Translator: Instructor + LiteLLM. Multi-provider via litellm model strings
("openai/gpt-5.5", "anthropic/claude-sonnet-4-6", "gemini/gemini-3.1-pro-preview",
"xai/grok-4.3"). Required schema is minimal; model can add any extra fields.
"""

import logging
from pydantic import BaseModel, ConfigDict
import instructor
import litellm

log = logging.getLogger(__name__)


class Line(BaseModel):
    """One translated line. Required: speaker, text. Model may add more."""
    model_config = ConfigDict(extra="allow")
    speaker: str
    text: str


class Translation(BaseModel):
    """A translated dialogue. Required: lines. Model may add notes,
    directorial asides, anything else useful."""
    model_config = ConfigDict(extra="allow")
    lines: list[Line]


def translate(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 32000,
    temperature: float | None = None,
) -> Translation:
    """Translate via instructor + litellm; return Translation pydantic model.
    Temperature omitted by default (some reasoning models reject custom values)."""
    client = instructor.from_litellm(litellm.completion)
    kwargs = dict(
        model=model,
        response_model=Translation,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
    if temperature is not None:
        kwargs["temperature"] = temperature
    return client.create(**kwargs)
