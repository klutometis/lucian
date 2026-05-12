"""
Holistic critique pass: each flagship evaluator reads the reading + all
translations from the big three (Claude Opus, GPT-5.5, Gemini 3.1 Pro)
across all 30 dialogues, then produces a comparative critique with
per-dialogue rankings and stylistic profiles.

Output: works/<work>/output/critiques/holistic_<evaluator>.json

Usage:
    uv run pipeline/translation/critique.py
    uv run pipeline/translation/critique.py --evaluator anthropic/claude-opus-4-7
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Literal

import instructor
import litellm
import yaml
from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# The contender translations. Drops Sonnet 4.6 and Grok per
# tier-consistency + reliability concerns.
CONTENDERS = [
    "anthropic/claude-opus-4-7",
    "openai/gpt-5.5",
    "gemini/gemini-3.1-pro-preview",
]

# All three are evaluators too. (Each model evaluates everyone including itself.)
EVALUATORS = CONTENDERS


def safe_id(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SceneVerdict(BaseModel):
    model_config = ConfigDict(extra="allow")
    dialogue_id: int = Field(description="Scene/dialogue/passage id (whatever unit the work uses).")
    winner: str = Field(description="Model id of the strongest translation for this scene.")
    runner_up: str = Field(description="Model id of the second-strongest.")
    confidence: Literal["high", "medium", "low"]
    why: str = Field(description="1-3 sentences explaining the verdict. Be specific — name lines or moments.")
    notable_misses: str = Field(
        default="",
        description="Optional: lines or moments where even the winner falls short, "
                    "and which other translation got them right.",
    )


class StylisticProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    signature: str = Field(description="What this model's translations sound like, in 2-4 sentences.")
    where_it_wins: str = Field(description="What kinds of dialogues or moments this model serves best.")
    where_it_loses: str = Field(description="What kinds of dialogues or moments this model fails on.")


class HolisticCritique(BaseModel):
    model_config = ConfigDict(extra="allow")
    profiles: list[StylisticProfile] = Field(description="One profile per contender model.")
    per_dialogue: list[SceneVerdict] = Field(description="One verdict per scene/dialogue/passage.")
    overall: str = Field(
        description="Overall verdict: is one model clearly best, do winners vary, what should be done? 4-8 sentences."
    )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_TEMPLATE = """You are the dramaturg evaluating translations of
{title} ({author}) for an audio production. Your job: give the production
team a clear, opinionated recommendation about which translation to record
for each scene, and why.

# What you're seeing

You have the director's brief (the reading: register, cast, running gags,
tone anchors) and full-corpus translations of all scenes, one from each
contender model:
{contenders_block}

# What you're producing

A structured critique:
  1. A stylistic profile per model: what does each one's voice sound like,
     where does it serve the material, where does it fail it.
  2. A per-scene verdict: which translation wins, runner-up, confidence,
     specific reasons (cite lines or moments).
  3. An overall verdict: one model wins the work, or winners vary, or
     synthesis is needed for specific scenes.

# What "best" means here

The director's register pitch is the load-bearing brief:

  > {register_pitch}

The best translation is the one that:
  - Lands the comic / dramatic timing of each beat
  - Holds a consistent character voice across each scene
  - Avoids the literal-fidelity tax (serves the performance, not the lexicon)
  - Trusts the register pitch above without hedging toward neutral formality

# Be opinionated, be specific

Quote lines or paraphrase moments. Don't say "X is more theatrical"; say
"X renders [character]'s complaint as '[exact phrase]' which softens the
[register descriptor] rhythm the brief asks for." Concrete > abstract.

If you're the model whose translation is being evaluated (yes, this happens
— you see your own work alongside the others), be honest. Self-favoritism
or false modesty both hurt the production.
"""

HUMAN = """# The reading (director's brief)

{reading_block}

# The three translations to compare

{translations_block}

