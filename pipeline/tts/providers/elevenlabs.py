"""
ElevenLabs provider. Library-voice selection (LLM-assisted) + multi-speaker
dialogue API.

Voice design from prompt is documented as a prototyping feature with variable
quality; library voices are professionally trained and produce far better
output. We extract gender/age from the character's voice description, query
the shared voice library, and have an LLM pick the best match.

Voice control is via inline audio tags in the text itself ([laughs],
[sighs], [whispering], etc.) — translator-emitted tags pass through.
There is no per-utterance description or speed parameter; the model
reads the text and tags.
"""

import logging
import os
from typing import Literal

import instructor
import litellm
from elevenlabs import ElevenLabs
from elevenlabs.types import DialogueInput
from pydantic import BaseModel, Field

from .base import Utterance

log = logging.getLogger(__name__)


class _Filters(BaseModel):
    """Filter terms extracted from a character voice description."""
    gender: Literal["male", "female", "neutral"]
    age: Literal["young", "middle_aged", "old"]


class _Pick(BaseModel):
    voice_id: str
    reasoning: str = Field(description="Why this voice fits the character, 1–2 sentences.")


class ElevenLabsProvider:
    name = "elevenlabs"

    # Default model for text-to-dialogue. v3 is the expressive multi-speaker model.
    dialogue_model_id = "eleven_v3"

    # LLM used to extract filters and pick a voice from candidates.
    matching_model = "openai/gpt-5.5"

    def __init__(self, api_key: str | None = None):
        self.client = ElevenLabs(
            api_key=api_key or os.environ.get("ELEVENLABS_API_KEY")
                            or os.environ["ELEVEN_API_KEY"]
        )
        self._instructor = instructor.from_litellm(litellm.completion)

    def design_voice(
        self,
        description: str,
        name: str,
        sample_text: str,
        excluded_voice_ids: list[str] | None = None,
    ) -> str:
        """Library-voice selection.
        1. Extract gender/age from description via LLM.
        2. Query shared voice library with those filters.
        3. LLM picks best candidate (excluding any already-used voices).
        Returns: shared voice_id (usable directly in TTS / dialogue calls).
        """
        log.info(f"ElevenLabs.design_voice (library match): {name!r}")
        excluded = set(excluded_voice_ids or [])

        filters = self._extract_filters(description)
        log.info(f"  filters: gender={filters.gender}, age={filters.age}")

        # Try professional voices first (voice actors, studio-quality);
        # fall back to high_quality (curated) if pool is empty.
        candidates = []
        for category in ("professional", "high_quality"):
            resp = self.client.voices.get_shared(
                gender=filters.gender,
                age=filters.age,
                language="en",
                category=category,
                page_size=50,
            )
            candidates = [v for v in resp.voices if v.voice_id not in excluded]
            log.info(f"  category={category}: {len(candidates)} candidates (after excluding {len(excluded)} already-used)")
            if candidates:
                break

        if not candidates:
            raise RuntimeError(f"No library voices match filters for {name}")

        chosen_id = self._pick_voice(description, candidates)
        chosen = next((c for c in candidates if c.voice_id == chosen_id), candidates[0])
        log.info(f"  chose: {chosen.name} ({chosen.voice_id})")
        return chosen.voice_id

    def _extract_filters(self, description: str) -> _Filters:
        return self._instructor.create(
            model=self.matching_model,
            response_model=_Filters,
            messages=[
                {"role": "system", "content": (
                    "Extract demographic filters from a character voice description "
                    "for matching against ElevenLabs' voice library. Map the description "
                    "to gender (male/female/neutral) and age (young/middle_aged/old)."
                )},
                {"role": "user", "content": description},
            ],
            max_tokens=2000,
        )

    def _pick_voice(self, description: str, candidates) -> str:
        candidate_block = "\n".join(
            f"- voice_id={v.voice_id}\n  name={v.name}\n  description={v.description or ''}\n  "
            f"accent={v.accent or '?'}, descriptive={v.descriptive or '?'}, use_case={v.use_case or '?'}"
            for v in candidates
        )
        pick = self._instructor.create(
            model=self.matching_model,
            response_model=_Pick,
            messages=[
                {"role": "system", "content": (
                    "You are casting a voice for a character. Given the character's "
                    "voice description and a list of available library voices, pick "
                    "the one whose qualities best match. Reply with the chosen voice_id "
                    "(verbatim from the candidates) and 1–2 sentences of reasoning."
                )},
                {"role": "user", "content": (
                    f"# Character voice description\n{description}\n\n"
                    f"# Library candidates\n{candidate_block}"
                )},
            ],
            max_tokens=2000,
        )
        return pick.voice_id

    def synthesize(self, utterances: list[Utterance]) -> bytes:
        """Render via the text_to_dialogue endpoint. Returns WAV bytes.

        ElevenLabs has no per-utterance description/speed; all delivery
        control is in the text via audio tags. Description and speed
        from the annotation are ignored here (they shape Hume only).
        """
        log.info(f"ElevenLabs.synthesize: {len(utterances)} utterances")
        inputs = [
            DialogueInput(text=self._with_trailing_silence(u), voice_id=u.voice_id)
            for u in utterances
        ]
        chunks = self.client.text_to_dialogue.convert(
            inputs=inputs,
            model_id=self.dialogue_model_id,
            output_format="wav_48000",
        )
        return b"".join(chunks)

    @staticmethod
    def _with_trailing_silence(u: Utterance) -> str:
        """ElevenLabs has no per-utterance silence param; append [pause] tags.
        [long pause] is roughly ~1s; [pause] is shorter. Anything > 0.7s gets
        [long pause]; 0.2-0.7 gets [pause]; below that, leave it to the model.
        """
        s = u.trailing_silence_seconds or 0.0
        if s >= 0.7:
            return f"{u.text} [long pause]"
        if s >= 0.2:
            return f"{u.text} [pause]"
        return u.text
