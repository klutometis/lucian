"""
Image generation via Nano Banana (Gemini 3 image models).

Usage:
    uv run pipeline/images/generate.py --prompt "..." --out path.png
    uv run pipeline/images/generate.py --prompt "..." --model gemini-3-pro-image-preview
"""

import argparse
import logging
import os
from pathlib import Path

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def generate(
    prompt: str,
    out: Path,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: str = "1:1",
    image_size: str = "2K",
) -> Path:
    """Aspect ratios: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, etc.
    Image sizes: 1K, 2K, 4K (3.1 Flash adds 512)."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    log.info(f"generating with {model} ({aspect_ratio}, {image_size})...")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        ),
    )
    # Find the image part
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(part.inline_data.data)
            log.info(f"saved → {out} ({out.stat().st_size // 1024} KB)")
            return out
    raise RuntimeError("No image in response")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="gemini-3-pro-image-preview",
                    help="gemini-3-pro-image-preview (Nano Banana Pro, 4K) "
                         "or gemini-3.1-flash-image-preview (Nano Banana 2, faster)")
    ap.add_argument("--aspect", default="1:1",
                    help="1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, ...")
    ap.add_argument("--size", default="2K", help="1K, 2K, or 4K")
    args = ap.parse_args()
    generate(args.prompt, args.out, args.model, args.aspect, args.size)


if __name__ == "__main__":
    main()
