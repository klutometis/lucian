"""
Build the reading: one-shot pre-pass over the source text producing a
director's brief — cast, register, running gags. The artifact flows
downstream into casting, translation, and annotation.

No schema. Model emits JSON. We save it.

Usage:
    uv run pipeline/bible/build_reading.py --work lucian-dialogues-of-the-dead
    uv run pipeline/bible/build_reading.py --model openai/gpt-5.5
"""

import argparse
import json
import logging
import re
from pathlib import Path

import litellm
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


SYSTEM = """You are an experienced theater director preparing to dramatize
a classical work as an audio production. You are reading the source text
once, end to end, and producing a director's brief that the rest of the
production team — translators, voice casters, line-by-line annotators —
will work from.

Your output is a single artifact called the reading. It is JSON.

What it must contain:
- A `work` object with at minimum: title, register_pitch (1–3 sentences
  defining the directorial register), running_gags (the recurring comedic
  structures), tone_anchors (short directorial reminders).
- A `cast` array. Each character has at minimum: id (lowercase ascii slug),
  name_grc, name_en, sketch (2–4 sentences naming dramatic function and
  the way they should sound), voice_description (specific and evocative —
  age, gender, register, accent, vocal qualities; this will be fed to a
  generative TTS model that designs voices from prompts).

Beyond the minimum, add whatever you want — fields you think a director
would brief the cast on. Don't pad; only add what's actually useful.

You are NOT producing a glossary, term commitments, or scholarly apparatus.
The translators will know what the words mean. Your job is performance brief.

The scene is the smallest unit anyone downstream works with — do not
break scenes into sub-structure.

Lean into the directorial register the user specifies. Make casting choices
that serve it.

Respond with ONLY the JSON object. No prose before or after.
"""

HUMAN = """## Work

- Title: {title}
- Author: {author}
- Language: {language}
- Genre: {genre}
- Directorial register: {register_hint}

## Source dialogues

{dialogues}

Produce the reading as JSON.
"""


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


def extract_json(text: str) -> dict:
    """Strip markdown fences if present, parse JSON."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def build(work_id: str, model: str) -> dict:
    work_dir = PROJECT_ROOT / "works" / work_id
    meta = yaml.safe_load((work_dir / "work.yaml").read_text())
    dialogues = json.loads((work_dir / "source" / "dialogues.json").read_text())

    log.info(f"Read {len(dialogues)} dialogues from {work_id}")
    log.info(f"Authoring reading with {model}...")

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": HUMAN.format(
                title=meta["title"],
                author=meta["author"],
                language=meta["language"],
                genre=meta["genre"],
                register_hint=meta.get("register_hint", "neutral"),
                dialogues=format_dialogues(dialogues),
            )},
        ],
        max_tokens=64000,
        temperature=0.4,
    )

    text = response.choices[0].message.content
    return extract_json(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--model", default="anthropic/claude-sonnet-4-6")
    args = ap.parse_args()

    reading = build(args.work, args.model)

    out_path = PROJECT_ROOT / "works" / args.work / "bible" / "reading.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(reading, ensure_ascii=False, indent=2))

    log.info(f"Wrote reading → {out_path}")
    work = reading.get("work", {})
    cast = reading.get("cast", [])
    log.info(f"  cast: {len(cast)} characters")
    print(f"\n  Title:           {work.get('title', '?')}")
    print(f"  Register pitch:  {work.get('register_pitch', '')[:200]}")


if __name__ == "__main__":
    main()
