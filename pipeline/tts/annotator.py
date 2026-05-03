"""
Per-line annotation. Reads the reading + a translation; emits per-line
voice/text/pacing data for the stitcher.

Currently emits Cartesia-shaped fields (emotion, speed, volume, pauses).
Hume provider with natural-language acting instructions to come later.
"""

from pydantic import BaseModel, ConfigDict, Field
import instructor
import litellm


# Cartesia emotive voice library (current default provider)
CARTESIA_VOICES = {
    "Leo":    "0834f3df-e650-4766-a20c-5a93a43aa6e3",
    "Jace":   "6776173b-fd72-460d-89b3-d85812ee518d",
    "Kyle":   "c961b81c-a935-4c17-bfb3-ba2239de8c2f",
    "Gavin":  "f4a3a8e4-694c-4c45-9ca0-27caf97901b5",
    "Maya":   "cbaf8084-f009-4838-a096-07ee2e6612b1",
    "Tessa":  "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",
    "Dana":   "cc00e582-ed66-4004-8336-0175b85c85f6",
    "Marian": "26403c37-80c1-4a1a-8692-540551ca2ae5",
}


class AnnotatedLine(BaseModel):
    """One annotated line. Required: stitcher-consumed fields. Extras allowed."""
    model_config = ConfigDict(extra="allow")
    speaker: str
    text: str = Field(description="Text with optional inline Cartesia SSML tags")
    voice_name: str = Field(description="One of the Cartesia voice names")
    emotion: str
    speed: float = Field(ge=0.6, le=1.5)
    volume: float = Field(ge=0.5, le=2.0)
    pause_before_ms: int = Field(ge=0, le=3000)
    pause_after_ms: int = Field(ge=0, le=3000)


class Annotation(BaseModel):
    """Per-dialogue annotation. Required: lines. Extras allowed."""
    model_config = ConfigDict(extra="allow")
    lines: list[AnnotatedLine]


SYSTEM_TEMPLATE = """You are annotating dialogue lines for Cartesia Sonic-3 TTS.

# The reading (your director's brief)

Register: {register_pitch}

Cast (each character has a voice description; use it to choose voice + delivery):
{cast_block}

Tone anchors:
{tone_block}

# Casting

Map each character to one of these Cartesia voices: {voice_names}.
Be consistent: the same character gets the same voice across the dialogue.

# Cartesia emotion vocabulary

Primary: neutral, angry, excited, content, sad, scared
Extended: joking/comedic, sarcastic, ironic, contempt, frustrated, agitated,
tired, melancholic, dejected, hurt, nostalgic, wistful, hesitant, anxious,
proud, confident, contemplative, determined, curious, sympathetic, amused,
calm, peaceful, serene, triumphant, surprised, disappointed, bored, resigned

# Pauses (milliseconds)

Interruption: 0–50. Normal response: 100–200. Dramatic beat: 300–800.

# Output

Per line: speaker, text, voice_name (from the list), emotion (from vocab),
speed (0.6–1.5), volume (0.5–2.0), pause_before_ms, pause_after_ms.
You may add extra fields (a directorial note, a stage direction) per line.
"""


def build_system(reading: dict) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])

    cast_lines = []
    for c in cast:
        cast_lines.append(
            f"- {c.get('name_en', '?')}: {c.get('voice_description', '')}"
        )
    cast_block = "\n".join(cast_lines) if cast_lines else "(none)"

    tone = work.get("tone_anchors", [])
    tone_block = "\n".join(f"- {t}" for t in tone) if tone else "(none)"

    return SYSTEM_TEMPLATE.format(
        register_pitch=work.get("register_pitch", ""),
        cast_block=cast_block,
        tone_block=tone_block,
        voice_names=", ".join(CARTESIA_VOICES.keys()),
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
