"""
Render an annotated dialogue to audio via the chosen provider.
One multi-utterance request; provider handles inter-line pacing.

Usage:
    uv run pipeline/tts/render.py --dialogue 4 --provider hume
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from providers.base import Utterance
from providers.hume import HumeProvider
from providers.elevenlabs import ElevenLabsProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PROVIDERS = {
    "hume": HumeProvider,
    "elevenlabs": ElevenLabsProvider,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--dialogue", type=int, required=True)
    ap.add_argument("--translation-model", default="openai/gpt-5.5")
    ap.add_argument("--provider", default="hume", choices=list(PROVIDERS))
    args = ap.parse_args()

    work = PROJECT_ROOT / "works" / args.work
    safe_tm = args.translation_model.replace("/", "-").replace(":", "-")
    annotation_path = work / "output" / "annotations" / f"dialogue_{args.dialogue:02d}_{safe_tm}_annotated.json"
    casting_path = work / "bible" / f"casting_{args.provider}.json"
    reading_path = work / "bible" / "reading.json"

    if not annotation_path.exists():
        raise FileNotFoundError(f"No annotation: {annotation_path}")
    if not casting_path.exists():
        raise FileNotFoundError(f"No casting: {casting_path} (run build_casting.py first)")

    annotation = json.loads(annotation_path.read_text())
    casting = json.loads(casting_path.read_text())
    reading = json.loads(reading_path.read_text())

    # Map speaker name (English or Greek) → character id → voice_id
    name_to_id = {}
    for char in reading.get("cast", []):
        for key in (char.get("name_en"), char.get("name_grc"), char.get("id")):
            if key:
                name_to_id[key] = char["id"]

    utterances = []
    for line in annotation["lines"]:
        speaker = line["speaker"]
        cid = name_to_id.get(speaker)
        if not cid or cid not in casting:
            log.warning(f"No voice for speaker {speaker!r}; skipping")
            continue

        utterances.append(Utterance(
            voice_id=casting[cid]["voice_id"],
            text=line["text"],
            description=line.get("description"),
            speed=line.get("speed", 1.0),
        ))

    log.info(f"Rendering {len(utterances)} utterances via {args.provider}...")
    provider = PROVIDERS[args.provider]()
    audio = provider.synthesize(utterances)

    audio_dir = work / "output" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = audio_dir / f"dialogue_{args.dialogue:02d}_{safe_tm}_{args.provider}.wav"
    out_path.write_bytes(audio)
    log.info(f"Saved → {out_path} ({len(audio)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
