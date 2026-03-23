import io
import json
from typing import Any

from docx import Document
from pypdf import PdfReader


def parse_linkedin_json(raw_bytes: bytes) -> dict[str, Any]:
    # LinkedIn exports and manually edited JSON files may include UTF-8 BOM.
    return json.loads(raw_bytes.decode("utf-8-sig"))


def parse_pdf_text(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def parse_docx_text(raw_bytes: bytes) -> str:
    doc = Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def flatten_linkedin_json(data: dict[str, Any]) -> str:
    lines: list[str] = []

    for key in ["headline", "summary", "industry", "location"]:
        value = data.get(key)
        if value:
            lines.append(f"{key.title()}: {value}")

    experiences = data.get("experience", []) or data.get("positions", [])
    if experiences:
        lines.append("Experience:")
        for item in experiences:
            role = item.get("title") or item.get("role") or ""
            company = item.get("company") or item.get("companyName") or ""
            desc = item.get("description") or ""
            lines.append(f"- {role} at {company}. {desc}".strip())

    skills = data.get("skills", [])
    if skills:
        lines.append("Skills: " + ", ".join(str(s) for s in skills))

    return "\n".join(lines).strip()
