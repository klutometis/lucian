# Cinematography Pass

Extend the audio pipeline with a visual track. Goal: animated video of
each dialogue. LLM directs the shots; Nano Banana renders the frames;
Hedra animates them against the existing audio.

## Architecture

```
existing                                  new
─────────                                 ────
reading.json    ─────────────────────────► appearance per character
       │                                          │
       ▼                                          ▼
   translation                              cinematography
       │                                    (per dialogue: shot list)
       ▼                                          │
   annotation ──────────────────────────────────► │
       │                                          │
       ▼                                          ▼
   audio render ──┬──────────────────────► frame generation
                  │                         (Nano Banana with ref image)
                  │                                │
                  │                                ▼
                  └──────────────────────► animation per shot
                                           (Hedra: image + audio slice)
                                                  │
                                                  ▼
                                              stitch to video
                                              (ffmpeg, cut on
                                               per-line boundaries)
```

## Five new stages

### 1. Appearance (one-time, work-level)

Extends the reading with structured visual descriptions per character.
The model that built `reading.json` produces these in a parallel pass,
or we add them to `reading.json` itself in a re-read.

Example output (`bible/appearance.json`):

```json
{
  "kroisos": {
    "physical": "Lydian king, 50s, olive complexion, dark curled hair
      and beard, kohl-rimmed eyes, weighty build",
    "costume": "layered gold-thread robes with crimson accents, golden
      torc, heavy rings, twisted gold crown over the hair",
    "props": "small ornamental casket (the lost-fortune motif)"
  },
  "menippos": {
    "physical": "as a literal dog — scrappy gray-and-tan terrier mix,
      one upright ear and one half-down, intelligent eyes, knowing
      half-smile",
    "costume": "leather collar with a small brass lantern hanging from it",
    "notes": "Lucian's joke made flesh — the Cynic philosopher rendered
      as κύων (kyon, 'dog'). All dialogue lines delivered as the dog."
  }
}
```

Reused across all 30 dialogues. Built once, locked. ~$0.50 LLM.

### 2. Cinematography (per dialogue)

LLM reads annotation + appearance and produces a shot list, binding
each shot to specific lines:

```json
{
  "dialogue_id": 2,
  "shots": [
    {"shot_id": "s1",
     "type": "wide_establishing",
     "frame_for_lines": [0],
     "duration_hint_s": 4,
     "description": "Throne room of Hades. Pluto on dark stone throne
        with trident, Persephone beside him holding pomegranate.
        Croesus, Midas, Sardanapalus kneeling in foreground. Menippus-
        the-dog sits to the right with lantern collar."},
    {"shot_id": "s2",
     "type": "medium",
     "frame_for_lines": [1, 2],
     "description": "Croesus and Midas, waist-up, mid-complaint."},
    {"shot_id": "s3",
     "type": "closeup",
     "frame_for_lines": [3],
     "description": "Pluto's face, mildly puzzled, beard catching the
        torchlight."},
    {"shot_id": "s4",
     "type": "reaction",
     "frame_for_lines": [4],
     "description": "Menippus-the-dog tilting head, mid-laugh, lantern
        swaying."}
  ]
}
```

Shot vocabulary the cinematographer should know:
- `wide_establishing` — whole scene, all characters in frame
- `wide` — full bodies, multiple characters
- `medium` — waist-up, 1–3 characters
- `closeup` — head-and-shoulders, one character
- `extreme_closeup` — eyes, mouth, hands, an object
- `over_shoulder` — back of one character, focus on the one being addressed
- `reaction` — cut to a listener responding
- `insert` — an object (the obol, a sealed will, etc.)

~$0.20 LLM per dialogue. Saved as `output/cinematography/dialogue_NN_<model>_shots.json`
where `<model>` is the translation model whose annotation it was built from.

### 3. Frame generation (Nano Banana Pro)

For each shot, generate the still that will be animated. Inputs:
- The shot description
- Appearance descriptions for the characters in frame
- One or more reference images (the original establishing image; previous
  shots from the same dialogue for continuity)

Nano Banana Pro's strength is the reference-image flow — given a base
image, generate consistent characters across multiple shots. That's the
whole reason this pipeline works at all.

Saved as `output/frames/dialogue_NN_shot_sX.png`.

~$0.10–0.30 per frame; 5–15 frames per dialogue.

### 4. Animation (Hedra)

Per shot, slice the existing Hume audio to cover `frame_for_lines`, then
send (still frame + audio slice) to Hedra. Hedra does audio-driven
lip-sync over the frame.

Constraints from Hedra:
- Most models cap at ~8s per generation. Omnia supports longer.
- Single character lip-synced per clip; multi-character framing has only
  the speaking character animated, others static. That's fine for our
  cut-between approach.
