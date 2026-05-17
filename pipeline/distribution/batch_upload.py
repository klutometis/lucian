"""
Batch upload: read an episode manifest, generate artwork for each
entry, upload each episode to Buzzsprout. Idempotent — skips entries
whose title already exists on the podcast.

Manifest schema:
[
  {
    "episode_number": 1,
    "audio_file": "works/.../dialogue_01_*.wav",
    "title": "...",
    "description": "...",
    "artwork_description": "..."
  },
  ...
]

Usage:
    uv run pipeline/distribution/batch_upload.py
    uv run pipeline/distribution/batch_upload.py --only 1,2,3
    uv run pipeline/distribution/batch_upload.py --skip-artwork  # use show cover
    uv run pipeline/distribution/batch_upload.py --public         # publish immediately
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from images.generate import generate as generate_image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from upload_buzzsprout import upload, PODCAST_ID, USER_AGENT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def existing_episode_numbers(podcast_id: str = PODCAST_ID) -> dict[int, str]:
    """Return {episode_number: title} already on the podcast."""
    token = os.environ["BUZZSPROUT_API_TOKEN"]
    resp = requests.get(
        f"https://www.buzzsprout.com/api/{podcast_id}/episodes.json",
        headers={
            "Authorization": f"Token token={token}",
            "User-Agent": USER_AGENT,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return {ep["episode_number"]: ep["title"]
            for ep in resp.json() if ep.get("episode_number")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path,
                    default=PROJECT_ROOT / "works/lucian-dialogues-of-the-dead/output/episode_manifest.json")
    ap.add_argument("--artwork-dir", type=Path,
                    default=PROJECT_ROOT / "works/lucian-dialogues-of-the-dead/output/images")
    ap.add_argument("--only", help="Comma-separated episode numbers (default: all)")
    ap.add_argument("--skip-artwork", action="store_true",
                    help="Don't generate per-episode artwork; show cover used instead")
    ap.add_argument("--public", action="store_true",
                    help="Publish immediately (default: upload as private draft)")
    ap.add_argument("--force-artwork", action="store_true",
                    help="Regenerate artwork even if file exists")
    args = ap.parse_args()

    entries = json.loads(args.manifest.read_text())
    if args.only:
        wanted = {int(n) for n in args.only.split(",")}
        entries = [e for e in entries if e["episode_number"] in wanted]

    seen = existing_episode_numbers()
    log.info(f"podcast already has {len(seen)} episodes")

    for entry in entries:
        n = entry["episode_number"]
        title = entry["title"]
        if n in seen:
            log.info(f"[{n:02d}] already uploaded as {seen[n]!r}, skipping")
            continue

        audio = PROJECT_ROOT / entry["audio_file"]
        if not audio.exists():
            log.warning(f"[{n:02d}] missing audio: {audio}")
            continue

        # Generate artwork
        artwork = None
        if not args.skip_artwork:
            artwork = args.artwork_dir / f"episode_{n:02d}.png"
            if artwork.exists() and not args.force_artwork:
                log.info(f"[{n:02d}] artwork cached → {artwork.name}")
            else:
                log.info(f"[{n:02d}] generating artwork...")
                try:
                    generate_image(
                        prompt=entry["artwork_description"],
                        out=artwork,
                        aspect_ratio="1:1",
                        image_size="2K",
                    )
                except Exception as e:
                    log.error(f"[{n:02d}] artwork failed: {e}; uploading without")
                    artwork = None

        # Upload
        try:
            upload(
                audio=audio,
                artwork=artwork,
                title=title,
                description=entry["description"],
                episode_number=n,
                private=not args.public,
            )
        except Exception as e:
            log.error(f"[{n:02d}] upload failed: {e}")


if __name__ == "__main__":
    main()
