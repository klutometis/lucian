# Global Artifacts: The Reading, the Casting, the Direction

## Problem with the current setup

Current files (`STYLE.md`, `CONVENTIONS.md`, `GLOSSARY.md`) are scholarship
apparatus inherited from the Heidegger pipeline. They were designed to enforce
term-by-term consistency across thousands of paragraphs of philosophical prose
where one mistranslated *Sein* breaks the argument. Lucian doesn't have that
problem.

Worse, they actively work against the goal. We're asking for sitcom voice;
then we hand the model a glossary that says "render αὐτάρκεια as
'self-sufficiency'." That's a *philosophy translation* instruction — it
encourages the model to weight terminology over comic timing.

**Tear them down.** Replace with a single global artifact: **the reading.**

## The reading: one-time pre-pass

A director reads the play before casting. They produce a brief: the cast,
the running gags, the beats, the register. Everyone — translators,
voice-casters, line annotators — works from that brief.

For Lucian, run a one-shot LLM pass over the full Greek text (it's short,
fits in any modern context window). Produce one artifact.

### Artifact: `bible/reading.json`

```json
{
  "work": {
    "title": "Dialogues of the Dead",
    "author": "Lucian of Samosata",
    "register_pitch": "Sitcom — fast, contemporary American English. Underworld as workplace comedy. Recurring ensemble cast.",
    "running_gags": [
      "Wealthy dead still mourning their lost gold/kingdoms/looks",
      "Legacy-hunters outliving the rich men they were courting",
      "Philosophers exposed as frauds the moment they cross the Styx",
      "Charon shaking down passengers for the obol fare",
      "Cynics (Diogenes, Menippus) cheerfully unbothered by everything"
    ],
    "tone_anchors": [
      "Dry. Punchy. Beat-driven.",
      "Death is mundane; the absurdity is everyone's reaction to it.",
      "Cynics laugh, kings sulk, philosophers get caught with rouge in their pockets."
    ]
  },
  "cast": [
    {
      "id": "menippus",
      "name_grc": "Μένιππος",
      "name_en": "Menippus",
      "sketch": "Cynic philosopher, dies amused. The only one who gets the joke. Annoyingly comfortable with everything.",
      "voice_description": "Mid-30s male, dry, slightly nasal, unhurried. Always sounds like he's about to laugh.",
      "register": "deadpan, ~1.1 speed",
      "emotion_default": "amused detachment"
    },
    {
      "id": "charon",
      "name_grc": "Χάρων",
      "name_en": "Charon",
      "sketch": "Ferryman of the dead. Petty bureaucrat. Obsessed with his obol fee. DMV clerk energy.",
      "voice_description": "Older male, gravelly, perpetually mildly aggrieved, brisk delivery. Sounds like he's been doing this job for too long.",
      "register": "frustrated, brisk, ~1.15 speed",
      "emotion_default": "weary irritation"
    }
    // ...etc, ~10–15 recurring characters
  ],
  "beats_per_dialogue": [
    {
      "id": 4,
      "title_en": "Hermes & Charon settle accounts",
      "premise": "Hermes is collecting on supplies he advanced for Charon's boat. Charon can't pay because there's a peace on.",
      "beats": [
        {"lines": "1-2", "beat": "setup: Hermes opens the books"},
        {"lines": "3-10", "beat": "itemized invoice — escalating absurdity of expenses"},
        {"lines": "11-13", "beat": "the punchline: 'wish for a plague so I can pay you'"},
        {"lines": "14-17", "beat": "Hermes' nostalgic rant about the old breed of dead"}
      ],
      "key_payoff": "Charon's deadpan 'money's worth dying for' caps the bit"
    }
    // ...one per dialogue
  ]
}
```

## How `reading.json` flows downstream

```
                   ┌─────────────────────┐
                   │   reading.json      │
                   │   (the bible)       │
                   └──────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐
   │ Casting │          │Translate │          │ Annotate │
   │         │          │          │          │          │
   │ cast →  │          │ register │          │ beats →  │
   │ voice   │          │ + cast   │          │ pacing   │
   │ id      │          │ sketches │          │          │
   │         │          │ + beats  │          │ cast →   │
   │         │          │          │          │ voice    │
   │         │          │          │          │ +        │
   │         │          │          │          │ acting   │
   │         │          │          │          │ instr    │
   └─────────┘          └──────────┘          └──────────┘
```

## Step 1 — Casting (one-time, locked)

Input: `cast[].voice_description` from `reading.json`
Output: `bible/casting.json` (locked artifact — used everywhere)

