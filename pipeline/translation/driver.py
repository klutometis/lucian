"""
Translation driver.

Usage:
    uv run pipeline/translation/driver.py --dialogue 4
    uv run pipeline/translation/driver.py --dialogue 4 --all-models
    uv run pipeline/translation/driver.py --start 1 --end 5
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_builder import build_system, build_user
from translator import translate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MODELS = [
    "openai/gpt-5.5",
    "anthropic/claude-sonnet-4-6",
    "gemini/gemini-3.1-pro-preview",
    "xai/grok-4.3",
]
DEFAULT_MODEL = "openai/gpt-5.5"


def work_paths(work_id: str) -> tuple[Path, dict, list[dict], dict]:
    work = PROJECT_ROOT / "works" / work_id
    out = work / "output" / "translations"
    out.mkdir(parents=True, exist_ok=True)
    meta = yaml.safe_load((work / "work.yaml").read_text())
    dialogues = json.loads((work / "source" / "dialogues.json").read_text())
    reading = json.loads((work / "bible" / "reading.json").read_text())
    return out, meta, dialogues, reading


def boundary(dialogues: list[dict], idx: int, n_prev: int = 3, n_next: int = 2):
    prev = dialogues[idx - 1]["lines"][-n_prev:] if idx > 0 else []
    nxt = dialogues[idx + 1]["lines"][:n_next] if idx < len(dialogues) - 1 else []
    return prev, nxt


def safe_model_id(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--dialogue", type=int)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--all-models", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-translate even if output exists")
    args = ap.parse_args()

    out_dir, meta, dialogues, reading = work_paths(args.work)
    system = build_system(reading, meta["language"])
    models = MODELS if args.all_models else [args.model]

    if args.dialogue:
        targets = [i for i, d in enumerate(dialogues) if d["id"] == args.dialogue]
    else:
        end = args.end or max(d["id"] for d in dialogues)
        targets = [i for i, d in enumerate(dialogues) if args.start <= d["id"] <= end]

    for idx in targets:
        d = dialogues[idx]
        prev, nxt = boundary(dialogues, idx)
        user = build_user(dialogue=d, prev_lines=prev, next_lines=nxt)

        for model in models:
            out_path = out_dir / f"dialogue_{d['id']:02d}_{safe_model_id(model)}.json"
            if out_path.exists() and not args.force:
                log.info(f"Dialogue {d['id']} ← {model}: cached, skipping")
                continue
            try:
                log.info(f"Dialogue {d['id']} ← {model}")
                tr = translate(model=model, system=system, user=user)
            except Exception as e:
                log.error(f"  failed: {e}")
                continue

            out_path.write_text(tr.model_dump_json(indent=2))
            log.info(f"  saved → {out_path.name} ({len(tr.lines)} lines)")


if __name__ == "__main__":
    main()
