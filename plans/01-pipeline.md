# Pipeline Plan

## Scope

Produce listenable, dramatized audio of Western Canon classical texts
(starting with Lucian, then Terence/Plautus) from public-domain source texts.
Two coupled pipelines: **translation** (source language → English) and
**TTS/performance** (annotated English → audio). Both live here because the
translation style decision cascades directly into TTS annotation parameters.

---

## Guiding Principles

- **LLM over regex** for all structural detection (chunking, speaker
  assignment, emotion annotation). Deterministic parsers break across
  editions; LLMs handle typographic inconsistency gracefully.
- **Scene = minimum coherent semantic unit (MCSU)** for drama. More
  generally, the MCSU differs by text type (see Chunking below). Never chunk
  smaller than the MCSU — emotional weight and argumentative structure are
  relational properties that vanish below that threshold.
- **Global context travels with every call.** Performance bible (TTS) and key
  terms / style spec (translation) are prepended to every inference call.
  Established at the start; never re-derived mid-run.
- **Style spec bridges both pipelines.** The translation register (e.g.,
  Faux KJV vs. Sitcom) determines TTS parameters (pace, pause, emotion
  defaults). Decide once; it propagates.

---

## Text Types and Chunking

Pass 0 is an LLM segmentation call, parameterized by `text_type`. The output
schema is stable; only field names shift:

| Text type | MCSU | LLM detects via | Example fields |
|-----------|------|-----------------|----------------|
| Drama (Lucian, Terence, Plautus) | Scene | Entrances, exits, act breaks | `act`, `scene`, `speakers` |
| Epic (Lucretius, Homer, Virgil) | Episode / thematic argument | Topic shifts, proposition + demonstration blocks | `book`, `passage`, `topic` |
| Lyric (Catullus, Horace) | Poem | Already self-contained | `poem_number`, `title` |
| Philosophical dialogue (Plato, Cicero) | Exchange / argument | Interlocutor shift + logical resolution | `section`, `interlocutors` |

Drama is the first target. Other text types are structurally accommodated from
the start — Pass 0 just needs a `text_type` hint in the prompt.

---

## Translation Pipeline

Methodology adapted from the Heidegger *Being and Time* project. Source
texts from Perseus Digital Library (public domain Greek/Latin). New
translation = copyright free, stylistically specifiable.

### Passes

**Pass T0 — Key Terms / Global Context**  
All models (GPT-4o, Claude, Gemini, Grok) read the full source text.
Output: recurring terms, character name connotations, thematic vocabulary.
This is the stable preamble for all subsequent translation calls —
the translation equivalent of the performance bible.

**Pass T1 — Translation (per MCSU, with boundary overlap)**  
Each model independently translates one MCSU at a time.
Each call receives: key terms preamble + style spec + current unit in source
language + last few lines of previous unit's translation (continuity) +
first few lines of next unit (resolution target).

**Pass T2 — Critique Round**  
Each model reads the other three translations of the same passage.
Critiques: fidelity, register consistency, missed connotations, style drift.

**Pass T3 — Consensus**  
Synthesis call reads all four translations + critiques → single coherent
translation.

### Configuration Files (per text / style)

Mirrors heidegger/ pattern but for classical drama:

- `STYLE.md` — register choice and its TTS implications  
  (e.g., Faux KJV → measured pacing, longer pauses, grandeur in mundane moments;
  Sitcom → fast tempo, tight gaps, `joking/comedic` as default emotion)
- `CONVENTIONS.md` — proper name handling, stock character type labels,
  recurring phrase commitments
- `GLOSSARY.md` — key Greek/Latin terms with alternative renderings

### Reuse from heidegger/

Port and generalize (not fork):
- `translator.py` — multi-model LangChain wrapper; content-agnostic as-is
- `prompt_builder.py` — reads STYLE/CONVENTIONS/GLOSSARY; works for any language pair
- `meta_analysis.py` — critique/consensus round; fully general

Do not port:
- `chunker.py` — heidegger uses deterministic `\n\n` / `§` detection;
  lucian needs LLM-based MCSU segmentation (Pass 0, see TTS pipeline below)
- `preprocess.py` — written for a specific djvu OCR artifact set

---

## TTS / Performance Pipeline

### Pass 0 — Segmentation

LLM call over full source text. No regex. Output: structured unit map
with line ranges, speaker lists (drama) or topic labels (other types).

### Pass 1 — Performance Bible

Single LLM call over full play text + unit map. Output: director's notes
prepended to every Pass 2 call.