**With Hume Octave 2 (recommended):** the `voice_description` IS the input.
No catalog search. The model designs a voice from the prompt. Save the
returned `voice_id`.

**With ElevenLabs v3 (alternative):** dump the catalog once; embed
voice descriptions; nearest-neighbor search per character; LLM proposes
top 3 with reasoning; human picks. Save the chosen `voice_id`.

Either way, output is the same shape:
```json
{
  "menippus": { "provider": "hume", "voice_id": "xxx", "reasoning": "..." },
  "charon":   { "provider": "hume", "voice_id": "yyy", "reasoning": "..." }
}
```

Locked. Reused across all 30 dialogues.

## Step 2 — Translation (per dialogue)

Input per call:
- `reading.json` (full bible — small, prepended every time)
- The current dialogue's beat structure
- Last 2-3 lines of previous dialogue (continuity)
- First 1-2 lines of next dialogue (resolution)
- The Greek source

System prompt becomes ~200 words:
- *"You are translating Lucian. Sitcom register. Here is the cast brief.
  Here is this scene's beat structure. Translate. No glossary, no
  commitments — just nail the voice."*

No `STYLE.md`. No `CONVENTIONS.md`. No `GLOSSARY.md`. The reading carries
all the load-bearing context.

All four models in parallel (per `02-translation-philosophy.md`).

## Step 3 — Annotation (per dialogue)

Input per call:
- `reading.json` (cast sketches + this dialogue's beats)
- `casting.json` (which voice for which character)
- The translated dialogue
- Boundary context (same as translation)

Output per line: `{voice_id, acting_instruction, speed, pause_before_ms,
pause_after_ms}`.

**With Hume Octave:** `acting_instruction` is natural language,
beat-aware: "Hermes, mid-rant, picking up speed and frustration. Half
sarcastic, half exhausted."

**With Cartesia Sonic-3 (current):** `acting_instruction` becomes
emotion-enum + speed/volume, harder to express beat-shifts.

The beat awareness is the upgrade — annotation isn't just per-line
emotion, it's "where in the arc are we." A line at the end of the
itemized-invoice beat should sound different from a line at the start
of the nostalgic rant, *even if both are tagged "frustrated."*

## Step 4 — Stitching

Unchanged in shape. Pauses still live in the stitcher (TTS providers
are stateless on inter-line timing). Provider abstraction so we can
swap Cartesia ↔ Hume ↔ ElevenLabs without touching upstream.

## Deletions

- `translation/STYLE.md` — replaced by `register_pitch` in `reading.json`
- `translation/CONVENTIONS.md` — delete; the model knows what Hermes is
- `translation/GLOSSARY.md` — delete; if a Greek term needs special care,
  it goes in the relevant character's sketch or in a one-line note in
  `running_gags`
- `tts/annotator.py` `BIBLE_SYSTEM` (the giant inline prompt) — replaced
  by reading the global `reading.json`

## File layout after refactor

Directory layout is defined in plan 04. The reading lives at
`works/<work>/bible/reading.json`; the casting at
`works/<work>/bible/casting.json`. Voice catalogs are work-agnostic and
live at `voices/` at the project root. Pipeline code lives under
`pipeline/`. See plan 04 for the full tree.

## Phasing

1. **Build the reading.** One-shot LLM pass on the 30 dialogues → `reading.json`.
   Validate by reading it as a human director would. Fix anything wrong.
2. **Tear down Heideggerian files.** Delete STYLE/CONVENTIONS/GLOSSARY.
   Rewrite `prompt_builder.py` to read the reading.
3. **Re-translate dialogue 4** with the slimmer prompt + reading. Compare
   to the pre-refactor takes. Confirm voice quality preserved.
4. **Build casting workflow.** Default to Hume Octave; produce `casting.json`
   for the recurring cast.
5. **Build provider abstraction in TTS.** Run dialogue 4 through Hume,
   compare to Cartesia version. Listening test settles it.
6. **Beat-aware annotator.** Annotator now has access to which beat each
   line belongs to. Generate richer per-line acting instructions.

## Open questions

- **Beat structure granularity.** Per-dialogue beats are clear for
  longer dialogues (10+ lines). Shorter dialogues may not need them — they
  ARE one beat. Decide threshold during reading construction.
- **Single-model or multi-model reading?** The reading is the *one*
  artifact where consistency across dialogues matters most. Probably
  one model (Claude or GPT-5.5) authors it; human reviews; lock.
  Multi-model parallelism applies to translation, not to the reading.
- **Cross-validate reading against translations?** After the first pass,
  some character traits will only be visible in the audio. The reading
  may need to be revised once we have audio takes. Treat as living
  document for the first few dialogues, then lock.
