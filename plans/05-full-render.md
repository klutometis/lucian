# Full Render Plan

Goal: full 30-dialogue translation matrix and Hume audio for the entire
*Dialogues of the Dead*.

## Scope

| Stage | Count | Status |
|---|---|---|
| Reading (cast + register) | 1 | done |
| Casting (Hume voice design) | 48 chars | 7/48 (Menippus, Charon, Hermes, Pluto, Croesus, Midas, Sardanapalus) |
| Translation | 30 dialogues × 4 models = 120 | 4/120 (dialogue 4 × all, dialogue 2 × 2 models) |
| Annotation | 30 × 4 = 120 | 3/120 |
| Render (Hume) | 30 × 4 = 120 | 3/120 |

Models: `openai/gpt-5.5`, `anthropic/claude-sonnet-4-6`,
`gemini/gemini-3.1-pro-preview`, `xai/grok-4.3`.

## Cost estimate

| Bucket | Estimated $ |
|---|---|
| Translation | $40–80 |
| Annotation (gpt-5.5 across 120 calls) | $20–40 |
| Hume voice design (~41 remaining) | <$5 |
| Hume synthesis (120 × ~5K chars on creator tier) | $100–180 |
| **Total** | **$200–300** |

## Phasing

We split into independent phases so we can pause and inspect between them.

### Phase 1 — Translate everything
- Run all 4 models across all 30 dialogues.
- 120 outputs at `output/translations/dialogue_NN_<model>.json`.
- Skip-if-exists: already-translated combinations are not redone.
- Exit. Human reads through the variety; gets a sense of which models
  win for which dialogue types before committing to render cost.

### Phase 2 — Cast everything
- Run `build_casting.py --provider hume` with no `--only` filter.
- Designs voices for the remaining ~41 cast members.
- One-time, locked.

### Phase 3 — Annotate everything
- Run annotator over all 4 translations × 30 dialogues = 120 annotations.
- Skip-if-exists.
- Output: `output/annotations/dialogue_NN_<translation_model>_annotated.json`.

### Phase 4 — Render everything
- Hume only (per current decision; ElevenLabs takes 4× without proportional payoff).
- 120 audio files at `output/audio/dialogue_NN_<translation_model>_hume.wav`.
- Skip-if-exists.

Phases are independent. Each can be re-run; outputs are cached.

## Infrastructure

What we need to add for batch operation:

1. **Orchestrator script** `pipeline/run_phase.py` with phase argument:
   - `--phase translate` → translate(every dialogue × every model)
   - `--phase cast` → run casting workflow
   - `--phase annotate` → annotate every (dialogue, translation) combo
   - `--phase render` → render every (dialogue, translation) combo
   - All phases skip-if-exists. Resumable.
   - `--start NN --end NN --models gpt-5.5,claude-sonnet-4-6` for narrowing scope.

2. **Concurrency.** Per phase, optional `--concurrency N`:
   - Translation: 4–8 concurrent (different providers OK; same provider rate-limited).
   - Annotation: 2–4 concurrent (single provider).
   - Render: 2 concurrent (Hume rate limits).

3. **Cost tracking.** Each phase logs token count + estimated cost so far.

We're not building all of this for Phase 1 — translation is simple enough
to do with the existing `pipeline/translation/driver.py` plus a shell
loop. Build the orchestrator for Phase 3+ where the matrix gets bigger
and concurrency starts to matter.

## Open questions to resolve between phases

- After Phase 1: does any model produce dramatically better translations
  than the others? If yes, render that model only. If no, render all 4
  for full A/B/C optionality (~$200 of Hume, vs. ~$50 for one model).
- After Phase 2: are any auto-cast voices wrong? Re-cast specific
  characters with a different `voice_description` if the result misses.
- After Phase 4: for a small set of "winner" dialogues, also generate
  ElevenLabs renders for direct comparison to LibriVox baselines.

## What we're not building yet

- Cross-dialogue consistency QA (post-hoc check that Menippus-as-Cynic
  reads consistent across dialogues).
- ElevenLabs full render. Defer.
- Synthesis pass (combining best parts of multiple model translations).
  Per `02-translation-philosophy.md`: only triggered after listening, only
  when justified.
