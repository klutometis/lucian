# Distribution Checklist

Practical step-by-step for getting the Buzzsprout-hosted podcast onto
the major listening platforms. Verified against current (2026) docs.

## Your RSS feed URL

`https://feeds.buzzsprout.com/2618366.rss`

This is the source of truth. Every platform below ingests this URL.

## Buzzsprout plan first — decide before distributing

You're on the **free tier**. The constraints:

- 2 hours of upload per month (we used ~78 min, fine)
- **Episodes auto-delete 90 days after upload** — confirmed at
  https://www.buzzsprout.com/help/231

If you submit to Apple/Spotify/Amazon now and let the 90 days lapse,
the audio files vanish and the directory listings break.

**Real Buzzsprout pricing** (2026, https://www.buzzsprout.com/pricing):

| Plan | $/mo (annual) | Upload hours/year |
|---|---|---|
| Free | $0 | 2/mo, 90-day expiration |
| Audio | $15 | 72 |
| Audio + Video | $25 | 72 + video on Apple Podcasts |
| Archive | $5 | keeps episodes live, no new uploads |

For a 78-minute completed show that you want to stay published, the
**Archive plan at $5/mo** is the right call — episodes stay live, you
don't need additional upload capacity. Switch from Free → Archive
before the 90-day clock matters.

(My earlier "$12/mo" was wrong — that was the Hume Creator plan we
upgraded, not Buzzsprout.)

## Step 1 — Apple Podcasts (highest priority)

1. Go to **https://podcastsconnect.apple.com**
2. Sign in with your Apple ID (any existing Apple ID works; no special
   developer account needed)
3. Accept the Podcaster Agreement (one-time)
4. Click the **+** in the top-left → **New Show** → **Add a show with
   an RSS feed**
5. Paste the feed URL
6. Apple sends a verification email to the address in the RSS feed's
   `<itunes:owner>` tag (probably your Buzzsprout email)
7. Click the verification link; return to Podcasts Connect
8. Complete the show metadata Apple prompts for (some pre-fills from
   the RSS — title, category, language; you might tweak)
9. Click **Submit for review**
10. Apple reviews; typically 0–48 hours, sometimes up to a week

Once approved, "Lucian's Dialogues of the Dead: The Underworld Sitcom"
is searchable in Apple Podcasts globally.

## Step 2 — Spotify (easy, fast)

1. Go to **https://creators.spotify.com**
2. Sign in with your Spotify account (free Spotify works)
3. Click your avatar / hamburger → **Add a new show**
4. Choose **Find an existing show** → **Somewhere else**
5. Paste the feed URL
6. Spotify sends a verification code to the email in the RSS feed
7. Enter the code; show is approved within hours, often minutes

## Step 3 — Amazon Music + Audible (one submission, two platforms)

Amazon Music for Podcasters auto-distributes to both Amazon Music and
Audible.

1. Go to **https://podcasters.amazon.com/submit-rss**
2. Sign in with your Amazon account (your regular shopping account)
3. Paste the feed URL → click submit
4. Amazon sends a verification email
5. Confirm; show appears on Amazon Music and Audible within ~24-48
   hours

Audible-as-podcast is the back door we discussed — your show lists on
Audible without going through ACX's audiobook flow.

## Step 4 — YouTube Music (optional but worth it)

Since Google Podcasts shut down in 2024, YouTube Music is where podcast
listeners in the Google ecosystem now live.

Two paths:

- **Buzzsprout integration** — in your Buzzsprout admin go to
  **Directories** tab → enable YouTube Music. Buzzsprout handles the
  submission via their partnership.
- **Manual** — YouTube Studio → Content → Podcasts → "Set up your
  podcast" if you have a YouTube channel.

The Buzzsprout integration is one click; do that.

## Step 5 — iHeart, Pandora, etc. (the long tail)

In your Buzzsprout admin → **Directories** tab, there's a one-click
submit list for everything else. Most of these don't get meaningful
traffic but submission is free and trivial:

- iHeart Radio
- Pandora
- Podchaser
- TuneIn
- Player.fm
- Deezer
- Castbox

Click them all; they're all roughly equivalent submissions.

## Step 6 — Independent listings (separate from RSS)

These are not RSS-driven; you set them up manually if you want:

- **Internet Archive** (https://archive.org) — upload the WAVs directly.
  Free permanent hosting; parallel listing to the existing LibriVox
  version of Lucian. Good SEO. ~30 minutes of work.
- **GitHub Pages** — the repo at github.com/klutometis/lucian is already
  public. Could add a static landing page at klutometis.github.io/lucian
  with audio embeds + links to all the above. Optional, but it's the
  "how it was made" artifact that ties everything together.

## Realistic timeline

- **Today (~30 min total)**: upgrade Buzzsprout to Archive ($5/mo);
  submit to Apple Podcasts (Spotify, Amazon), click through Buzzsprout
  Directories for the long tail.
- **24–48 hours**: Spotify live, Amazon live, YouTube Music live.
- **2–7 days**: Apple Podcasts approved and searchable.
- **Optional later**: Internet Archive upload, GitHub Pages landing.

## What I previously got wrong

- "Apple/Spotify/Audible propagation: ~24 hours" — that's the
  propagation **after submission**. Submission itself is manual per
  platform and requires accounts.
- "$12 (one month Starter)" Buzzsprout — wrong. The actual Audio plan
  is $15/mo annual; Archive (which is what we actually want) is $5/mo.
  $12 was the Hume Creator upgrade.
- Buzzsprout free plan is fine for uploading and proving the pipeline,
  but the 90-day expiration is real. Don't list the show on Apple/etc.
  until you've decided to upgrade or the listings break in 3 months.
