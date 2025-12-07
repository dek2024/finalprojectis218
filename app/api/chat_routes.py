from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from app.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from openai import OpenAI


logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_client() -> OpenAI | None:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("OpenAI API key is not configured; chat disabled.")
        return None
    return OpenAI(api_key=api_key)


@router.post("/resume")
async def chat_about_resume(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Simple chat endpoint that lets the user ask questions about their latest resume and job matches."""

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is required",
        )

    client = _get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI chat is not configured",
        )

    # Get latest resume summary/analysis for context
    from app.models.resume import Resume

    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )

    resume_context = ""
    if latest_resume:
        resume_context = f"SUMMARY: {latest_resume.content or ''}\nADVICE: {latest_resume.analysis or ''}"

    system_prompt = (
        "You are CareerLens, a friendly career coach. "
        "Use the resume context if available, and answer the user's question "
        "with concise, practical advice about careers, job matches, and resume improvements."
    )

    try:
        logger.info("CareerLens chat request from user %s: %s", current_user.id, message)

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"RESUME CONTEXT (may be empty):\n{resume_context}\n\n"
                        f"USER QUESTION: {message}"
                    ),
                },
            ],
        )

        if not resp.choices:
            logger.warning("OpenAI chat returned no choices")
            reply_text = "I can help you think about your resume and job search."
        else:
            message_obj = resp.choices[0].message
            content = getattr(message_obj, "content", None) if message_obj else None
            if not content:
                logger.warning("OpenAI chat choice had empty content: %s", resp)
                reply_text = "I can help you think about your resume and job search."
            else:
                reply_text = content.strip()

        return {"reply": reply_text}
    except Exception as exc:
        logger.error("OpenAI resume chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        )
