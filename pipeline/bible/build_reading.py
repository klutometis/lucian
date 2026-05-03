"""
Build the reading: one-shot pre-pass over the source text producing
a director's brief — cast, register, running gags.

The reading is the central artifact that flows downstream into casting,
translation, and annotation. See plans/03-global-artifacts.md.

Usage:
    uv run pipeline/bible/build_reading.py --work lucian-dialogues-of-the-dead
    uv run pipeline/bible/build_reading.py --model gpt-5.5
"""

import argparse
import json
import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class Work(BaseModel):
    title: str
    register_pitch: str = Field(description="The directorial register in 1–3 sentences.")
    running_gags: list[str] = Field(description="Recurring comedic structures across the work.")
    tone_anchors: list[str] = Field(description="Short directorial reminders about tone.")


class Character(BaseModel):
    id: str = Field(description="Lowercase ascii identifier, e.g. 'menippus'")
    name_grc: str = Field(description="Greek form")
    name_en: str = Field(description="Standard English form")
    sketch: str = Field(description="2–4 sentences. Dramatic function and personality.")
    voice_description: str = Field(
        description="Natural-language voice spec suitable as a Hume Octave prompt. "
                    "Age, gender, register, accent, vocal qualities."
    )
    register_notes: str = Field(description="Pace + emotional default, e.g. 'deadpan, ~1.1 speed'")
    emotion_default: str


class Reading(BaseModel):
    work: Work
    cast: list[Character]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM = """You are an experienced theater director preparing to dramatize a
classical work as an audio production. You are reading the source text once,
end to end, and producing a director's brief that the rest of the production
team — translators, voice casters, line-by-line annotators — will work from.

Your output is a single artifact called "the reading."

Your job is to make the work LEGIBLE as performance. That means:
- Identifying the recurring cast and giving each member a 2–4 sentence sketch
  that names their dramatic function and the way they should sound.
- Writing each character's voice description as if you were briefing a casting
  director: age, gender, register, accent, vocal qualities. These descriptions
  will be fed directly into a generative TTS model that designs voices from
  prompts, so be specific and evocative.
- Identifying the running gags and tonal anchors that hold across scenes.

The scene is the smallest unit anyone downstream works with; do not
break scenes into sub-structure.

You are NOT producing a glossary, term commitments, or scholarly apparatus.
The translators will know what the words mean. Your job is performance brief.

Lean into the directorial register the user specifies. If they say "sitcom,"
think character voices and comedic timing — not literal
fidelity. Make casting choices that serve the register.
"""

HUMAN = """## Work

- Title: {title}
- Author: {author}
- Language: {language}
- Genre: {genre}
- Directorial register: {register_hint}

## Source dialogues (Greek with structured speakers)

{dialogues}

Produce the reading.
"""


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def make_model(name: str):
    # Reading output for Lucian's full 30 dialogues runs ~30K+ tokens.
    # Use the model's max output budget.
    if name.startswith("gpt"):
        return ChatOpenAI(model=name, temperature=0.4, max_completion_tokens=128000)
    if name.startswith("claude"):
        return ChatAnthropic(model=name, temperature=0.4, max_tokens=64000)
    raise ValueError(f"Unsupported model for reading: {name}")


def format_dialogues(dialogues: list[dict]) -> str:
    parts = []
    for d in dialogues:
        parts.append(f"### Dialogue {d['id']}: {d['title']}")
        parts.append(f"Speakers: {', '.join(d['speakers'])}")
        parts.append("")
        for i, line in enumerate(d["lines"]):
            parts.append(f"  [{i}] {line['speaker']}: {line['text']}")
        parts.append("")
    return "\n".join(parts)


def build(work_id: str, model_name: str) -> Reading:
    work_dir = PROJECT_ROOT / "works" / work_id
    meta = yaml.safe_load((work_dir / "work.yaml").read_text())
    dialogues = json.loads((work_dir / "source" / "dialogues.json").read_text())

    log.info(f"Read {len(dialogues)} dialogues from {work_id}")
    log.info(f"Authoring reading with {model_name}...")

    model = make_model(model_name).with_structured_output(Reading)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])
    chain = prompt | model

    return chain.invoke({
        "title": meta["title"],
        "author": meta["author"],
        "language": meta["language"],
        "genre": meta["genre"],
        "register_hint": meta.get("register_hint", "neutral"),
        "dialogues": format_dialogues(dialogues),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="lucian-dialogues-of-the-dead")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    reading = build(args.work, args.model)

    out_path = PROJECT_ROOT / "works" / args.work / "bible" / "reading.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(reading.model_dump_json(indent=2))

    log.info(f"Wrote reading → {out_path}")
    log.info(f"  cast: {len(reading.cast)} characters")
    print(f"\n{'='*60}\nWORK\n{'='*60}")
    print(f"  Title:           {reading.work.title}")
    print(f"  Register pitch:  {reading.work.register_pitch}")
    print(f"\n  Running gags:")
    for g in reading.work.running_gags:
        print(f"    - {g}")
    print(f"\n  Tone anchors:")
    for t in reading.work.tone_anchors:
        print(f"    - {t}")
    print(f"\n{'='*60}\nCAST ({len(reading.cast)})\n{'='*60}")
    for char in reading.cast:
        print(f"\n  [{char.id}] {char.name_en} ({char.name_grc})")
        print(f"    Sketch:  {char.sketch}")
        print(f"    Voice:   {char.voice_description}")
        print(f"    Register: {char.register_notes}")
        print(f"    Default emotion: {char.emotion_default}")


if __name__ == "__main__":
    main()
