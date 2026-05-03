Sure — and honestly you don't even need a tool for this, just paste this directly into the Claude conversation:

---

```markdown
# Western Canon — TTS & Translation Pipeline

## Context

Building listenable audio dramatizations of Western Canon classical texts
(Lucian, Terence, Plautus) for the **Western Canon > Lucian** project based
on Harold Bloom's canon.

**The problem**: Nothing usable exists on Audible or any platform. LibriVox
recordings are flat, affectless, no genuine dialogue interaction, wrong
pacing, no shared acoustic space. Various actors are repackaging these as
"podcasts" with ads inserted, distributed on Audible.

**The goal**: Produce something better using Cartesia Sonic-3, intelligently
annotated by an LLM pipeline. Potentially also produce fresh translations in
interesting stylistic registers.

---

## Part I: TTS Production Pipeline

### Conceptual Model

**Forward diarization**: pre-assign text to voices, annotate each line with
emotion/tempo/pause data, generate per-line audio via Cartesia, stitch.

The LibriVox failure is both prosodic (flat affect) and rhythmic (wrong
inter-speaker timing, no shared acoustic space). The pipeline fixes both.

---

### The Four Passes

#### Pass 0 — Scene Identification / Chunking

> **Do not use regex or deterministic Python.** Breaks across editions,
> authors, and translation conventions. One LLM prompt handles everything.

- **Input**: Raw play text in any format (Project Gutenberg, Loeb, OCR, etc.)
- **Output**: Structured scene map with line ranges and speaker lists

```json
[
  { "act": 1, "scene": 1, "lines": [1, 48], "speakers": ["Simo", "Sosia"] },
  { "act": 1, "scene": 2, "lines": [49, 91], "speakers": ["Simo", "Pamphilus"] }
]
```

Scene boundaries in classical drama are semantically unambiguous (entrances,
exits, act breaks) even when typographically inconsistent across editions.

---

#### Pass 1 — Performance Bible

- **Input**: Full play text + scene map from Pass 0
- **Output**: Structured director's notes — prepended to **every** Pass 2 call
- **One inference call** over the full play text (Terence/Lucian are short
  enough — 4,000–8,000 words — to fit comfortably in context)

**Contents:**

**Character profiles** (stable across the whole play):
- Dramatic function and stock type (senex, adulescens, servus callidus, etc.)
- Assigned Cartesia voice ID
- Emotional palette: which emotion tags suit this character
  - e.g. Syrus → `joking/comedic`, `sarcastic`, `triumphant`, `scared` when caught
  - e.g. Demea → `angry`, `frustrated`, `contempt`
- Typical pace, volume, register

**Narrative arc**: Key reversals, dramatic trajectory, resolution

**Scene-by-scene directorial notes** (keyed to Pass 0 scene IDs):
- Dramatic purpose
- Tempo envelope (e.g. "breathless — gaps under 200ms" vs. "slow, melancholic")
- Dominant emotional register
- Key beats and turning points
- Flag long scenes (40+ lines) with suggested internal split points for Pass 2

---

#### Pass 2 — Line-Level Annotation (×N scenes)

- **N separate inference calls**, one per scene
- **Do not use separate passes for emotion, tempo, and rhythm** — these
  dimensions are interdependent. Annotate all dimensions simultaneously.

**Each call receives:**
1. Full performance bible (global context, stable)
2. Last 3–5 lines of the previous scene (boundary overlap)
3. Full current scene (the annotation target)
4. First 1–2 lines of the next scene (resolution target)

> **Key principle**: Show the model the **whole scene at once**, not a
> sliding line-by-line window. The scene is the bounded dramatic unit. The
> few-line overlap only applies at scene *boundaries*. This is the lesson
> from the Norvig/Koralus knowledge graph work: too-granular chunking loses
> relational context. Emotional weight is a relational property — you can't
> annotate a line without seeing the arc it belongs to.

**Output per line:**

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

All four dimensions produced simultaneously within scene context.

---

#### Pass 3 — Audio Stitching

- Generate per-line audio via Cartesia API (voice ID + annotated transcript)
- Insert `pause_before_ms` / `pause_after_ms` silence between clips
- Optional: light room reverb to create shared acoustic space
- Scene transitions: longer pause or distinct audio marker

> Pause values live in the stitching layer, not in Cartesia. Cartesia is
> fully stateless — no memory between calls. The LLM annotates pause timing
> because only the LLM knows whether a line is an interruption (near-zero
> gap), a normal response (short gap), or a dramatic beat (longer gap).

---

### Cartesia Sonic-3 Reference

**Model IDs**: `sonic-3` (stable) · `sonic-3-latest` (beta/testing)

**Emotion control** — two mechanisms:
```
# API parameter
generation_config.emotion = "joking/comedic"

