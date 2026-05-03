"""
TTS annotation pipeline.

Pass 1: Performance Bible — one call over the full dialogue, produces
        director's notes and character profiles.

Pass 2: Line-Level Annotation — one call per dialogue, annotates each
        line with emotion, speed, volume, pause_before_ms, pause_after_ms.
"""

import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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


class CharacterProfile(BaseModel):
    name: str
    dramatic_function: str
    voice_name: str = Field(description="One of: Leo, Jace, Kyle, Gavin, Maya, Tessa, Dana, Marian")
    voice_id: str = ""
    emotion_palette: list[str] = Field(description="2–4 Cartesia emotion tags that suit this character")
    typical_speed: float = Field(description="Base speed ratio 0.8–1.4")
    register_notes: str


class PerformanceBible(BaseModel):
    characters: list[CharacterProfile]
    narrative_arc: str
    tempo_envelope: str = Field(description="Overall pacing description for this dialogue")
    dominant_emotion: str
    key_beats: list[str]
    directorial_notes: str


class AnnotatedLine(BaseModel):
    line_index: int
    speaker: str
    text: str = Field(description="Text with inline Cartesia SSML tags")
    emotion: str
    speed: float = Field(ge=0.6, le=1.5)
    volume: float = Field(ge=0.5, le=2.0)
    pause_before_ms: int = Field(ge=0, le=3000)
    pause_after_ms: int = Field(ge=0, le=3000)


class DialogueAnnotation(BaseModel):
    lines: list[AnnotatedLine]
    notes: str = ""


# ---------------------------------------------------------------------------
# Pass 1: Performance Bible
# ---------------------------------------------------------------------------

BIBLE_SYSTEM = """You are a director preparing to dramatize Lucian's *Dialogues of the Dead*
as an audio production using AI text-to-speech (Cartesia Sonic-3).

The style is **sitcom register** — fast, punchy, contemporary American English.
Characters are:
- Menippus: Zen, dry, annoyingly unruffled. Speed ~1.2. Emotions: content, sarcastic.
- Charon: Petty DMV-clerk bureaucrat. Speed ~1.15. Emotions: frustrated, agitated, tired.
- Hermes: George Costanza — perpetually aggrieved. Speed ~1.25. Emotions: tired, frustrated, exasperated.
- Diogenes: Cheerfully contemptuous. Speed ~1.1. Emotions: joking/comedic, contempt.
- Pluto: Middle management, wants no drama. Speed ~1.0. Emotions: calm, neutral.
- Wealthy shades (Croesus, Midas, etc.): Insufferable, still mourning. Speed ~0.95. Emotions: melancholic, contempt.
- Philosophers: Pompous then deflated. Speed ~1.1 → 0.9. Emotions: confident → dejected.

Available voices (emotive): Leo, Jace, Kyle, Gavin, Maya, Tessa, Dana, Marian.
Assign a distinct voice to each character. Keep assignments consistent across dialogues.

Respond with valid JSON matching the schema.
"""

BIBLE_HUMAN = """## Dialogue {dialogue_id}: {title}

{translated_lines}

{format_instructions}
"""


def build_performance_bible(
    dialogue_id: int,
    title: str,
    translated_lines: list[dict],
    model_name: str = "gpt-4o",
) -> PerformanceBible:
    model = ChatOpenAI(model=model_name, temperature=0.2)
    parser = PydanticOutputParser(pydantic_object=PerformanceBible)

    prompt = ChatPromptTemplate.from_messages([
        ("system", BIBLE_SYSTEM),
        ("human", BIBLE_HUMAN),
    ])
    chain = prompt | model | parser

    lines_str = "\n".join(
        f"{l.get('speaker', '?')}: {l.get('text', '')}" for l in translated_lines
    )

    bible = chain.invoke({
        "dialogue_id": dialogue_id,
        "title": title,
        "translated_lines": lines_str,
        "format_instructions": parser.get_format_instructions(),
    })

    # Resolve voice IDs
    for char in bible.characters:
        char.voice_id = CARTESIA_VOICES.get(char.voice_name, "")

    return bible


# ---------------------------------------------------------------------------
# Pass 2: Line-Level Annotation
# ---------------------------------------------------------------------------

ANNOTATION_SYSTEM = """You are annotating dialogue lines for Cartesia Sonic-3 TTS production.

## Performance Bible
{bible}

## Cartesia Emotion Tags (use these exactly)
Primary: neutral, angry, excited, content, sad, scared
Extended: happy, enthusiastic, elated, triumphant, amazed, surprised,
flirtatious, joking/comedic, curious, peaceful, serene, calm,
grateful, affectionate, sympathetic, anticipation, mysterious,
mad, outraged, frustrated, agitated, threatened, disgusted, contempt,
envious, sarcastic, ironic, dejected, melancholic, disappointed, hurt,
guilty, bored, tired, rejected, nostalgic, wistful, apologetic,
hesitant, insecure, confused, resigned, anxious, panicked, alarmed,
proud, confident, distant, skeptical, contemplative, determined

## SSML inline tags (embed in text field)
<emotion value="joking/comedic"/> text here
<speed ratio="1.25"/> text
<volume ratio="1.5"/> text
[laughter] anywhere in text

## Rules
- Annotate all four dimensions simultaneously (emotion, speed, volume, pauses)
- Pauses: interruption = <50ms, normal response = 100-200ms, dramatic beat = 300-800ms
- Scene register is SITCOM: default speed ~1.2, tight gaps, comedic emotion
- Embed one <emotion> tag at the start of each text line
- Respond with valid JSON matching the schema
"""

ANNOTATION_HUMAN = """## Dialogue {dialogue_id}: {title}

### Previous dialogue's last lines (context):
{prev_lines}

### Translate and annotate these lines:
{lines}

### Next dialogue's first lines (resolution):
{next_lines}

{format_instructions}
"""


def annotate_dialogue(
    dialogue_id: int,
    title: str,
    translated_lines: list[dict],
    bible: PerformanceBible,
    prev_lines: list[dict] | None = None,
    next_lines: list[dict] | None = None,
    model_name: str = "gpt-4o",
) -> DialogueAnnotation:
    model = ChatOpenAI(model=model_name, temperature=0.1)
    parser = PydanticOutputParser(pydantic_object=DialogueAnnotation)

    prompt = ChatPromptTemplate.from_messages([
        ("system", ANNOTATION_SYSTEM),
        ("human", ANNOTATION_HUMAN),
    ])
    chain = prompt | model | parser

    def fmt(lines):
        if not lines:
            return "None"
        return "\n".join(f"{l.get('speaker','?')}: {l.get('text','')}" for l in lines)

    indexed = [{"line_index": i, **l} for i, l in enumerate(translated_lines)]
    lines_str = "\n".join(
        f"[{l['line_index']}] {l.get('speaker','?')}: {l.get('text','')}"
        for l in indexed
    )

    return chain.invoke({
        "dialogue_id": dialogue_id,
        "title": title,
        "bible": bible.model_dump_json(indent=2),
        "prev_lines": fmt(prev_lines or []),
        "lines": lines_str,
        "next_lines": fmt(next_lines or []),
        "format_instructions": parser.get_format_instructions(),
    })
