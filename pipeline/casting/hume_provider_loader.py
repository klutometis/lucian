"""Tiny shim to load a provider by name without circular imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tts"))


def load_provider(name: str):
    if name == "hume":
        from providers.hume import HumeProvider
        return HumeProvider()
    if name == "elevenlabs":
        from providers.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider()
    raise ValueError(f"Unknown provider: {name}")
