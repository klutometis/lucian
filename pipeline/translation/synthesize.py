"""
Synthesis pass: given N existing translations of one dialogue, ask a model
to produce an editorial paraphrase that picks the sharpest version of each
move (or writes a fifth phrasing where none of the inputs lands).

NOT averaging. NOT consensus. Editing.

Output filename: dialogue_NN_synth-<model>.json
(uses the existing translation-dir naming so render.py can consume it via
--translation-model synth/<model>).

Usage:
    uv run pipeline/translation/synthesize.py --dialogue 2
    uv run pipeline/translation/synthesize.py --dialogue 2 --synth-model openai/gpt-5.5
    uv run pipeline/translation/synthesize.py --dialogue 2 --all-models
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translator import translate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_MODELS = [
    "openai/gpt-5.5",
    "anthropic/claude-sonnet-4-6",
    "gemini/gemini-3.1-pro-preview",
    "xai/grok-4.3",
]


def safe_id(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


SYSTEM = """You are editing a translation of one scene of Lucian's Dialogues
of the Dead. Four other translators have produced their takes. You are
reading all four and writing the canonical paraphrase.

# This is editorial work, not averaging.

For each line:
- Identify the sharpest version of the move — the most landed punchline,
  the cleanest character voice, the most apt register.
- If one of the four nails it, take that phrasing verbatim.
- If none of the four lands it but you can see what was needed, write the
  fifth version.
- Drop softeners ("anymore", "simply", "rather") unless they're load-bearing.
- Prefer parallel constructions over verbose alternation
  ("move him, or we move" beats "either move him somewhere else or we're relocating").
- Trust the model's register pitch (sitcom, deadpan, contemporary). Don't
  hedge toward formality.

# Commit to ONE consistent voice per character across the scene.

Don't cherry-pick GPT's clipped register for one line and Claude's theatrical
register for the next — the character will sound schizophrenic. Pick a voice
for each character and hold it.

# Inline performance tags

You may carry forward [laughs] / [sighs] / [pause] / [long pause] tags from
the source translations, or add your own where the timing benefits. Sparing
use only.

# The director's brief (reading)

Register: {register_pitch}

Cast (each with sketch):
{cast_block}

Tone anchors:
{tone_block}
"""

HUMAN = """## Dialogue {dialogue_id}: {title}

Speakers: {speakers}

## The four translations to synthesize

{translations_block}

Produce the editorial paraphrase as a list of `lines`, each with `speaker`
and `text`. Same shape as the inputs.
"""


def load_translations(work_dir: Path, dialogue_id: int, source_models: list[str]) -> dict:
    out = {}
    for m in source_models:
        path = work_dir / "output" / "translations" / f"dialogue_{dialogue_id:02d}_{safe_id(m)}.json"
        if not path.exists():
            log.warning(f"  missing translation: {path.name}")
            continue
        out[m] = json.loads(path.read_text())
    return out


def format_translations(translations: dict) -> str:
    parts = []
    for model, data in translations.items():
        parts.append(f"### {model}")
        for line in data["lines"]:
            parts.append(f"  {line['speaker']}: {line['text']}")
        parts.append("")
    return "\n".join(parts)


def build_system(reading: dict) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])
    cast_block = "\n".join(
        f"- {c.get('name_en', '?')}: {c.get('sketch', '')}" for c in cast
    ) or "(none)"
    tone_block = "\n".join(f"- {t}" for t in work.get("tone_anchors", [])) or "(none)"
    return SYSTEM.format(
        register_pitch=work.get("register_pitch", ""),
        cast_block=cast_block,
        tone_block=tone_block,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--dialogue", type=int, required=True)
    ap.add_argument("--synth-model", default="anthropic/claude-sonnet-4-6")
    ap.add_argument("--all-models", action="store_true",
                    help="Run synthesis with each of the 4 source models as the synthesizer")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    work_dir = PROJECT_ROOT / "works" / args.work
    meta = yaml.safe_load((work_dir / "work.yaml").read_text())
    dialogues = json.loads((work_dir / "source" / "dialogues.json").read_text())
    reading = json.loads((work_dir / "bible" / "reading.json").read_text())
    out_dir = work_dir / "output" / "translations"

    dialogue = next((d for d in dialogues if d["id"] == args.dialogue), None)
    if not dialogue:
        raise ValueError(f"No dialogue {args.dialogue}")

    translations = load_translations(work_dir, args.dialogue, SOURCE_MODELS)
    if len(translations) < 2:
        raise RuntimeError(f"Need at least 2 source translations; got {len(translations)}")

    system = build_system(reading)
    user = HUMAN.format(
        dialogue_id=args.dialogue,
        title=dialogue["title"],
        speakers=", ".join(dialogue["speakers"]),
        translations_block=format_translations(translations),
    )

    synth_models = SOURCE_MODELS if args.all_models else [args.synth_model]
    for synth in synth_models:
        out_path = out_dir / f"dialogue_{args.dialogue:02d}_synth-{safe_id(synth)}.json"
        if out_path.exists() and not args.force:
            log.info(f"synth via {synth}: cached, skipping")
            continue
        log.info(f"synth via {synth}...")
        try:
            tr = translate(model=synth, system=system, user=user)
        except Exception as e:
            log.error(f"  failed: {e}")
            continue
        out_path.write_text(tr.model_dump_json(indent=2))
        log.info(f"  saved → {out_path.name} ({len(tr.lines)} lines)")


if __name__ == "__main__":
    main()
