"""
Build translation prompts from the reading + boundary context.
The reading carries register, gags, tone anchors, and cast sketches.
No glossary, no conventions, no commitments — just nail the voice.
"""

import json


def build_system(reading: dict, source_language: str) -> str:
    work = reading.get("work", {})
    cast = reading.get("cast", [])

    cast_lines = []
    for c in cast:
        cast_lines.append(
            f"- {c.get('name_en', '?')} ({c.get('name_grc', '')}): {c.get('sketch', '')}"
        )
    cast_block = "\n".join(cast_lines) if cast_lines else "(none specified)"

    gags = work.get("running_gags", [])
    gags_block = "\n".join(f"- {g}" for g in gags) if gags else "(none specified)"

    tone = work.get("tone_anchors", [])
    tone_block = "\n".join(f"- {t}" for t in tone) if tone else "(none specified)"

    return f"""You are translating from {source_language} into English.

# Register

{work.get('register_pitch', '')}

# Cast

{cast_block}

# Running gags

{gags_block}

# Tone anchors

{tone_block}

# Your job

Translate the dialogue. Nail the voice — register, character, comic timing.
No literal-fidelity tax: serve the performance. The smallest unit is the
scene; you have the whole scene at once.

Required output: a list of `lines`, each with `speaker` and `text`.
You may add other fields per line if useful (e.g., a directorial note),
but don't pad."""


def build_user(
    *,
    dialogue: dict,
    prev_lines: list[dict] | None = None,
    next_lines: list[dict] | None = None,
) -> str:
    def fmt(lines):
        if not lines:
            return "(none)"
        return "\n".join(f"{l['speaker']}: {l['text']}" for l in lines)

    speakers = ", ".join(dialogue.get("speakers", []))
    return f"""## Dialogue {dialogue['id']}: {dialogue['title']}

Speakers: {speakers}

### Previous dialogue's last lines (for continuity)
{fmt(prev_lines)}

### This dialogue (translate)
{fmt(dialogue['lines'])}

### Next dialogue's first lines (for resolution awareness)
{fmt(next_lines)}
"""
