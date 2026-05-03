"""
TTS annotation driver.

Usage:
    uv run tts/driver.py --dialogue 4
    uv run tts/driver.py --dialogue 4 --translation-model gpt-4o
"""

import argparse
import json
import logging
from pathlib import Path

from annotator import build_performance_bible, annotate_dialogue

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def work_paths(work_id: str) -> tuple[Path, Path]:
    work = PROJECT_ROOT / "works" / work_id
    translations = work / "output" / "translations"
    annotations = work / "output" / "annotations"
    annotations.mkdir(parents=True, exist_ok=True)
    return translations, annotations


def load_translation(translations_dir: Path, dialogue_id: int, model: str = "gpt-4o") -> dict:
    safe = model.replace("/", "-").replace(":", "-")
    path = translations_dir / f"dialogue_{dialogue_id:02d}_{safe}.json"
    if not path.exists():
        raise FileNotFoundError(f"No translation found at {path}")
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="lucian-dialogues-of-the-dead")
    parser.add_argument("--dialogue", type=int, required=True)
    parser.add_argument("--translation-model", default="gpt-4o")
    parser.add_argument("--annotation-model", default="gpt-4o")
    args = parser.parse_args()

    translations_dir, annotations_dir = work_paths(args.work)
    data = load_translation(translations_dir, args.dialogue, args.translation_model)
    lines = data["translation"]
    title = data.get("title_grc", f"Dialogue {args.dialogue}")

    log.info(f"Pass 1: Building performance bible for dialogue {args.dialogue}...")
    bible = build_performance_bible(
        dialogue_id=args.dialogue,
        title=title,
        translated_lines=lines,
        model_name=args.annotation_model,
    )

    print("\n=== PERFORMANCE BIBLE ===")
    for char in bible.characters:
        print(f"\n  {char.name} → voice: {char.voice_name} ({char.voice_id})")
        print(f"    Function: {char.dramatic_function}")
        print(f"    Emotions: {', '.join(char.emotion_palette)}")
        print(f"    Speed: {char.typical_speed}")
        print(f"    Notes: {char.register_notes}")
    print(f"\nArc: {bible.narrative_arc}")
    print(f"Tempo: {bible.tempo_envelope}")
    print(f"Dominant emotion: {bible.dominant_emotion}")
    print(f"Key beats: {'; '.join(bible.key_beats)}")
    print(f"Director: {bible.directorial_notes}")

    log.info(f"Pass 2: Annotating {len(lines)} lines...")
    annotation = annotate_dialogue(
        dialogue_id=args.dialogue,
        title=title,
        translated_lines=lines,
        bible=bible,
        model_name=args.annotation_model,
    )

    print("\n=== ANNOTATED LINES ===")
    for line in annotation.lines:
        print(f"\n[{line.line_index:>2}] {line.speaker:>12}  "
              f"emotion={line.emotion:<20} speed={line.speed}  "
              f"vol={line.volume}  "
              f"↓{line.pause_before_ms}ms ↑{line.pause_after_ms}ms")
        print(f"     {line.text}")

    # Save
    out = {
        "dialogue_id": args.dialogue,
        "title": title,
        "bible": bible.model_dump(),
        "annotation": annotation.model_dump(),
    }
    out_path = annotations_dir / f"dialogue_{args.dialogue:02d}_annotated.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    log.info(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
