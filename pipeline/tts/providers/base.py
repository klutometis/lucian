"""
Provider interface. Two responsibilities:
- design_voice: feed a voice description, save and return a persistent voice id
- synthesize: take a list of utterances (provider-shaped), return audio bytes
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Utterance:
    """Provider-agnostic utterance for synthesis."""
    voice_id: str
    text: str
    description: str | None = None
    speed: float = 1.0
    trailing_silence_seconds: float = 0.0


class Provider(Protocol):
    name: str

    def design_voice(self, description: str, name: str, sample_text: str) -> str:
        """Design and persist a voice from a text description.
        Returns a stable voice_id."""
        ...

    def synthesize(self, utterances: list[Utterance]) -> bytes:
        """Render all utterances in a single multi-speaker request.
        Returns audio bytes (WAV)."""
        ...
