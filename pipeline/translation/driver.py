"""
Translation driver. Runs one or more dialogues through the translation pipeline.

Usage:
    uv run translation/driver.py --dialogue 4          # translate dialogue 4 only
    uv run translation/driver.py --dialogue 4 --all-models
    uv run translation/driver.py --start 1 --end 5     # translate dialogues 1-5
"""

import argparse
import json
import logging
from pathlib import Path

from prompt_builder import TranslationPromptBuilder
from translator import Translator, DialogueTranslation

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

MODELS = [
    "gpt-5.5",
    "claude-sonnet-4-6",
    "gemini-3.1-pro-preview",
    "grok-4.3",
]

DEFAULT_MODEL = "gpt-5.5"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def work_paths(work_id: str) -> tuple[Path, Path]:
    work = PROJECT_ROOT / "works" / work_id
    out = work / "output" / "translations"
    out.mkdir(parents=True, exist_ok=True)
    return work, out


def load_dialogues(work_dir: Path) -> list[dict]:
    return json.loads((work_dir / "source" / "dialogues.json").read_text())


def boundary_lines(dialogues: list[dict], idx: int, n: int = 3) -> tuple:
    prev = dialogues[idx - 1]["lines"][-n:] if idx > 0 else []
    next_ = dialogues[idx + 1]["lines"][:2] if idx < len(dialogues) - 1 else []
    return prev, next_


def translate_dialogue(
    dialogue: dict,
    prev: list,
    next_: list,
    model_name: str,
    builder: TranslationPromptBuilder,
) -> DialogueTranslation:
    translator = Translator(model_name=model_name)
    prompt = builder.build_translation_prompt()
    log.info(f"Translating dialogue {dialogue['id']} with {model_name}...")
    return translator.translate(prompt, dialogue, prev_lines=prev, next_lines=next_)


def save_translation(dialogue: dict, result: DialogueTranslation, model_name: str, out_dir: Path):
    safe_model = model_name.replace("/", "-").replace(":", "-")
    out_path = out_dir / f"dialogue_{dialogue['id']:02d}_{safe_model}.json"
    data = {
        "dialogue_id": dialogue["id"],
        "title_grc": dialogue["title"],
        "model": model_name,
        "translation": result.translation,
        "thinking": result.thinking,
        "key_terms": result.key_terms,
        "uncertainties": result.uncertainties,
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"Saved → {out_path}")
    return out_path


def print_translation(dialogue: dict, result: DialogueTranslation):
    print(f"\n{'='*60}")
    print(f"Dialogue {dialogue['id']}: {dialogue['title']}")
    print(f"{'='*60}")
    for line in result.translation:
        print(f"\n{line.get('speaker', '?'):>16}: {line.get('text', '')}")
    print(f"\n--- Translator's Notes ---\n{result.thinking}")
    if result.key_terms:
        print(f"\nKey terms: {', '.join(result.key_terms)}")
    if result.uncertainties:
        print(f"Uncertainties: {', '.join(result.uncertainties)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="lucian-dialogues-of-the-dead")
    parser.add_argument("--dialogue", type=int, help="Translate a single dialogue by ID")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--all-models", action="store_true")
    args = parser.parse_args()

    work_dir, out_dir = work_paths(args.work)
    dialogues = load_dialogues(work_dir)
    builder = TranslationPromptBuilder(config_dir=Path(__file__).parent)

    models = MODELS if args.all_models else [args.model]

    # Determine which dialogues to translate
    if args.dialogue:
        targets = [i for i, d in enumerate(dialogues) if d["id"] == args.dialogue]
    else:
        end = args.end or len(dialogues)
        targets = [i for i, d in enumerate(dialogues)
                   if args.start <= d["id"] <= end]

    for idx in targets:
        dialogue = dialogues[idx]
        prev, next_ = boundary_lines(dialogues, idx)

        for model_name in models:
            try:
                result = translate_dialogue(dialogue, prev, next_, model_name, builder)
                print_translation(dialogue, result)
                save_translation(dialogue, result, model_name, out_dir)
            except Exception as e:
                log.error(f"Failed {dialogue['id']} with {model_name}: {e}")


if __name__ == "__main__":
    main()