Produce the holistic critique.
"""


def load_translations(work_dir: Path) -> dict[int, dict[str, dict]]:
    """Returns: {dialogue_id: {model: translation_data}}."""
    out: dict[int, dict[str, dict]] = {}
    tr_dir = work_dir / "output" / "translations"
    for model in CONTENDERS:
        for path in sorted(tr_dir.glob(f"dialogue_*_{safe_id(model)}.json")):
            dialogue_id = int(path.stem.split("_")[1])
            data = json.loads(path.read_text())
            out.setdefault(dialogue_id, {})[model] = data
    return out


def format_translations(translations: dict[int, dict[str, dict]]) -> str:
    parts = []
    for dialogue_id in sorted(translations):
        per_model = translations[dialogue_id]
        parts.append(f"## Dialogue {dialogue_id}")
        for model in CONTENDERS:
            data = per_model.get(model)
            if not data:
                parts.append(f"\n### {model}\n(missing)\n")
                continue
            parts.append(f"\n### {model}")
            for line in data["lines"]:
                parts.append(f"  {line['speaker']}: {line['text']}")
        parts.append("")
    return "\n".join(parts)


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
        "\n## Cast",
    ]
    for c in cast:
        parts.append(f"- [{c.get('id','?')}] {c.get('name_en','?')}: {c.get('sketch','')}")
    return "\n".join(parts)


def make_client():
    return instructor.from_litellm(litellm.completion)


def run_evaluator(
    evaluator: str,
    system: str,
    reading_block: str,
    translations_block: str,
    max_tokens: int = 32000,
) -> HolisticCritique:
    client = make_client()
    log.info(f"running evaluator: {evaluator}")
    return client.create(
        model=evaluator,
        response_model=HolisticCritique,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": HUMAN.format(
                reading_block=reading_block,
                translations_block=translations_block,
            )},
        ],
        max_tokens=max_tokens,
    )


def build_system(meta: dict, reading: dict) -> str:
    contenders_block = "\n".join(f"  - {m}" for m in CONTENDERS)
    return SYSTEM_TEMPLATE.format(
        title=meta.get("title", "the work"),
        author=meta.get("author", "unknown"),
        contenders_block=contenders_block,
        register_pitch=reading.get("work", {}).get("register_pitch", "(no register pitch specified)"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="lucian-dialogues-of-the-dead")
    ap.add_argument("--evaluator", help="Run only one evaluator (default: all 3)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    work_dir = PROJECT_ROOT / "works" / args.work
    meta = yaml.safe_load((work_dir / "work.yaml").read_text())
    reading = json.loads((work_dir / "bible" / "reading.json").read_text())
    translations = load_translations(work_dir)
    log.info(f"loaded {len(translations)} scenes × {len(CONTENDERS)} models")

    missing = [d for d, t in translations.items() if len(t) < len(CONTENDERS)]
    if missing:
        log.warning(f"dialogues missing one or more contenders: {missing}")

    out_dir = work_dir / "output" / "critiques"
    out_dir.mkdir(parents=True, exist_ok=True)

    system = build_system(meta, reading)
    reading_block = format_reading(reading)
    translations_block = format_translations(translations)
    log.info(f"input size: ~{(len(system) + len(reading_block) + len(translations_block)) // 4} tokens (rough)")

    evaluators = [args.evaluator] if args.evaluator else EVALUATORS
    for evaluator in evaluators:
        out_path = out_dir / f"holistic_{safe_id(evaluator)}.json"
        if out_path.exists() and not args.force:
            log.info(f"  {evaluator}: cached, skipping")
            continue
        try:
            critique = run_evaluator(evaluator, system, reading_block, translations_block)
        except Exception as e:
            log.error(f"  {evaluator}: failed: {e}")
            continue
        out_path.write_text(critique.model_dump_json(indent=2))
        log.info(f"  saved → {out_path}")


if __name__ == "__main__":
    main()
