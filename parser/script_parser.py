"""
Script parser for English listening exam scripts.

Supported formats:
─────────────────────────────────────────────────────────────
1. Speaker-labeled dialogue (multi-voice):
   [Man]: Good morning, can I help you?
   [Woman]: Yes, I'd like to book a table.
   Man: Sure, what time?          ← colon format also works
   Woman: Around 7 PM.

2. Chinese labels:
   [男]: 你好！
   [女]: 你好！

3. Plain monologue / narration (no speaker label):
   Welcome to this year's science fair.
   Today we will be exploring three topics...

4. Question number markers:
   (Q1) or [Q1] or Q1. or Number 1.

5. Metadata header (optional):
   @title: Unit 3 Listening Test
   @type: dialogue            ← dialogue / monologue / broadcast
   @voice_A: male_uk          ← override voice for a speaker
   @voice_B: female_us

6. Comments (ignored):
   # This is a comment
─────────────────────────────────────────────────────────────
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScriptSegment:
    """One unit of speech: a speaker's turn or a narrator line."""
    speaker: Optional[str]   # None = narrator / monologue
    text: str
    is_question_marker: bool = False  # e.g. "Number 1"


@dataclass
class ParsedScript:
    title: str = "Listening Audio"
    script_type: str = "auto"          # dialogue / monologue / broadcast
    voice_overrides: dict = field(default_factory=dict)  # speaker -> voice key
    segments: list[ScriptSegment] = field(default_factory=list)

    @property
    def speakers(self) -> list[str]:
        """Return unique speaker names (excluding narrator)."""
        seen = []
        for seg in self.segments:
            if seg.speaker and seg.speaker not in seen:
                seen.append(seg.speaker)
        return seen


# ─────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────
_META_RE    = re.compile(r"^@(\w+)\s*:\s*(.+)$")
_COMMENT_RE = re.compile(r"^\s*#")
_SPEAKER_RE = re.compile(r"^\[([^\]]+)\]\s*:\s*(.+)$|^([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s]*?)\s*:\s+(.+)$")
_QNUM_RE    = re.compile(
    r"^\s*(?:\(Q\d+\)|\[Q\d+\]|Q\d+\.|Number\s+\d+\.?|Question\s+\d+\.?)\s*$",
    re.IGNORECASE,
)
# Inline question number at start of text
_QNUM_INLINE_RE = re.compile(
    r"^\s*(?:Number|Question)\s+(\d+)[.:]\s*(.*)",
    re.IGNORECASE,
)


def _normalize_speaker(name: str) -> str:
    return name.strip()


def _is_question_number(line: str) -> bool:
    return bool(_QNUM_RE.match(line))


def parse_script(text: str) -> ParsedScript:
    """Parse a listening exam script string into structured segments."""
    result = ParsedScript()
    lines = text.splitlines()

    for raw_line in lines:
        line = raw_line.rstrip()

        # Skip blank lines
        if not line.strip():
            continue

        # Skip comments
        if _COMMENT_RE.match(line):
            continue

        # Metadata
        m = _META_RE.match(line.strip())
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "title":
                result.title = val
            elif key == "type":
                result.script_type = val
            elif key.startswith("voice_"):
                speaker_hint = key[6:].lower()  # e.g. "voice_a" -> "a"
                result.voice_overrides[speaker_hint] = val
            continue

        # Question number marker (standalone line)
        if _is_question_number(line.strip()):
            label = line.strip().rstrip(".")
            result.segments.append(ScriptSegment(
                speaker=None,
                text=label,
                is_question_marker=True,
            ))
            continue

        # Speaker-labeled line
        m = _SPEAKER_RE.match(line.strip())
        if m:
            if m.group(1):  # [Speaker]: text
                speaker = _normalize_speaker(m.group(1))
                text = m.group(2).strip()
            else:           # Speaker: text  (only if followed by space)
                speaker = _normalize_speaker(m.group(3))
                text = m.group(4).strip()

            # Ignore metadata-style lines caught by speaker regex
            if not text:
                continue

            # Check for inline question number within the text
            qm = _QNUM_INLINE_RE.match(text)
            if qm:
                num, rest = qm.group(1), qm.group(2).strip()
                result.segments.append(ScriptSegment(
                    speaker=None,
                    text=f"Number {num}",
                    is_question_marker=True,
                ))
                if rest:
                    result.segments.append(ScriptSegment(speaker=speaker, text=rest))
            else:
                result.segments.append(ScriptSegment(speaker=speaker, text=text))
            continue

        # Plain text (monologue / narration)
        text = line.strip()
        # Still check for inline question number
        qm = _QNUM_INLINE_RE.match(text)
        if qm:
            num, rest = qm.group(1), qm.group(2).strip()
            result.segments.append(ScriptSegment(
                speaker=None,
                text=f"Number {num}",
                is_question_marker=True,
            ))
            if rest:
                result.segments.append(ScriptSegment(speaker=None, text=rest))
        else:
            result.segments.append(ScriptSegment(speaker=None, text=text))

    # Auto-detect type if not specified
    if result.script_type == "auto":
        result.script_type = "dialogue" if len(result.speakers) >= 2 else "monologue"

    return result


def parse_file(path: str) -> ParsedScript:
    with open(path, encoding="utf-8") as f:
        return parse_script(f.read())
