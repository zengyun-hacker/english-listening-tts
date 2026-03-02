"""
Audio processor: merges TTS segments into a single listening exam audio file.

Uses pydub for audio manipulation.
Requires ffmpeg installed on the system.
  macOS:  brew install ffmpeg
  Ubuntu: apt install ffmpeg
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Callable

from pydub import AudioSegment

from config import AUDIO_SETTINGS
from parser.script_parser import ParsedScript, ScriptSegment
from tts.base import TTSProvider


# ─────────────────────────────────────────────
# Silence helpers
# ─────────────────────────────────────────────

def _silence(ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=ms)


# ─────────────────────────────────────────────
# Voice assignment
# ─────────────────────────────────────────────

def _assign_voices(
    script: ParsedScript,
    provider: TTSProvider,
    voice_overrides: dict[str, str] | None = None,
) -> dict[str | None, str]:
    """
    Build a mapping: speaker_name -> resolved_voice.

    Priority:
      1. voice_overrides passed at call time
      2. @voice_X metadata in the script
      3. Provider default for the speaker name
    """
    overrides = dict(voice_overrides or {})
    # Merge script-level overrides (keyed by lowercase index: "a", "b", ...)
    overrides.update({k.lower(): v for k, v in script.voice_overrides.items()})

    mapping: dict[str | None, str] = {}
    speakers = [None] + script.speakers  # None = narrator

    for idx, speaker in enumerate(speakers):
        # Check explicit override by speaker name
        key = (speaker or "narrator").lower()
        if key in overrides:
            override_val = overrides[key]
            mapping[speaker] = provider.resolve_voice(override_val)
            continue

        # Check override by index letter (a, b, c, ...)
        idx_letter = chr(ord("a") + idx - 1) if speaker else "narrator"
        if idx_letter in overrides:
            mapping[speaker] = provider.resolve_voice(overrides[idx_letter])
            continue

        # Default: let the provider resolve from the speaker name
        mapping[speaker] = provider.resolve_voice(speaker)

    return mapping


# ─────────────────────────────────────────────
# Core rendering
# ─────────────────────────────────────────────

async def render_audio(
    script: ParsedScript,
    provider: TTSProvider,
    output_path: str | Path,
    voice_overrides: dict[str, str] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> Path:
    """
    Synthesize all segments and merge them into a single audio file.

    Args:
        script:           Parsed exam script.
        provider:         TTS provider instance (EdgeTTS or OpenAI).
        output_path:      Where to save the final merged audio.
        voice_overrides:  Extra speaker->voice mappings.
        progress_callback: Called with (current, total, speaker) for progress.

    Returns:
        Path to the output audio file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = AUDIO_SETTINGS
    pause_ms       = cfg["pause_between_speakers"]
    q_pause_ms     = cfg["pause_after_question_number"]
    lead_silence   = cfg["leading_silence"]
    trail_silence  = cfg["trailing_silence"]

    voice_map = _assign_voices(script, provider, voice_overrides)

    segments = script.segments
    total = len(segments)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        parts: list[AudioSegment] = [_silence(lead_silence)]

        for i, seg in enumerate(segments):
            if progress_callback:
                label = seg.speaker or ("Q-marker" if seg.is_question_marker else "narrator")
                progress_callback(i + 1, total, label)

            voice = voice_map.get(seg.speaker, voice_map.get(None, ""))
            seg_path = tmp / f"seg_{i:04d}.mp3"

            await provider.synthesize(seg.text, voice, seg_path)
            audio = AudioSegment.from_file(seg_path)
            parts.append(audio)

            # Pause after this segment
            if seg.is_question_marker:
                parts.append(_silence(q_pause_ms))
            else:
                parts.append(_silence(pause_ms))

        parts.append(_silence(trail_silence))

        merged = sum(parts[1:], parts[0])
        fmt = cfg.get("output_format", "mp3")
        merged.export(str(output_path), format=fmt)

    return output_path


# ─────────────────────────────────────────────
# Convenience: render multiple scripts (one file each)
# ─────────────────────────────────────────────

async def render_batch(
    scripts: list[tuple[ParsedScript, Path]],
    provider: TTSProvider,
    voice_overrides: dict[str, str] | None = None,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
) -> list[Path]:
    """
    Render multiple scripts sequentially and return their output paths.

    progress_callback(title, current_seg, total_segs, speaker)
    """
    results = []
    for script, out_path in scripts:
        def cb(cur, tot, spk, title=script.title):
            if progress_callback:
                progress_callback(title, cur, tot, spk)

        path = await render_audio(script, provider, out_path, voice_overrides, cb)
        results.append(path)
    return results
