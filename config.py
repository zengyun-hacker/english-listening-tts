"""
Voice configuration for English listening exam TTS.
Supports edge-tts (free) and OpenAI TTS providers.
"""

# ─────────────────────────────────────────────
# edge-tts voices (Microsoft Neural)
# Full list: run `edge-tts --list-voices`
# ─────────────────────────────────────────────
EDGE_VOICES = {
    # Male voices
    "male":     "en-US-GuyNeural",          # American male, standard
    "male_us":  "en-US-GuyNeural",          # American male
    "male_uk":  "en-GB-RyanNeural",         # British male
    "male_au":  "en-AU-WilliamNeural",      # Australian male

    # Female voices
    "female":   "en-US-JennyNeural",        # American female, standard
    "female_us":"en-US-JennyNeural",        # American female
    "female_uk":"en-GB-SoniaNeural",        # British female
    "female_au":"en-AU-NatashaNeural",      # Australian female

    # Aliases: Chinese labels
    "男":       "en-US-GuyNeural",
    "女":       "en-US-JennyNeural",
    "男生":     "en-US-GuyNeural",
    "女生":     "en-US-JennyNeural",
    "男士":     "en-US-GuyNeural",
    "女士":     "en-US-JennyNeural",

    # Common exam character names (map to voice types)
    "man":      "en-US-GuyNeural",
    "woman":    "en-US-JennyNeural",
    "boy":      "en-US-GuyNeural",
    "girl":     "en-US-JennyNeural",

    # Narrator / announcer
    "narrator": "en-US-AndrewNeural",
    "announcer":"en-US-AndrewNeural",
    "旁白":     "en-US-AndrewNeural",
    "播音员":   "en-US-AndrewNeural",

    # Default fallback
    "default":  "en-US-JennyNeural",
}

# ─────────────────────────────────────────────
# OpenAI TTS voices
# Options: alloy, echo, fable, onyx, nova, shimmer
# ─────────────────────────────────────────────
OPENAI_VOICES = {
    "male":     "onyx",     # Deep male voice
    "male_us":  "echo",     # American male
    "female":   "nova",     # American female, clear
    "female_us":"nova",
    "female_uk":"shimmer",  # Softer female

    # Chinese labels
    "男":       "onyx",
    "女":       "nova",
    "男生":     "onyx",
    "女生":     "nova",
    "男士":     "onyx",
    "女士":     "nova",

    # Common names
    "man":      "onyx",
    "woman":    "nova",
    "boy":      "echo",
    "girl":     "shimmer",

    # Narrator
    "narrator": "alloy",
    "announcer":"alloy",
    "旁白":     "alloy",
    "播音员":   "alloy",

    "default":  "nova",
}

# ─────────────────────────────────────────────
# Audio settings
# ─────────────────────────────────────────────
AUDIO_SETTINGS = {
    # Silence between speaker turns (milliseconds)
    "pause_between_speakers": 600,

    # Silence after question number announcement
    "pause_after_question_number": 800,

    # Silence at beginning and end of audio
    "leading_silence": 1000,
    "trailing_silence": 2000,

    # edge-tts speech rate adjustment
    # Format: "+10%" speeds up, "-10%" slows down
    # Exam standard is slightly slower than normal speech
    "edge_rate": "-5%",

    # OpenAI TTS speech speed (0.25 to 4.0, 1.0 = normal)
    "openai_speed": 0.95,

    # Output format
    "output_format": "mp3",  # mp3 or wav
}
