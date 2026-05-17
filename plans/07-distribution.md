# Distribution

How to actually publish Lucian once the audio (and eventually video) is
finished. Realistic 2026 channel landscape, where the constraints sit,
and a concrete recommended path.

## What we have to distribute

- 30 dialogues × 1 canonical audio per dialogue (Opus → Hume) = 78 min of audio
- Per-dialogue translations + annotations (research artifacts, optional)
- Eventually: per-dialogue animated video (per plan 06)

## Channel landscape

### Viable

**Podcast RSS** — *the highest-leverage path.*

A single RSS feed flows to Apple Podcasts, Spotify, Amazon Music, Audible
(as podcast — Audible has accepted podcasts since 2022), Pandora, iHeart,
all the long-tail aggregators. One upload, dozens of platforms.

Each dialogue becomes one episode. 30 episodes = a season. ~3–5 min each.

Hosts:
- **Buzzsprout** — ~$12/mo on entry tier, great UX
- **Transistor** — ~$19/mo, stronger analytics
- **Spotify for Creators** — free, Spotify-owned (so less platform optionality)
- **Podbean** — free tier

Audible distribution via this path doesn't trip the human-narration policy
that blocks AI on the ACX (audiobook) side — Audible's podcast acceptance
has no AI-specific restriction.

**YouTube**

Broadest reach, no gatekeeping, fastest to publish. The catch: audio-only
videos with static images underperform; YouTube's recommendation system
favors video. This is where the cinematography pass from plan 06 earns
its keep — animated lip-synced visuals turn a static-image upload into
content people actually watch.

AI content disclosure required as of 2026. Label honestly. Not
monetization-blocking; algorithm-sensitive.

**Internet Archive**

Free hosting, permanent URLs, parallel listing to the existing LibriVox
upload. On-brand: we're explicitly making the "better LibriVox." Listing
beside it is rhetorical positioning, not just hosting. Good SEO for
"Lucian audio" searches because the LibriVox entry already pulls traffic.

**Own site (GitHub Pages / Netlify / Vercel)**

The canonical landing page that all other channels link back to.
`klutometis.github.io/lucian` is already free since the repo is public.
Static page with embedded audio + links to each platform + a "how this
was made" section linking back to the pipeline.

Especially valuable as a production-transparency artifact — the *making*
of this thing is part of the work.

### Hard / not happening

**Audible audiobook proper (via ACX).** Three blockers:
- ACX retains a human-narration preference; AI submissions get "voice
  quality" rejections that read like polite refusals.
- Audible launched their own AI narration program in 2025 (their tool,
  their royalty) which is incompatible with submitting external AI audio.
- 30 short dialogues isn't an audiobook shape; ACX wants longer
  continuous works.

You can sidestep all three by publishing as podcast — which lands on
Audible anyway, just in a different category. Don't fight this.

**LibriVox.** Explicit human-only policy. Not happening, and on principle
that's fine — they exist for a different reason.

## Recommended path

Maximum leverage on minimum effort:

1. **Podcast RSS via Buzzsprout** (~$12/mo). 30 episodes pre-loaded.
   Auto-distributes to Apple Podcasts, Spotify, Amazon Music, Audible,
   etc.

2. **Internet Archive** upload. Free, on-brand, parallel listing to the
   LibriVox version. Permanent URL.

3. **GitHub Pages site** at the existing repo. Landing page with audio
   embeds, link out to all platforms, "how this was made" section linking
   back to the plans and code.

4. **YouTube channel**, but only after building the cinematography pass
   from plan 06. Static-image audio on YouTube is dead-on-arrival;
   visuals are the entry ticket. Until then, hold.

Cost: ~$12/mo recurring (podcast host). Everything else free.

## Production prep before publishing

Things to nail down before the first episode goes live:

**Intro / outro per episode.** ~10–15 seconds: "Lucian's Dialogues of the
Dead, dialogue 2: The Kings Complain to Pluto. From the Greek of Lucian
of Samosata, second century CE." Hume-generated, in a separate
narrator voice distinct from the cast.

Closer: "This recording is voiced and translated by AI from the original
Greek. The source text is public domain; the translation is original.
Production at github.com/klutometis/lucian."

**Cover art.** That dialogue-2 image is the natural channel cover (the
sitcom premise is in the frame). One generic cover for the show + one
custom per episode would be ideal; one for the show is the minimum.

**Show notes** per episode:
- Greek title + English title (the actual scene title)
- Synopsis (3–4 sentences)
- Cast list with character → voice name (the Hume voice IDs are
  numeric but we named them `lucian-menippos`, `lucian-charon`, etc.;
  the "name" is the production credit)
- Source citation (Perseus Digital Library, Jacobitz 1909 edition)
- Link to the GitHub repo

**AI disclosure.** Honest, prominent, in the description on every
platform. Not a footnote.

## Sequencing

To avoid launching half-finished:

1. **Week 1: Setup.** Buzzsprout account, GitHub Pages site scaffold,
   Internet Archive account. Cover art generated. Intro/outro audio
   recorded (or Hume-generated). Show description, hosting metadata.

2. **Week 2: First 3 episodes.** Upload dialogues 2, 4, 22 — the ones
   we know land well. Get the workflow tight. Promote nowhere; this is
   the soft launch.

3. **Week 3: Full season.** Upload remaining 27 episodes weekly or
   biweekly. Each episode gets show notes + a tweet-length description.

4. **Week 4+: YouTube** if cinematography pass is ready. Otherwise
   keep audio-only on the podcast circuit and re-evaluate later.

## What we're not deciding yet

- **Monetization.** Free across all channels for v1. Revisit only if it
  gets traction; podcast ad-supported is the obvious follow-up but not
  worth optimizing for at zero listeners.
- **Translations into other languages.** The pipeline supports it
  (the reading + translation prompts are language-agnostic). Defer
  until the English version has traction.
- **Subsequent works.** Terence, Plautus, Lucretius. The pipeline is
  built for them. But ship Lucian first; one finished thing beats four
  half-things.

## Open questions

- **Episode cadence.** All 30 at once (binge-friendly), weekly (sustained
  attention), or hybrid (first 3 immediate, then weekly)? Hybrid is
  probably right — gives algorithm time to learn the show without
  rationing artificially.
- **Series naming.** "Lucian's Dialogues of the Dead" is literal and
  searchable but boring. "The Underworld Sitcom" is sharper but
  potentially misleading. Probably go literal + a tagline:
  *"Lucian's Dialogues of the Dead — the underworld as workplace comedy."*
- **Single voice for intro/outro.** Hume design a new voice — narrator,
  warm, slightly knowing. Not part of the cast.
