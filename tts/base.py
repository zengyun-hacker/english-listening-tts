"""Abstract base class for TTS providers."""

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Base interface for all TTS providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str, output_path: Path) -> None:
        """
        Convert text to speech and save to output_path.

        Args:
            text:        The text to speak.
            voice:       Provider-specific voice identifier.
            output_path: Where to save the audio file.
        """
        ...

    @abstractmethod
    def resolve_voice(self, speaker: str | None) -> str:
        """
        Map a speaker name / role to a provider-specific voice identifier.

        Args:
            speaker: Speaker name from the script (e.g. "Man", "女", None).

        Returns:
            A voice string understood by this provider.
        """
        ...
