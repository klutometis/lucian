"""
Hume Octave provider. Voice design from prompt + multi-utterance synthesis.

Octave 1 is required for voice design and the per-utterance `description`
acting-instruction field. (Octave 2 lacks both as of early 2026.)
"""

import base64
import io
import logging
import os
import wave

from hume import HumeClient
from hume.tts.types import (
    FormatWav,
    PostedUtterance,
    PostedUtteranceVoiceWithId,
)

from .base import Utterance

log = logging.getLogger(__name__)


class HumeProvider:
    name = "hume"
    octave_version = "1"  # voice design + acting instructions require v1

    def __init__(self, api_key: str | None = None):
        self.client = HumeClient(api_key=api_key or os.environ["HUME_API_KEY"])

    def design_voice(self, description: str, name: str, sample_text: str) -> str:
        """Generate a voice from `description`, save it, return the voice id.

        Two API calls: (1) generate a candidate, (2) save it as a custom voice.
        """
        log.info(f"Hume.design_voice: {name!r}")
        gen = self.client.tts.synthesize_json(
            utterances=[
                PostedUtterance(text=sample_text, description=description),
            ],
            num_generations=1,
            version=self.octave_version,
        )
        generation = gen.generations[0]
        gen_id = generation.generation_id
        saved = self.client.tts.voices.create(generation_id=gen_id, name=name)
        log.info(f"  saved voice id={saved.id}")
        return saved.id

    def synthesize(self, utterances: list[Utterance]) -> bytes:
        """Render all utterances in one multi-speaker request, return WAV bytes."""
        log.info(f"Hume.synthesize: {len(utterances)} utterances")
        posted = [
            PostedUtterance(
                text=u.text,
                description=u.description,
                speed=u.speed,
                voice=PostedUtteranceVoiceWithId(id=u.voice_id),
            )
            for u in utterances
        ]
        result = self.client.tts.synthesize_json(
            utterances=posted,
            num_generations=1,
            version=self.octave_version,
            format=FormatWav(),
        )
        # Multi-utterance request returns one generation with all utterances
        # rendered into one continuous WAV.
        return base64.b64decode(result.generations[0].audio)