Contents:
- Character profiles: dramatic function, stock type, Cartesia voice ID,
  emotion palette, typical pace/register
- Narrative arc: reversals, trajectory, resolution
- Unit-by-unit directorial notes: dramatic purpose, tempo envelope,
  dominant emotion, key beats, split flags for long units (40+ lines)

### Pass 2 — Line-Level Annotation (×N units)

N separate calls, one per MCSU. Each call receives:
- Full performance bible (stable)
- Last 3–5 lines of previous unit (boundary overlap)
- Full current unit (annotation target)
- First 1–2 lines of next unit (resolution target)

Output per line:
```json
{
  "line": 14,
  "speaker": "Syrus",
  "text": "<emotion value='joking/comedic'/> Oh certainly, master. [laughter]",
  "speed": 1.25,
  "volume": 1.0,
  "pause_before_ms": 180,
  "pause_after_ms": 80
}
```

All four dimensions (emotion, speed, volume, pause) annotated simultaneously
within unit context. Never per-dimension in separate passes.

### Pass 3 — Audio Stitching

- Per-line audio via Cartesia Sonic-3 API (voice ID + annotated transcript)
- `pause_before_ms` / `pause_after_ms` silence inserted between clips
- Optional: light room reverb for shared acoustic space
- Unit transitions: longer pause or distinct audio marker

Cartesia is fully stateless. Pause values live in the stitching layer.

---

## Cartesia Reference (Sonic-3)

Model IDs: `sonic-3` · `sonic-3-latest`

Emotive voices:
| Name | Voice ID |
|------|----------|
| Leo | `0834f3df-e650-4766-a20c-5a93a43aa6e3` |
| Jace | `6776173b-fd72-460d-89b3-d85812ee518d` |
| Kyle | `c961b81c-a935-4c17-bfb3-ba2239de8c2f` |
| Gavin | `f4a3a8e4-694c-4c45-9ca0-27caf97901b5` |
| Maya | `cbaf8084-f009-4838-a096-07ee2e6612b1` |
| Tessa | `6ccbfb76-1fc6-48f7-b71d-91ac6298247b` |
| Dana | `cc00e582-ed66-4004-8336-0175b85c85f6` |
| Marian | `26403c37-80c1-4a1a-8692-540551ca2ae5` |

---

## Directory Structure

```
lucian/
  translation/
    translator.py       # ported from heidegger/, generalized
    prompt_builder.py   # ported from heidegger/, generalized
    meta_analysis.py    # ported from heidegger/, generalized
    STYLE.md            # new: Lucian-specific register + TTS implications
    CONVENTIONS.md      # new: Greek terms, character names, stock types
    GLOSSARY.md         # new: Lucian's vocabulary
  tts/
    segmenter.py        # Pass 0: LLM-based MCSU detection
    annotator.py        # Passes 1 & 2: performance bible + line annotation
    stitcher.py         # Pass 3: Cartesia API + silence + reverb
  sources/              # Perseus Digital Library texts (public domain)
  output/
    translations/
    audio/
  plans/                # this directory
```

---

## Phasing

**Phase 1 — Prototype (single scene, end-to-end)**  
Target: one scene of *Dialogues of the Dead* through the full pipeline.
Validate Pass 0 segmentation, Pass T1 translation quality, Pass 2 annotation
coherence, Pass 3 audio output. Commit to voice casting and style register.

**Phase 2 — Translation pipeline (full text)**  
Complete Passes T0–T3 for a full Lucian dialogue. Establish
STYLE/CONVENTIONS/GLOSSARY. Port and adapt heidegger/ infrastructure.

**Phase 3 — TTS pipeline (full text)**  
Performance bible + full line annotation + stitching. First complete audio.

**Phase 4 — Distribution**  
YouTube first (lowest friction). Then podcast RSS, Internet Archive,
own site. GitHub for pipeline code.

---

## Open Questions

1. **Style register**: Faux KJV vs. Sitcom — decide at prototype stage.
   Start with Sitcom (faster to validate TTS; *Dialogues of the Dead* is
   structurally already a sitcom).
2. **Voice casting**: Browse Cartesia emotive library, cast stock types
   (senex, adulescens, servus, meretrix, divine bureaucrat).
3. **Source text acquisition**: Script Perseus Digital Library fetch for
   target Lucian dialogues (Greek).
4. **Lucretius / non-drama**: MCSU segmentation prompt needs `text_type`
   parameter and appropriate output schema before tackling epic. Validate
   drama first.
