"""
OpenAI TTS provider — high quality, requires OpenAI API key.

Install: pip install openai
Voices: alloy, echo, fable, onyx, nova, shimmer
Models: tts-1 (fast), tts-1-hd (high quality)
"""

import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from config import OPENAI_VOICES, AUDIO_SETTINGS
from tts.base import TTSProvider


class OpenAITTSProvider(TTSProvider):
    """Premium TTS via OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "tts-1-hd",
        speed: float | None = None,
    ):
        """
        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var).
            model:   "tts-1" (fast/cheaper) or "tts-1-hd" (higher quality).
            speed:   Speech speed 0.25–4.0; 1.0 is normal.
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.speed = speed or AUDIO_SETTINGS.get("openai_speed", 0.95)

    def resolve_voice(self, speaker: str | None) -> str:
        if not speaker:
            return OPENAI_VOICES["default"]
        key = speaker.lower().strip()
        if key in OPENAI_VOICES:
            return OPENAI_VOICES[key]
        if speaker in OPENAI_VOICES:
            return OPENAI_VOICES[speaker]
        # If user passed a raw OpenAI voice name
        valid = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        if speaker.lower() in valid:
            return speaker.lower()
        return OPENAI_VOICES["default"]

    async def synthesize(self, text: str, voice: str, output_path: Path) -> None:
        response = await self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            speed=self.speed,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(output_path))


def get_provider(
    api_key: str | None = None,
    model: str = "tts-1-hd",
    speed: float | None = None,
) -> OpenAITTSProvider:
    return OpenAITTSProvider(api_key=api_key, model=model, speed=speed)
