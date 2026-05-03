"""
TTS annotation driver.

Usage:
    uv run pipeline/tts/driver.py --dialogue 4
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotator import annotate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--dialogue", type=int, required=True)
    ap.add_argument("--translation-model", default="openai/gpt-5.5")
    ap.add_argument("--annotation-model", default="openai/gpt-5.5")
    args = ap.parse_args()

    work = PROJECT_ROOT / "works" / args.work
    safe = args.translation_model.replace("/", "-").replace(":", "-")
    tr_path = work / "output" / "translations" / f"dialogue_{args.dialogue:02d}_{safe}.json"

    if not tr_path.exists():
        raise FileNotFoundError(f"No translation: {tr_path}")

    tr_data = json.loads(tr_path.read_text())
    reading = json.loads((work / "bible" / "reading.json").read_text())
    dialogues = json.loads((work / "source" / "dialogues.json").read_text())
    title = next((d["title"] for d in dialogues if d["id"] == args.dialogue), "?")

    log.info(f"Annotating dialogue {args.dialogue} with {args.annotation_model}...")
    ann = annotate(
        model=args.annotation_model,
        reading=reading,
        dialogue_id=args.dialogue,
        title=title,
        translated_lines=tr_data["lines"],
    )

    out_dir = work / "output" / "annotations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"dialogue_{args.dialogue:02d}_{safe}_annotated.json"
    out_path.write_text(ann.model_dump_json(indent=2))
    log.info(f"Saved → {out_path}")

    print(f"\n=== Annotated lines ({len(ann.lines)}) ===")
    for i, line in enumerate(ann.lines):
        print(f"\n[{i:>2}] {line.speaker:>14}  speed={line.speed}")
        print(f"     desc: {line.description}")
        print(f"     text: {line.text[:90]}")


if __name__ == "__main__":
    main()
