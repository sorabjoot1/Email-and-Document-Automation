from __future__ import annotations

import io
from datetime import datetime

from docx import Document
from pypdf import PdfReader
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def extract_text_from_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    parts = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(parts).strip()


def _safe(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_pdf(title: str, body: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=inch, rightMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Heading1"], spaceAfter=12)
    body_style = ParagraphStyle("BodyCustom", parent=styles["BodyText"], leading=16, spaceAfter=8)
    story = [
        Paragraph(_safe(title or "Document"), title_style),
        Paragraph(_safe(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"), body_style),
        Spacer(1, 10),
        Paragraph(_safe(body), body_style),
    ]
    doc.build(story)
    return buffer.getvalue()


def build_docx(title: str, body: str) -> bytes:
    document = Document()
    document.add_heading(title or "Document", level=1)
    document.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    for block in (body or "").split("\n"):
        document.add_paragraph(block)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
