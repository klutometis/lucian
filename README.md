# Lucian

An audio dramatization pipeline for Western Canon classical texts that don't
exist on Audible. Lucian of Samosata's *Dialogues of the Dead* (~165 CE) is
the first work through — last English translation 1905, available only as
flat single-narrator LibriVox readings.

The pipeline turns a Greek source text into a multi-speaker performance via
four stages: read the work, translate it, direct it, perform it. Every stage
is an LLM operating on natural language. No knowledge graphs, no scholarly
apparatus.

## What's in here

```
lucian/
├── plans/                                 # architecture decisions, in order
├── pipeline/
│   ├── bible/build_reading.py            # one-shot read of the source →
│   │                                       reading.json (cast, register,
│   │                                       running gags, tone anchors)
│   ├── translation/                       # 4-model parallel translation
│   ├── casting/build_casting.py          # voice design / voice match per char
│   └── tts/
│       ├── annotator.py                   # per-line acting instructions
│       ├── providers/{hume,elevenlabs}.py # TTS provider abstraction
│       └── render.py                      # one multi-utterance call per scene
└── works/lucian-dialogues-of-the-dead/
    ├── work.yaml                          # thin metadata: genre, language, register
    ├── source/dialogi_mortuorum_grc.xml   # Perseus TEI (Jacobitz 1909)
    ├── bible/reading.json                 # the director's brief
    ├── bible/casting_{hume,elevenlabs}.json
    └── output/{translations,annotations,audio}/
```

## The translation insight

Same Greek line from Dialogue 2 (Croesus to Pluto), four frontier models:

> οὐ φέρομεν, ὦ Πλούτων, Μένιππον τουτονὶ τὸν κύνα παροικοῦντα·
> ὥστε ἢ ἐκεῖνόν ποι κατάστησον ἢ ἡμεῖς μετοικήσομεν ἐς ἕτερον τόπον.

| Model | Translation | Register |
|---|---|---|
| Claude Sonnet 4.6 | "We can't take it anymore, Pluto. This dog Menippus, living next door to us — either move him somewhere else or we're relocating." | theatrical / HOA grievance |
| Gemini 3.1 Pro | "Pluto, we simply cannot tolerate having this dog Menippus as a neighbor. Either move him somewhere else, or we are relocating to another neighborhood." | bureaucratic / formal |
| GPT-5.5 | "We cannot live next door to Menippus here, Pluto. The dog has to move. Put him somewhere else, or we will relocate." | clipped / tabloid headline |
| Grok 4.3 | "We can't stand it, Pluto — this dog Menippus living right next door. Either move him somewhere or we'll relocate." | conversational / colloquial |

Same source, four register choices — none of them strictly "literal."
Translation under an LLM stops being language-to-language and starts being
voice-to-voice. We translate all 30 dialogues × 4 models = 120 takes and
keep them all (`works/.../output/translations/`).

## A/B/C: same scene, three productions

Dialogue 2 (the rich shades file a noise complaint about Menippus) and
Dialogue 22 (Charon shaking down Menippus for the obol) are fully rendered
across three stacks:

| Source | Dialogue 2 | Dialogue 22 |
|---|---|---|
| **A** — LibriVox volunteer reader (Howard Williams 1888 trans) | [`dialogue_02_librivox.mp3`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_02_librivox.mp3) | [`dialogue_22_librivox.mp3`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_22_librivox.mp3) |
| **B** — ElevenLabs v3 dialogue mode (professional library voices, GPT-5.5 translation) | [`dialogue_02_..._elevenlabs.wav`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_02_openai-gpt-5.5_elevenlabs.wav) | [`dialogue_22_..._elevenlabs.wav`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_22_openai-gpt-5.5_elevenlabs.wav) |
| **C** — Hume Octave 1 (voice-from-prompt, GPT-5.5 translation) | [`dialogue_02_..._hume.wav`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_02_openai-gpt-5.5_hume.wav) | [`dialogue_22_..._hume.wav`](works/lucian-dialogues-of-the-dead/output/audio/dialogue_22_openai-gpt-5.5_hume.wav) |

## Pipeline architecture

```
                ┌────────────────────────┐
                │     reading.json       │
                │  (one-shot pre-read    │
                │   of the source)       │
                └───────────┬────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
   ┌────────┐         ┌──────────┐         ┌──────────┐
   │Casting │         │Translate │         │ Annotate │
   │        │         │  (×4     │         │  per-line│
   │ design │         │   models │         │ acting + │
   │  voice │         │ in       │         │  timing  │
   │  per   │         │ parallel)│         │  notes   │
   │  char  │         │          │         │          │
   └────┬───┘         └────┬─────┘         └────┬─────┘
        │                  │                    │
        └────────┬─────────┴────────────────────┘
                 ▼
            ┌────────┐
            │ Render │   one multi-utterance request per scene;
            │  (TTS) │   provider handles inter-line pacing
            └────────┘
```

Each stage is one LLM call (or one per model, for translation):

- **Reading** — Claude or GPT reads all 30 dialogues end-to-end and produces
  cast sketches, voice descriptions, running gags, tone anchors. Replaces
  what would otherwise be a glossary + style guide + character bible.
- **Casting** — Each character's `voice_description` is fed to Hume's
  voice-from-prompt API (or, for ElevenLabs, used as an LLM-assisted
  search against their professional library). Output: `voice_id` per
  character, locked.
- **Translation** — Four frontier models (gpt-5.5, claude-sonnet-4-6,
  gemini-3.1-pro-preview, grok-4.3) translate independently. Inline
  performance tags allowed (`[laughs]`, `[sighs]`, `[pause]`) where
  comic timing benefits.
- **Annotation** — Per-line: speaker, text, natural-language acting
  instruction ("weary sarcasm, slight smile under the surface"), speed,
  optional `trailing_silence_seconds` for explicit comic beats.
- **Render** — All utterances in one multi-speaker request to Hume or
  ElevenLabs. The provider's LLM-native TTS handles inter-line pacing;
  no client-side splicing.

## Stack

- [LiteLLM](https://github.com/BerriAI/litellm) + [Instructor](https://github.com/jxnl/instructor)
  for the four translation/annotation models
- [Hume Octave 1](https://dev.hume.ai/docs/text-to-speech-tts/overview) for
  voice-from-prompt + acting-instruction TTS
- [ElevenLabs v3](https://elevenlabs.io) dialogue mode for the comparison track
- [Perseus Digital Library](https://github.com/PerseusDL/canonical-greekLit)
  for the Greek source text (Jacobitz 1909, public domain)

## Why

LibriVox readings of works like this exist but are flat — one volunteer
narrator doing everyone, no acting, no inter-character pacing. Lucian's
last English translation is from 1905 and out of copyright. There is no
commercial dramatization of him at any quality, anywhere.

This pipeline produces a multi-voice dramatization from a public-domain
Greek source via fresh translation + fresh performance. The translation
is original (not derivative of the 1905 Fowler), the audio is generated.
Per US copyright as of 2026, both layers are clean to publish.

## Status

- All 30 dialogues translated × 4 models = 120 translations in repo
- 2 dialogues fully rendered through Hume + ElevenLabs for A/B/C
- Full-render plan (`plans/05-full-render.md`) for the remaining 28 dialogues
- Cost so far: ~$80 in translations + minimal TTS for the rendered samples
