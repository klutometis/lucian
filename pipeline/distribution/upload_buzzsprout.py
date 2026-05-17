"""
Upload an episode to Buzzsprout via the API.

Usage:
    uv run pipeline/distribution/upload_buzzsprout.py \\
      --audio path/to/audio.wav \\
      --artwork path/to/cover.png \\
      --title "Episode title" \\
      --description "Episode description" \\
      --episode-number 1 \\
      --private        # uploads as draft; flip in UI to publish
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

PODCAST_ID = os.environ.get("BUZZSPROUT_PODCAST_ID", "2618366")
USER_AGENT = "lucian-pipeline/1.0 (github.com/klutometis/lucian)"


def publish(
    episode_id: int,
    published_at: str | None = None,
    podcast_id: str = PODCAST_ID,
) -> dict:
    """Flip an existing episode from private to public.
    Optionally set published_at to a specific ISO8601 timestamp."""
    token = os.environ["BUZZSPROUT_API_TOKEN"]
    url = f"https://www.buzzsprout.com/api/{podcast_id}/episodes/{episode_id}.json"
    payload = {"private": False}
    if published_at:
        payload["published_at"] = published_at
    log.info(f"PUT {url} ({payload})")
    resp = requests.put(
        url,
        headers={
            "Authorization": f"Token token={token}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    log.info(f"  published: id={body.get('id')} private={body.get('private')} published_at={body.get('published_at')}")
    return body


def upload(
    audio: Path,
    title: str,
    description: str,
    artwork: Path | None = None,
    episode_number: int | None = None,
    season_number: int | None = None,
    private: bool = True,
    explicit: bool = False,
    podcast_id: str = PODCAST_ID,
) -> dict:
    token = os.environ["BUZZSPROUT_API_TOKEN"]
    url = f"https://www.buzzsprout.com/api/{podcast_id}/episodes.json"

    data = {
        "title": title,
        "description": description,
        "private": str(private).lower(),
        "explicit": str(explicit).lower(),
        "email_user_after_audio_processed": "false",
    }
    if episode_number is not None:
        data["episode_number"] = str(episode_number)
    if season_number is not None:
        data["season_number"] = str(season_number)

    files = {"audio_file": (audio.name, audio.read_bytes(), "audio/wav")}
    if artwork:
        mime = "image/png" if artwork.suffix.lower() == ".png" else "image/jpeg"
        files["artwork_file"] = (artwork.name, artwork.read_bytes(), mime)

    log.info(f"POST {url}")
    log.info(f"  audio:    {audio} ({audio.stat().st_size // 1024} KB)")
    if artwork:
        log.info(f"  artwork:  {artwork} ({artwork.stat().st_size // 1024} KB)")
    log.info(f"  title:    {title}")
    log.info(f"  private:  {private}")

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Token token={token}",
            "User-Agent": USER_AGENT,
        },
        data=data,
        files=files,
        timeout=600,
    )
    if resp.status_code not in (200, 201):
        log.error(f"  HTTP {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
    body = resp.json()
    log.info(f"  saved → id={body.get('id')} ({body.get('title')})")
    return body


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=False)

    pub = sub.add_parser("publish", help="Flip an existing episode public")
    pub.add_argument("--episode-id", type=int, required=True)

    # Default: upload
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--artwork", type=Path)
    ap.add_argument("--title")
    ap.add_argument("--description")
    ap.add_argument("--episode-number", type=int)
    ap.add_argument("--season-number", type=int)
    ap.add_argument("--public", action="store_true",
                    help="Publish immediately (default: upload as private draft)")
    ap.add_argument("--explicit", action="store_true")
    args = ap.parse_args()

    if args.cmd == "publish":
        publish(args.episode_id)
        return

    if not args.audio or not args.title or not args.description:
        ap.error("--audio, --title, and --description are required for upload")

    upload(
        audio=args.audio,
        artwork=args.artwork,
        title=args.title,
        description=args.description,
        episode_number=args.episode_number,
        season_number=args.season_number,
        private=not args.public,
        explicit=args.explicit,
    )


if __name__ == "__main__":
    main()
