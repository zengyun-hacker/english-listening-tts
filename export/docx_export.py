"""
Export a ListeningTest to a Word (.docx) document.

Structure:
  - Title (Heading 1)
  - For each section:
      - Section name (Heading 2)
      - Instructions (italic paragraph)
      - For each item:
          - Question number + question text (Bold)
          - Options A / B / C / D
  - Answer Key page (Heading 2)
      - Answers with explanations grouped by section
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm.deepseek import ListeningTest


def export_to_docx(test: "ListeningTest") -> bytes:
    """
    Generate a Word document from a ListeningTest and return it as bytes.

    Args:
        test: A populated ListeningTest dataclass.

    Returns:
        Raw bytes of the .docx file, ready for st.download_button().
    """
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # ── Page margins (narrower for more content) ──────────────────────────
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.2)
        section.right_margin  = Inches(1.2)

    # ── Title ─────────────────────────────────────────────────────────────
    title_para = doc.add_heading(test.title, level=1)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()   # spacer

    # ── Sections ──────────────────────────────────────────────────────────
    for sec in test.sections:
        doc.add_heading(sec.name, level=2)

        if sec.instructions:
            instr = doc.add_paragraph(sec.instructions)
            instr.runs[0].italic = True
            instr.paragraph_format.space_after = Pt(6)

        for item in sec.items:
            # Question header: "1. What does the woman imply?"
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(f"{item.number}. {item.question}")
            q_run.bold = True
            q_para.paragraph_format.space_before = Pt(8)
            q_para.paragraph_format.space_after  = Pt(2)

            # Options
            for letter in ("A", "B", "C", "D"):
                opt_text = item.options.get(letter, "")
                if opt_text:
                    opt_para = doc.add_paragraph(style="List Bullet")
                    opt_para.clear()   # remove auto bullet
                    opt_run = opt_para.add_run(f"  {letter}. {opt_text}")
                    opt_para.paragraph_format.space_after = Pt(1)

        doc.add_paragraph()   # spacer between sections

    # ── Answer Key ────────────────────────────────────────────────────────
    doc.add_page_break()
    doc.add_heading("Answer Key  参考答案", level=2)

    for sec in test.sections:
        sec_heading = doc.add_paragraph()
        sec_run = sec_heading.add_run(f"【{sec.name}】")
        sec_run.bold = True
        sec_run.font.color.rgb = RGBColor(0x1A, 0x73, 0xE8)

        for item in sec.items:
            ans_para = doc.add_paragraph()
            ans_para.paragraph_format.left_indent = Inches(0.3)
            ans_run = ans_para.add_run(f"{item.number}. {item.answer}")
            ans_run.bold = True
            if item.explanation:
                ans_para.add_run(f"   {item.explanation}")

        doc.add_paragraph()   # spacer

    # ── Serialize to bytes ────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
