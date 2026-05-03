# Per-Work Structure

## Why

The project started as a Lucian proof-of-concept but the pipeline is meant to
serve any Western Canon work — Terence, Plautus, Lucretius, Catullus, etc.
Each work has its own source format, genre, cast, register, and voice
casting. The project name stays `lucian` (named after the work that inspired
it; abstract project names are worse).

## Per-work vs shared

**Per-work (data + irreducibly custom glue):**
- Source files in whatever format the publisher ships
- Preprocessing — ad-hoc per work; Perseus TEI ≠ Gutenberg ASCII ≠ Loeb OCR
- Normalized intermediate (`dialogues.json`, `passages.json`, etc.)
- The reading (cast, beats, gags, register pitch) — entirely work-specific
- The casting (voice IDs for *this* work's characters)
- Translations, annotations, audio outputs

**Shared (library code + provider catalogs):**
- Translation pipeline (translator, prompt builder, multi-model fan-out)
- TTS pipeline (annotator, stitcher, provider abstraction)
- Chunker prompt (parameterized by genre)
- Voice catalogs (Hume's voices are work-agnostic; same Leo can play Hermes
  in Lucian and Tityrus in Vergil)

## Contract between them

Per-work code's only obligation: produce a normalized JSON structure that
downstream pipeline code can consume. The shape can flex per-work — an
epic poem with one narrator looks different from a drama with ensemble
cast — and that's fine. Pipeline code reads natural language anyway and
absorbs shape variation.

We're not pre-abstracting. Schemas stay fluid. Patterns emerge from doing
more works, not from guessing now.

## Directory layout

```
lucian/
  works/
    lucian-dialogues-of-the-dead/
      work.yaml             # thin: language, genre, source, register hint
      notes.md              # human-facing: casting reasoning, what was hard
      source/
        raw/                # whatever the source ships, untouched
        preprocess.py       # ad-hoc; do what this source needs
        dialogues.json      # normalized output for this work
      bible/
        reading.json        # one-time pre-read artifact
        casting.json        # character → voice_id, locked
      output/
        translations/
        annotations/
        audio/
    terence-adelphoe/        # later
    lucretius-de-rerum-natura/  # later
  pipeline/                  # shared library code
    translation/
    tts/
      providers/
    voices/
      sync.py                # refreshes voice catalogs from providers
  voices/                    # current catalog snapshots, committed
    hume.json
    elevenlabs.json
    cartesia.json
  plans/
```

## Conventions

- **`work.yaml`** is thin — just enough metadata for the pipeline to know
  the language pair, genre hint for chunker, register pitch, source
  attribution. Heavy work-specific content goes in `bible/reading.json`.
- **`notes.md`** is human-facing. Casting reasoning, voicing decisions,
  things that didn't work, things to remember. Not consumed by code.
- **Preprocessing is per-work and free-form.** Don't try to share. Just
  output a normalized JSON downstream can read.
- **`voices/` is committed to the repo** (current Hume / ElevenLabs /
  Cartesia catalog snapshots) but periodically refreshable via
  `pipeline/voices/sync.py`. Each catalog file embeds its snapshot date.
- **Schemas are fluid.** A field in one work's `reading.json` doesn't have
  to appear in another's. The system tolerates shape variation because
  every stage operates on natural language.

## Migration from current layout

Current files are at the project root, assuming Lucian is the only work.
Migrate to:

```
sources/      → works/lucian-dialogues-of-the-dead/source/
translation/  → pipeline/translation/
  STYLE.md, CONVENTIONS.md, GLOSSARY.md  → delete (per plan 03)
tts/          → pipeline/tts/
output/       → works/lucian-dialogues-of-the-dead/output/
```

Mostly `git mv`s plus path fixes in a handful of files (driver scripts
that hardcode `sources/`, `output/`, etc.). Then add `work.yaml` and
empty `bible/` for Lucian. Validate by re-running the dialogue 4
pipeline end-to-end.

## What we explicitly defer

- Sharing preprocessing helpers across works. If we end up with five
  Perseus works and the TEI parsing repeats, we'll abstract then. Not now.
- Schema enforcement for `reading.json` / `casting.json`. We'll discover
  the right shape by writing them; not by specifying them.
- Cross-work voice reuse logic. If we want the same voice playing Hermes
  in Lucian and Apollo in Aeschylus, we'll figure that out when it
  matters. The voice catalogs are work-agnostic; that's enough.
