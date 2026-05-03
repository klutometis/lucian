"""
Pass 3: Audio stitching.
Reads annotated JSON, calls Cartesia Sonic-3 per line, inserts silence,
concatenates into a final WAV.

Usage:
    uv run tts/stitcher.py --dialogue 4
    uv run tts/stitcher.py --dialogue 4 --dry-run   # print plan, no API calls
"""

import argparse
import json
import logging
import os
import struct
import wave
from io import BytesIO
from pathlib import Path

import cartesia

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def work_paths(work_id: str) -> tuple[Path, Path]:
    work = PROJECT_ROOT / "works" / work_id
    annotations = work / "output" / "annotations"
    audio = work / "output" / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    return annotations, audio

MODEL_ID = "sonic-3"
SAMPLE_RATE = 44100
CHANNELS = 1


def silence_bytes(ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Generate PCM16 silence for the given duration in milliseconds."""
    n_samples = int(sample_rate * ms / 1000)
    return b"\x00\x00" * n_samples


def pcm_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS) -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def generate_line_audio(client: cartesia.Cartesia, line: dict) -> bytes:
    """Call Cartesia for a single annotated line, return raw PCM bytes."""
    voice_id = line.get("voice_id", "")
    if not voice_id:
        log.warning(f"No voice_id for speaker {line.get('speaker')} — skipping")
        return b""

    chunks = client.tts.bytes(
        model_id=MODEL_ID,
        transcript=line["text"],
        voice={"id": voice_id},
        output_format={
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": SAMPLE_RATE,
        },
    )
    # May be a generator or bytes; normalise to bytes
    if isinstance(chunks, (bytes, bytearray)):
        return bytes(chunks)
    return b"".join(chunks)


def stitch_dialogue(work_id: str, dialogue_id: int, dry_run: bool = False):
    annotations_dir, audio_dir = work_paths(work_id)
    annotation_path = annotations_dir / f"dialogue_{dialogue_id:02d}_annotated.json"
    if not annotation_path.exists():
        raise FileNotFoundError(f"No annotation at {annotation_path}")

    data = json.loads(annotation_path.read_text())
    bible = data["bible"]
    lines = data["annotation"]["lines"]

    # Build voice_id lookup from bible
    voice_map = {c["name"]: c["voice_id"] for c in bible["characters"]}

    print(f"\n=== Stitching dialogue {dialogue_id}: {data['title']} ===")
    print(f"  {len(lines)} lines, voice map: {voice_map}\n")

    if dry_run:
        total_ms = 0
        for line in lines:
            vid = voice_map.get(line["speaker"], "")
            total_ms += line["pause_before_ms"] + line["pause_after_ms"]
            est_words = len(line["text"].split())
            est_ms = int(est_words / (line["speed"] * 2.5) * 1000)
            total_ms += est_ms
            print(f"  [{line['line_index']:>2}] {line['speaker']:>12}  "
                  f"voice={vid[:8]}...  "
                  f"↓{line['pause_before_ms']}ms  ~{est_ms}ms  ↑{line['pause_after_ms']}ms")
            print(f"       {line['text'][:80]}")
        print(f"\n  Estimated total: ~{total_ms/1000:.1f}s")
        return

    client = cartesia.Cartesia(api_key=os.environ["CARTESIA_API_KEY"])
    pcm_segments = []

    for i, line in enumerate(lines):
        speaker = line["speaker"]
        voice_id = voice_map.get(speaker, "")
        if not voice_id:
            log.warning(f"No voice for {speaker}, skipping line {i}")
            continue

        log.info(f"  [{i:>2}/{len(lines)}] {speaker}: {line['text'][:60]}...")

        # Silence before
        if line["pause_before_ms"] > 0:
            pcm_segments.append(silence_bytes(line["pause_before_ms"]))

        # Generate speech
        line_with_voice = {**line, "voice_id": voice_id}
        audio = generate_line_audio(client, line_with_voice)
        if audio:
            pcm_segments.append(audio)

        # Silence after
        if line["pause_after_ms"] > 0:
            pcm_segments.append(silence_bytes(line["pause_after_ms"]))

    # Concatenate and write WAV
    all_pcm = b"".join(pcm_segments)
    wav_bytes = pcm_to_wav(all_pcm)

    out_path = audio_dir / f"dialogue_{dialogue_id:02d}.wav"
    out_path.write_bytes(wav_bytes)
    duration_s = len(all_pcm) / (SAMPLE_RATE * 2)
    log.info(f"Saved {duration_s:.1f}s of audio → {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="lucian-dialogues-of-the-dead")
    parser.add_argument("--dialogue", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan without calling Cartesia")
    args = parser.parse_args()
    stitch_dialogue(args.work, args.dialogue, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
