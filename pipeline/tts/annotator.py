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
    speaker: str
    text: str
    description: str = Field(
        description="Natural-language acting instruction, ≤100 chars. "
                    "Examples: 'weary sarcasm', 'frightened, rushed', "
                    "'cheerful but cutting'."
    )
    speed: float = Field(ge=0.5, le=2.0, default=1.0)


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
to decide HOW each line should be delivered):
{cast_block}

Tone anchors:
{tone_block}

# Output per line

- speaker: as in the translation
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

Inter-line pacing is handled by the TTS model in multi-utterance mode —
you don't need to think about pauses between lines. If a particular
line needs an explicit dramatic beat baked into it, use [pause] or
[long pause] inline within `text`.

You may add extra fields per line (e.g. `note`, `stage_business`) where
useful, but don't pad. The description does most of the work."""


def build_system(reading: dict) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])

    cast_lines = []
    for c in cast:
        cast_lines.append(
            f"- {c.get('name_en', '?')}: {c.get('sketch', '')}"
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
