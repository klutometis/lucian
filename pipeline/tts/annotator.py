"""
Per-line annotation, provider-agnostic.

Reads the reading + a translated dialogue; emits per-line shape that
maps cleanly onto Hume / ElevenLabs / etc.:

  speaker, text, description, speed, pause_before_ms, pause_after_ms

The text passes through with whatever inline tags the translator inserted
([laughs], [sighs], [pause], etc.). Each provider decides how to handle them.
"""

from pydantic import BaseModel, ConfigDict, Field
import instructor
import litellm


class AnnotatedLine(BaseModel):
    """Provider-agnostic line. Required: stitcher inputs. Extras allowed."""
    model_config = ConfigDict(extra="allow")
    character_id: str = Field(
        description="The cast id from the reading (e.g. 'menippos', 'plouton'). "
                    "This is what the renderer uses to look up the voice."
    )
    speaker: str = Field(description="Human-readable name as used in the translation.")
    text: str
    description: str = Field(
        description="Natural-language acting instruction, ≤100 chars. "
                    "Examples: 'weary sarcasm', 'frightened, rushed', "
                    "'cheerful but cutting'."
    )
    speed: float = Field(ge=0.5, le=2.0, default=1.0)
    trailing_silence_seconds: float = Field(
        ge=0.0, le=3.0, default=0.0,
        description="Explicit pause AFTER this line, in seconds. Use only "
                    "for dramatic beats the model wouldn't insert naturally. "
                    "Most lines should be 0 (let the model handle pacing). "
                    "Comedic beats: 0.3-0.7. Dramatic landings: 0.8-1.5."
    )


class Annotation(BaseModel):
    """Per-dialogue annotation. Required: lines. Extras allowed."""
    model_config = ConfigDict(extra="allow")
    lines: list[AnnotatedLine]


SYSTEM_TEMPLATE = """You are a director annotating a translated scene for
expressive TTS. Your job is to write per-line acting instructions and
pacing.

# The reading (your director's brief)

Register: {register_pitch}

Cast (each character has a sketch and a voice description; use the sketch
to decide HOW each line should be delivered. Use the bracketed `id` as
`character_id` per line — it's how the renderer looks up the voice):
{cast_block}

Tone anchors:
{tone_block}

# Output per line

- character_id: the bracketed `id` from the cast list above (e.g. menippos,
  plouton). Resolve aliases (Pluto / Hades / Plouton all → plouton).
- speaker: as in the translation (human-readable name).
- text: copy from the translation, including any inline tags ([laughs],
  [pause], etc.). Don't add or remove tags.
- description: ≤100 chars, natural language acting note. Be specific to
  THIS line in context. Examples:
    "weary sarcasm, slight smile under the surface"
    "frustrated, picking up speed"
    "cheerful, completely at ease — Menippus default"
    "deadpan, very dry"
    "indignant, genuinely scandalized"
- speed: 0.5–2.0. 1.0 is normal pace. Only deviate when delivery genuinely
  calls for it.

Inter-line pacing is mostly handled by the TTS model in multi-utterance
mode — don't add silence for normal turn-taking. But comic timing often
benefits from a deliberate beat the model wouldn't insert on its own.
Use `trailing_silence_seconds` SPARINGLY for these moments:
- after a punchline, to let it land
- before a one-liner that's a delayed reaction
- at the end of a beat-defining sentence
Most lines should have 0 (the default). When you do use it, 0.3-0.7
is a comedic beat; 0.8-1.5 is a dramatic landing.

You may add extra fields per line (e.g. `note`, `stage_business`) where
useful, but don't pad. The description does most of the work."""


def build_system(reading: dict) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])

    cast_lines = []
    for c in cast:
        cast_lines.append(
            f"- [{c.get('id', '?')}] {c.get('name_en', '?')}: {c.get('sketch', '')}"
        )
    cast_block = "\n".join(cast_lines) if cast_lines else "(none)"

    tone = work.get("tone_anchors", [])
    tone_block = "\n".join(f"- {t}" for t in tone) if tone else "(none)"

    return SYSTEM_TEMPLATE.format(
        register_pitch=work.get("register_pitch", ""),
        cast_block=cast_block,
        tone_block=tone_block,
    )


def annotate(
    *,
    model: str,
    reading: dict,
    dialogue_id: int,
    title: str,
    translated_lines: list[dict],
    max_tokens: int = 16000,
) -> Annotation:
    system = build_system(reading)
    user = f"## Dialogue {dialogue_id}: {title}\n\n"
    user += "\n".join(
        f"[{i}] {l.get('speaker','?')}: {l.get('text','')}"
        for i, l in enumerate(translated_lines)
    )

    client = instructor.from_litellm(litellm.completion)
    return client.create(
        model=model,
        response_model=Annotation,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
