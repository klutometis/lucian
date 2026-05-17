"""
Publish all private-draft episodes with sequential published_at timestamps,
so the public feed orders cleanly by episode_number.

Usage:
    uv run pipeline/distribution/batch_publish.py
    uv run pipeline/distribution/batch_publish.py --start "2026-05-18T10:00:00-04:00"
    uv run pipeline/distribution/batch_publish.py --interval-minutes 30
"""

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from upload_buzzsprout import publish, PODCAST_ID, USER_AGENT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def list_episodes(podcast_id: str = PODCAST_ID) -> list[dict]:
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
    return resp.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start",
                    help="ISO8601 timestamp for episode 1 (default: now). "
                         "Episodes 2..N get this + (N-1) * interval.")
    ap.add_argument("--interval-minutes", type=int, default=1,
                    help="Spacing between sequential episode published_at "
                         "timestamps (default: 1 minute). Use ~10080 for "
                         "weekly cadence.")
    ap.add_argument("--only", help="Comma-separated episode numbers (default: all private)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    episodes = list_episodes()
    if args.only:
        wanted = {int(n) for n in args.only.split(",")}
        episodes = [e for e in episodes if e.get("episode_number") in wanted]

    private = [e for e in episodes if e.get("private")]
    private.sort(key=lambda e: e.get("episode_number") or 0)
    log.info(f"{len(private)} private episodes queued")

    if args.start:
        start = datetime.fromisoformat(args.start)
    else:
        # Default: episode 1 gets "now", others sequential.
        start = datetime.now(timezone.utc).astimezone()

    interval = timedelta(minutes=args.interval_minutes)

    for i, ep in enumerate(private):
        ts = (start + i * interval).isoformat()
        log.info(f"[{ep.get('episode_number')}] {ep.get('title')!r} → published_at={ts}")
        if args.dry_run:
            continue
        try:
            publish(ep["id"], published_at=ts)
        except Exception as e:
            log.error(f"  failed: {e}")


if __name__ == "__main__":
    main()
