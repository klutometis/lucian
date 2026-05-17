"""
Build the episode manifest: one LLM call over the reading + all 30
translations → 30 entries of {episode_number, audio_file, title,
description, artwork_description}.

Usage:
    uv run pipeline/distribution/build_manifest.py
    uv run pipeline/distribution/build_manifest.py --translation-model anthropic/claude-opus-4-7
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import instructor
import litellm
import yaml
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Episode(BaseModel):
    episode_number: int
    title: str = Field(description="Punchy episode title, ~3-7 words. No 'Ep. N' prefix.")
    description: str = Field(
        description="Podcast episode description, 3-5 sentences. "
                    "Captures the premise + a few specific scene beats. "
                    "Ends with cast list (e.g. 'Cast: X, Y, Z.')."
    )
    artwork_description: str = Field(
        description="A specific visual prompt for the episode artwork. "
                    "Square frame. Describes characters present (using their "
                    "appearance from the reading), staging, lighting, mood. "
                    "Builds on the show's visual world (dark stone columns, "
                    "torchlit underworld, deadpan-comic painterly oil style). "
                    "Strong central composition that reads at thumbnail size."
    )


class Manifest(BaseModel):
    episodes: list[Episode]


SYSTEM = """You are writing podcast episode metadata for a 30-episode audio
adaptation of Lucian's *Dialogues of the Dead*. The register is deadpan
underworld sitcom — see the reading below for tone anchors.

For each of the 30 dialogues, produce:
- A punchy episode title (3-7 words; no "Ep. N" prefix, Buzzsprout has a
  separate episode-number field).
- A 3-5 sentence description capturing the premise and a few specific
  beats. End with "Cast: X, Y, Z." listing the named speakers.
- An artwork description: a specific visual prompt for square episode
  art that builds on the show's visual world (painterly digital oil
  painting; dark stone columns; warm torch-light against deep navy;
  the scrappy Cynic dog with brass-lantern collar from the show cover
  often visible somewhere in frame). Be specific about characters
  present (use their appearance from the reading), framing, lighting.

Tone: dry, contemporary, sitcom-y but not jokey. Don't oversell.
"""

HUMAN_TEMPLATE = """# The reading (director's brief)

{reading_block}

# The 30 translated dialogues

{translations_block}

Produce the manifest: one entry per dialogue, ordered 1 through 30.
"""


def safe_id(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def format_reading(reading: dict) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])
    parts = [
        f"## Title: {work.get('title', '')}",
        f"\n## Register pitch\n{work.get('register_pitch', '')}",
        "\n## Running gags",
        *[f"- {g}" for g in work.get("running_gags", [])],
        "\n## Tone anchors",
        *[f"- {t}" for t in work.get("tone_anchors", [])],
        "\n## Cast (with appearance)",
    ]
    for c in cast:
        parts.append(f"- [{c.get('id','?')}] {c.get('name_en','?')}: {c.get('sketch','')}")
        vd = c.get("voice_description")
        if vd:
            parts.append(f"    voice/appearance: {vd}")
    return "\n".join(parts)


def format_translations(work_dir: Path, model: str) -> str:
    parts = []
    safe = safe_id(model)
    for d in sorted((work_dir / "output" / "translations").glob(f"dialogue_*_{safe}.json")):
        data = json.loads(d.read_text())
        dialogue_id = int(d.stem.split("_")[1])
        parts.append(f"## Dialogue {dialogue_id}")
        for line in data["lines"]:
            parts.append(f"  {line['speaker']}: {line['text']}")
        parts.append("")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--translation-model", default="anthropic/claude-opus-4-7")
    ap.add_argument("--llm", default="anthropic/claude-opus-4-7",
                    help="Model that writes the metadata")
    ap.add_argument("--out", type=Path,
                    default=PROJECT_ROOT / "works/lucian-dialogues-of-the-dead/output/episode_manifest.json")
    args = ap.parse_args()

    work_dir = PROJECT_ROOT / "works" / args.work
    reading = json.loads((work_dir / "bible" / "reading.json").read_text())
    reading_block = format_reading(reading)
    translations_block = format_translations(work_dir, args.translation_model)
    user = HUMAN_TEMPLATE.format(
        reading_block=reading_block,
        translations_block=translations_block,
    )

    log.info(f"calling {args.llm}...")
    client = instructor.from_litellm(litellm.completion)
    manifest = client.create(
        model=args.llm,
        response_model=Manifest,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=32000,
    )

    # Bolt on audio_file paths so the batch uploader has everything it needs
    audio_dir = work_dir / "output" / "audio"
    safe_tm = safe_id(args.translation_model)
    entries = []
    for ep in sorted(manifest.episodes, key=lambda e: e.episode_number):
        audio = audio_dir / f"dialogue_{ep.episode_number:02d}_{safe_tm}_hume.wav"
        entries.append({
            "episode_number": ep.episode_number,
            "audio_file": str(audio.relative_to(PROJECT_ROOT)),
            "title": ep.title,
            "description": ep.description,
            "artwork_description": ep.artwork_description,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    log.info(f"wrote {len(entries)} entries → {args.out}")


if __name__ == "__main__":
    main()
