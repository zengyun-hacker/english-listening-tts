"""
edge-tts provider — free, uses Microsoft's neural TTS engine.
No API key required.

Install: pip install edge-tts
"""

import asyncio
from pathlib import Path

import edge_tts

from config import EDGE_VOICES, AUDIO_SETTINGS
from tts.base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """Free TTS via Microsoft Edge's neural voices."""

    def __init__(self, rate: str | None = None):
        """
        Args:
            rate: Speech rate adjustment, e.g. "-5%" or "+10%".
                  Defaults to AUDIO_SETTINGS["edge_rate"].
        """
        self.rate = rate or AUDIO_SETTINGS.get("edge_rate", "-5%")

    def resolve_voice(self, speaker: str | None) -> str:
        if not speaker:
            return EDGE_VOICES["default"]
        key = speaker.lower().strip()
        # Direct key lookup
        if key in EDGE_VOICES:
            return EDGE_VOICES[key]
        # Original case lookup (for full voice names passed directly)
        if speaker in EDGE_VOICES:
            return EDGE_VOICES[speaker]
        # If user passed a raw voice name (e.g. "en-GB-SoniaNeural")
        if speaker.startswith("en-"):
            return speaker
        return EDGE_VOICES["default"]

    async def synthesize(self, text: str, voice: str, output_path: Path) -> None:
        communicate = edge_tts.Communicate(text, voice, rate=self.rate)
        await communicate.save(str(output_path))

    async def list_voices(self) -> list[dict]:
        """Return all available English voices."""
        voices = await edge_tts.list_voices()
        return [v for v in voices if v["Locale"].startswith("en-")]


def get_provider(rate: str | None = None) -> EdgeTTSProvider:
    return EdgeTTSProvider(rate=rate)