- Cost roughly $0.20–0.50 per clip.

Saved as `output/video_clips/dialogue_NN_shot_sX.mp4`.

### 5. Stitch

Concatenate per-shot clips in order, sync against the original full-audio
WAV (cuts on the line boundaries the cinematography pass already declared).
Optional: light crossfades, occasional camera-move-on-still effects via
ffmpeg for wide shots that play long.

Saved as `output/video/dialogue_NN_<translation_model>_hume_hedra.mp4`.

## Cost / time per dialogue

| Stage | Cost | Time |
|---|---|---|
| Cinematography LLM | ~$0.20 | ~30s |
| Nano Banana frames (~10) | ~$2 | ~5 min |
| Hedra clips (~10) | ~$3 | ~5 min |
| Stitching | $0 | ~30s |
| **Per dialogue** | **~$5–8** | **~10–15 min** |
| **All 30 dialogues** | **~$150–250** | **~6–8 hours** |

Costs scale with line count more than dialogue count — long dialogues
like 10 (the boarding scene, ~30 lines) and 27 (Cynics watching new
arrivals, ~21 lines) will be 2–3× the average.

## Phasing

Same shape as the audio pipeline:

1. **Appearance pass** — extend reading with visual descriptions.
   One LLM call, ~$0.50, locked.

2. **Cinematography for dialogue 2 only.** Read the shot list as text.
   Does the model think about framing usefully — or is it bland
   "medium shot, character speaks"? Iterate the prompt if needed before
   scaling. ~$0.20.

3. **Frame generation for dialogue 2 only.** Use the existing dialogue-2
   image as the reference seed. Generate ~10 frames. Look at them
   together — do the characters stay consistent? Is the room consistent?
   ~$2.

4. **Hedra animation for dialogue 2 only.** ~10 clips at 5–8s. Listen +
   watch. ~$3.

5. **Stitch into one 1:35 video.** Cut against the existing Hume audio.
   If it works, scale to all 30. If not, identify which stage failed.

Total prototype cost: ~$6 + ~1 hour. Then decide whether to scale.

## What we're not building yet

- **Animated camera moves.** Hedra animates the character; the frame
  itself is static apart from light Ken-Burns pan effects we'd add in
  ffmpeg. Real camera movement (dolly, push-in, parallax) is its own
  problem and Veo/Sora-class work; defer.
- **Multi-character animation per clip.** Hedra (and most tools) lip-sync
  one character per clip. Multi-character scenes get one animated speaker
  with the rest static in frame. The cut-between-shots approach is the
  workaround. Good enough for v1.
- **Synced eyelines.** If shot A frames Croesus looking left and shot B
  cuts to Pluto's reaction, Pluto should be on Croesus's right (180-degree
  rule). The cinematographer LLM should be told about this; will it
  actually nail it? Open question; will see in practice.
- **Voice-of-character vs. voice-of-narrator differentiation.** Lucian
  is all dialogue — no narrator. Not an issue for this work. For
  Lucretius (didactic poem) we'd need to model "the narrator" as a
  shot too.

## Output directory after extension

```
works/lucian-dialogues-of-the-dead/
├── bible/
│   ├── reading.json
│   ├── appearance.json          # new: per-character visual
│   ├── casting_hume.json
│   └── casting_elevenlabs.json
└── output/
    ├── translations/
    ├── annotations/
    ├── critiques/
    ├── audio/
    ├── cinematography/          # new: shot lists
    ├── frames/                  # new: stills
    ├── video_clips/             # new: per-shot animated mp4s
    └── video/                   # new: stitched dialogue videos
```

## Reproducibility for other works

Same as the audio pipeline (per plan 04). The cinematography prompt is
parameterized by the work metadata + appearance — for Terence we'd get
Roman-comedy stock characters; for Vergil we'd get pastoral landscapes.
The shot vocabulary is universal cinema grammar; the cinematographer
LLM just needs to know the genre to weight shot choices appropriately.

## Open questions to resolve during the prototype

- **Reference image strategy.** Pass the establishing shot to every
  Nano Banana call, or chain references (each new shot also sees the
  previous one)? Chaining gives continuity but compounds drift. Test both.
- **Audio slicing.** Per-line slices, per-shot slices (multiple lines
  in one shot), or one continuous audio with shot cuts? Hedra likely
  wants per-clip audio. Per-shot is cleanest.
- **Hedra cap workaround.** When a shot covers >8s of audio, do we
  break it into multiple Hedra clips of the same frame, or generate a
  near-duplicate second frame from the same shot description? Probably
  multiple clips of the same frame — character continuity is the
  expensive part.
