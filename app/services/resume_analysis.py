from typing import Tuple
from pathlib import Path
import logging

from app.core.config import get_settings
from openai import OpenAI
from pypdf import PdfReader
from docx import Document


logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client() -> OpenAI | None:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("OpenAI API key is not configured; skipping resume analysis.")
        return None
    return OpenAI(api_key=api_key)


def _extract_text(file_path: Path) -> str | None:
    """Extract readable text from a PDF or DOCX resume."""

    try:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                parts.append(text)
            full_text = "\n".join(parts).strip()
            return full_text or None
        elif suffix == ".docx":
            doc = Document(str(file_path))
            parts = [para.text for para in doc.paragraphs]
            full_text = "\n".join(parts).strip()
            return full_text or None
        else:
            logger.warning("Unsupported resume file type for analysis: %s", suffix)
            return None
    except Exception as exc:
        logger.error("Failed to extract text from resume: %s", exc)
        return None


def summarize_resume(file_path: Path) -> Tuple[str | None, str | None]:
    """Use OpenAI to summarize a resume and suggest suitable roles.

    Returns (summary, advice). If OpenAI is not configured or call fails, both values are None.
    """

    client = _get_client()
    if client is None:
        return None, None

    text_content = _extract_text(file_path)
    if not text_content:
        logger.warning("No readable text extracted from resume for OpenAI analysis.")
        return (
            "We could not reliably read the text from this resume file. "
            "Please upload a standard PDF or DOCX resume exported from Word or Google Docs.",
            None,
        )

    base_prompt = (
        "You are CareerLens, an AI career coach. "
        "You will receive the plain text of a resume. "
        "Help the user understand their strengths, best-fit roles, and how to improve the resume."
    )

    try:
        # Summary + roles using chat.completions
        summary_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": base_prompt},
                {
                    "role": "user",
                    "content": (
                        "First, write a 3-5 sentence professional summary of this candidate. "
                        "Then list 3-5 best-fit job titles and industries. "
                        "Use headings: Summary and Best-Fit Roles.\n\n" + text_content
                    ),
                },
            ],
        )

        advice_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": base_prompt},
                {
                    "role": "user",
                    "content": (
                        "Analyze this resume and identify weak points, gaps, or areas that could be improved. "
                        "Provide concrete, actionable suggestions, including example bullet points or phrasing. "
                        "Use headings: Weak Points and How to Improve.\n\n" + text_content
                    ),
                },
            ],
        )

        summary_text = summary_resp.choices[0].message.content if summary_resp.choices else None
        advice_text = advice_resp.choices[0].message.content if advice_resp.choices else None

        if not summary_text:
            logger.warning("OpenAI summary response did not contain text output.")
        if not advice_text:
            logger.warning("OpenAI advice response did not contain text output.")

        return summary_text, advice_text
    except Exception as exc:
        logger.error("OpenAI resume analysis failed: %s", exc)
        return None, None
