# Translation Philosophy

## Why Lucian is not Heidegger

The Heidegger translation pipeline (4 models translate → 4 models critique
→ vote → synthesize) was machinery for a specific epistemic problem:
philosophical precision where *Dasein* vs "Being-there" carries centuries
of interpretive freight. Its output was as much "the reasoning trace" as
"the translation" — that's why *Four Minds on Being* was a deliverable.

Lucian is a different regime. The artifact is **audio that lands as funny.**
There is no philosophical truth-condition. Ground truth is "did Hermes' line
get a laugh in Leo's voice with that 150ms gap?" — knowable only by listening.

## Three concrete problems with porting critique-and-vote

1. **Convergence to safe averages.** Models critiquing each other equilibrate
   on "least objectionable." Sitcom comedy needs voice and risk. In our
   dialogue 4 test, Grok was the punchiest ("fudging the fares," "outta
   line"); a synthesis pass would smooth out exactly the edge that makes it
   work.

2. **Critique can't access the dimension that matters.** A model reading
   "Hey Charon, let's settle up" vs "Let's settle up, ferryman" can't tell
   which lands better when delivered by Leo at speed=1.25 with 150ms
   pause. That's a sound-level property. Text-level critique debates
   something orthogonal to the artifact.

3. **Cost asymmetry.** Heidegger committed to one rendering of *Dasein* in
   advance and lived with it for thousands of paragraphs. We can A/B
   compare cheaply in audio. Production surfaces the answer; we don't have
   to deliberate in advance.

## Phasing

```
Phase 1 — Generate (cheap, parallel)
  Each model translates independently end-to-end. No critique.
  Save all 4. Distinct voices, distinct registers, distinct risks.

Phase 2 — Produce audio (one or two takes per dialogue)
  Pick favorite(s), run through annotation + stitching, listen.

Phase 3 — Informed synthesis (only when justified)
  Triggered by human listening notes — "Grok's punchiness lines 1-5,
  Claude's voicing on Hermes' rant." Synthesis becomes "execute these
  specific human-curated decisions," not "average four texts."

Phase 4 — Cross-dialogue consistency (the bible layer)
  The thing that should be consensus-built up front isn't the
  per-dialogue translation — it's the CASTING + CHARACTER VOICE BIBLE.
  Hermes must sound like Hermes everywhere. Authored once with human
  review, then locked.
```

## Where critique-revise still has value (narrower than Heidegger)

- **Linting, not aesthetics.** A single self-review pass (one model
  checking its own output) catches literal errors: mistranslated word,
  misattributed line, name inconsistency, tone drift. Cheap. Worth having.
- **Cross-dialogue consistency check.** Once N dialogues are translated,
  flag "Menippus' voice drifted between dialogues 3 and 17." Post-hoc QA,
  not pre-commitment debate.

What we don't get and don't need: defensible scholarly reasoning. Nobody
will publish a footnote on why we said "fudging the fares."

## Division of labor

| Layer                       | Approach                              | Why                              |
|-----------------------------|---------------------------------------|----------------------------------|
| Translation (per dialogue)  | 4 models in parallel, no critique     | Preserve voice diversity         |
| Self-review (per translation) | One pass, same model                | Catch literal errors             |
| Casting bible (global)      | Built once, human-locked              | Cross-dialogue consistency       |
| Performance bible (per dialogue) | One model, references casting bible | Stable per-scene direction    |
| Annotation (per dialogue)   | One model                             | Per-line emotion/tempo           |
| Audio                       | Cartesia                              | Ground truth                     |
| Synthesis (rare)            | Triggered by human listening notes    | Only when there's something to synthesize |

## Action items

- Default translation pipeline runs all 4 models in parallel; no critique pass
- Build casting bible as separate, global, locked artifact (next iteration)
- Treat self-review as optional linting, not part of core pipeline
- Defer synthesis machinery until we have audio takes to compare
