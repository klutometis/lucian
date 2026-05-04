"""
Casting: design a voice per character via the chosen TTS provider.
Saves bible/casting_<provider>.json.

Usage:
    uv run pipeline/casting/build_casting.py --provider hume
    uv run pipeline/casting/build_casting.py --provider hume --only menippos,charon
"""

import argparse
import json
import logging
from pathlib import Path

from hume_provider_loader import load_provider  # local import-shim

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Default sample line for voice design.
SAMPLE_TEXT = (
    "I've been around longer than most. I've seen what people pretend to be, "
    "and I've seen what they actually are. There is, in the end, very little "
    "difference between the two."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--provider", required=True, choices=["hume", "elevenlabs"])
    ap.add_argument("--only", help="Comma-separated character ids (default: all)")
    ap.add_argument("--sample-text", default=SAMPLE_TEXT)
    args = ap.parse_args()

    work = PROJECT_ROOT / "works" / args.work
    reading = json.loads((work / "bible" / "reading.json").read_text())
    cast = reading.get("cast", [])

    casting_path = work / "bible" / f"casting_{args.provider}.json"
    casting = json.loads(casting_path.read_text()) if casting_path.exists() else {}

    only = set(s.strip() for s in args.only.split(",")) if args.only else None
    targets = [c for c in cast if not only or c["id"] in only]

    provider = load_provider(args.provider)

    for char in targets:
        cid = char["id"]
        if cid in casting:
            log.info(f"  [{cid}] already cast (voice_id={casting[cid]['voice_id']}); skipping")
            continue

        # Pass already-cast voice IDs so providers that pick from a fixed
        # library don't reuse the same voice for multiple characters.
        excluded = [v["voice_id"] for v in casting.values()]

        try:
            voice_id = provider.design_voice(
                description=char["voice_description"],
                name=f"lucian-{cid}",
                sample_text=args.sample_text,
                excluded_voice_ids=excluded,
            )
        except Exception as e:
            log.error(f"  [{cid}] failed: {e}")
            continue

        casting[cid] = {
            "voice_id": voice_id,
            "name_en": char.get("name_en", cid),
            "voice_description": char["voice_description"],
        }
        casting_path.write_text(json.dumps(casting, ensure_ascii=False, indent=2))

    log.info(f"Casting → {casting_path} ({len(casting)} voices)")


if __name__ == "__main__":
    main()