# Inline SSML (preferred for per-line control)
<emotion value="sarcastic"/> Sure, that'll definitely work.
```

Emotion tags are **guidance, not overrides**. The model infers from the
transcript itself; the tag reinforces. Mismatches are ignored.

**Full emotion palette**

Primary (best-supported): `neutral` `angry` `excited` `content` `sad` `scared`

Extended:
`happy` `enthusiastic` `elated` `euphoric` `triumphant` `amazed` `surprised`
`flirtatious` `joking/comedic` `curious` `peaceful` `serene` `calm`
`grateful` `affectionate` `trust` `sympathetic` `anticipation` `mysterious`
`mad` `outraged` `frustrated` `agitated` `threatened` `disgusted` `contempt`
`envious` `sarcastic` `ironic` `dejected` `melancholic` `disappointed` `hurt`
`guilty` `bored` `tired` `rejected` `nostalgic` `wistful` `apologetic`
`hesitant` `insecure` `confused` `resigned` `anxious` `panicked` `alarmed`
`proud` `confident` `distant` `skeptical` `contemplative` `determined`

**Speed / Volume / Laughter:**
```
<speed ratio="1.25"/>   # range 0.6–1.5
<volume ratio="1.5"/>   # range 0.5–2.0
[laughter]              # insert anywhere in transcript
```

**Best emotive voices** (tagged "Emotive" in Cartesia voice library):

| Name   | Voice ID                               |
|--------|----------------------------------------|
| Leo    | `0834f3df-e650-4766-a20c-5a93a43aa6e3` |
| Jace   | `6776173b-fd72-460d-89b3-d85812ee518d` |
| Kyle   | `c961b81c-a935-4c17-bfb3-ba2239de8c2f` |
| Gavin  | `f4a3a8e4-694c-4c45-9ca0-27caf97901b5` |
| Maya   | `cbaf8084-f009-4838-a096-07ee2e6612b1` |
| Tessa  | `6ccbfb76-1fc6-48f7-b71d-91ac6298247b` |
| Dana   | `cc00e582-ed66-4004-8336-0175b85c85f6` |
| Marian | `26403c37-80c1-4a1a-8692-540551ca2ae5` |

Docs: https://docs.cartesia.ai/build-with-cartesia/sonic-3/volume-speed-emotion

---

## Part II: Translation Pipeline

### Why Generate a New Translation

| Source | Status |
|--------|--------|
| Original Latin/Greek | ✅ Fully public domain — use Perseus Digital Library |
| Modern translations (Radice, Ruden, etc.) | ❌ Under copyright |
| Victorian translations (Riley 1853, Fowler 1905) | ✅ Public domain — but these are the bad LibriVox ones |
| LLM-generated translation (human-directed) | ✅ Likely yours — unsettled in law but human editorial direction helps |

Generating a new translation from the source Greek/Latin: avoids copyright,
allows stylistic specification, produces a work you own.

---

### Multi-Model Consensus Approach

Based on the Heidegger *Being and Time* project methodology (the project was
abandoned because the original is still under copyright, but the translation
approach was sound).

**Step 1 — Key terms / global context pass**
All four models (GPT-4o, Gemini, Claude, Grok) read the full source text and
extract: key terms, recurring concepts, character names with connotations,
thematic vocabulary. This becomes the stable global context for all
subsequent translation calls — equivalent to the performance bible on the
audio side.

**Step 2 — Translation pass (per scene, with overlap)**
Each model independently translates one scene at a time, receiving:
- Key terms / global context as preamble
- Style specification (see below)
- Current scene in source language
- Last few lines of previous scene's translation (continuity)
- First few lines of next scene (resolution target)

Same chunking architecture as the audio pipeline: scene as unit, overlap at
boundaries, global context stable throughout.

**Step 3 — Critique round**
Each model reads the other three translations of the same passage and
critiques: what did each get right, what did each miss, where did style drift.

**Step 4 — Consensus pass**
A synthesis call reads all four translations plus critiques and produces a
single coherent translation.

---

### Style Specifications

The style spec is a preamble that travels with every translation call.
**The style decision cascades downstream into TTS annotation** — specify it
once and it propagates through the entire pipeline.

#### Option A — Faux King James / Nietzschean

Archaic English register, "thus" and "verily" and "sayeth," solemn cadence.
Creates productive ironic tension with Lucian's satirical content.

Structurally faithful: Lucian wrote in deliberately archaic Attic Greek —
a dead literary register in his own time — as satirical performance. An
equally artificial English register mirrors the original gesture.

> *And Menippus said unto Charon: Verily I shall not pay thee. For what is
> an obol to one who hath nothing? And Charon was wroth, and gnashed his
> teeth, which were many and terrible.*

TTS implications → measured pacing, longer pauses, higher volume, grandeur
even in mundane moments.

#### Option B — Sitcom (Seinfeld / Friends)

Lucian's Dialogues of the Dead are structurally already a sitcom:
- Fixed location (the underworld)
- Recurring ensemble cast (Charon, Hermes, Diogenes, Menippus)
- Episodic short scenes
- Character-based humor — same personality clash every episode

Casting: Hermes as George Costanza (perpetually aggrieved), Charon as petty
bureaucrat, Menippus as the guy annoyingly comfortable with everything.

TTS implications → fast tempo (`speed: 1.3`), tight gaps (< 150ms),
`joking/comedic` as default emotion.

---

## Part III: Distribution

| Channel | Viable? | Notes |
|---------|---------|-------|
| YouTube | ✅ | Easiest first step, no gatekeeping, monetizable |
| Own website | ✅ | Canonical home everything else points to |
| Internet Archive | ✅ | Underrated — already hosts LibriVox, good SEO |
| Podcast (Apple/Spotify) | ✅ | Via podcast host + RSS, clean path |
| GitHub | ✅ | For the pipeline code, not the audio |
| Audible / ACX | ⚠️ | AI disclosure required, policies tightening |
| LibriVox | ❌ | Explicit human-only policy |

---

## Open Questions / Next Steps

1. **Prototype first**: Run a single scene through the full pipeline before
   committing — suggest *Adelphoe* Act II Scene 1 (Syrus and Demea, strong
   comic material, clear character contrast)

2. **Voice casting**: Browse Cartesia's emotive voice library, cast the stock
   character types (senex, adulescens, servus, meretrix), hold consistent
   across all plays

3. **Translation style decision**: Start with Lucian's *Dialogues of the
   Dead* — shorter, more episodic, better for prototyping the translation
   pipeline

4. **Stitching layer**: Needs to be built — reads JSON annotation output,
   calls Cartesia API per line, inserts pauses, optional room reverb,
   concatenates final audio

5. **Source texts**: Pull from Perseus Digital Library —
   https://www.perseus.tufts.edu — for both Latin (Terence) and Greek (Lucian)

---

## Key Design Principle (from Norvig/Koralus KG work)

> The model needs to operate at the level of meaning, not tokens. Knowledge
> graph edges only exist between nodes that are in context simultaneously.
> Drama annotation has the same topology: emotional weight is a relational
> property. You cannot annotate a line in isolation any more than you can
> extract a KG edge without both nodes in the window.

**Scene = the minimum meaningful chunk. Never go smaller.**
```
