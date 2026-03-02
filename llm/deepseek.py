"""
DeepSeek API client for generating English listening exam content.

DeepSeek is compatible with the OpenAI API — only the base_url differs.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────

@dataclass
class ListeningItem:
    """One question item within a listening section."""
    number: int
    script: str          # Raw dialogue/monologue text, e.g. "[Man]: ...\n[Woman]: ..."
    question: str
    options: dict        # {"A": "...", "B": "...", "C": "...", "D": "..."}
    answer: str          # "A" / "B" / "C" / "D"
    explanation: str = ""


@dataclass
class ListeningSection:
    """One section (e.g. Part I Short Conversations, Part II Long Conversations)."""
    name: str
    instructions: str
    section_type: str    # "dialogue" | "monologue"
    items: list[ListeningItem] = field(default_factory=list)


@dataclass
class ListeningTest:
    """A complete listening exam with multiple sections."""
    title: str
    sections: list[ListeningSection] = field(default_factory=list)

    def to_tts_script(self) -> str:
        """
        Produce a flat TTS script string compatible with parse_script().

        Format:
            Number 1.
            [Man]: ...
            [Woman]: ...

            Number 2.
            ...
        """
        lines = []
        for section in self.sections:
            for item in section.items:
                lines.append(f"Number {item.number}.")
                lines.append(item.script.strip())
                lines.append("")   # blank line separator
        return "\n".join(lines).strip()

    def to_answer_key(self) -> str:
        """Return a human-readable answer key string."""
        parts = []
        for section in self.sections:
            parts.append(f"【{section.name}】")
            for item in section.items:
                exp = f"  {item.explanation}" if item.explanation else ""
                parts.append(f"  {item.number}. {item.answer}{exp}")
        return "\n".join(parts)


# ─────────────────────────────────────────────
# JSON parsing helpers
# ─────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """
    Try to find a JSON object in the response text.
    Handles both raw JSON and ```json ... ``` code blocks.
    """
    # Try to extract from markdown code block first
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        return code_block.group(1)

    # Find first { ... } spanning the whole content
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text


def _parse_response(raw: str) -> ListeningTest:
    """Parse the raw LLM response into a ListeningTest object."""
    json_str = _extract_json(raw)
    data = json.loads(json_str)

    sections = []
    for sec in data.get("sections", []):
        items = []
        for it in sec.get("items", []):
            items.append(ListeningItem(
                number=int(it["number"]),
                script=it["script"],
                question=it["question"],
                options=it["options"],
                answer=it["answer"].strip().upper(),
                explanation=it.get("explanation", ""),
            ))
        sections.append(ListeningSection(
            name=sec["name"],
            instructions=sec.get("instructions", ""),
            section_type=sec.get("section_type", "dialogue"),
            items=items,
        ))

    return ListeningTest(
        title=data.get("title", "Listening Test"),
        sections=sections,
    )


# ─────────────────────────────────────────────
# Main generation function
# ─────────────────────────────────────────────

def generate_listening_test(
    prompt: str,
    api_key: str,
    model: str = "deepseek-chat",
) -> ListeningTest:
    """
    Call DeepSeek to generate a structured listening test.

    Args:
        prompt:  User's description of what to generate (e.g. "大学英语四级听力，15题").
        api_key: DeepSeek API key.
        model:   DeepSeek model name (default: "deepseek-chat").

    Returns:
        A ListeningTest dataclass with all sections and items populated.

    Raises:
        json.JSONDecodeError: If the model returned malformed JSON.
        Exception:            Any network or API error.
    """
    from openai import OpenAI
    from llm.prompts import SYSTEM_PROMPT

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.8,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content
    return _parse_response(raw)
