from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.user import User
from app.models.interview import InterviewPrep
from app.models.resume import Resume
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from openai import OpenAI


router = APIRouter(prefix="/api/interview", tags=["interview"])

settings = get_settings()


def _get_client() -> OpenAI | None:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


@router.post("/generate")
def generate_interview_prep(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate STAR-style behavioral interview questions from the latest resume summary."""

    client = _get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is not configured",
        )

    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )

    summary = (latest_resume.content or "") if latest_resume else ""
    advice = (latest_resume.analysis or "") if latest_resume else ""

    prompt = (
        "You are an interview coach. Generate 5 behavioral interview questions "
        "that encourage STAR (Situation, Task, Action, Result) answers. "
        "Base them on this candidate's resume summary and strengths. "
        "Return a JSON object with a 'questions' array of strings only.\n\n"
        f"RESUME SUMMARY:\n{summary}\n\nADVICE:\n{advice}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content if resp.choices else "{}"
        data = json.loads(content)
        questions_text = data.get("questions", [])

        # Ensure we only keep non-empty, non-bracket artifacts
        cleaned: list[str] = []
        for q in questions_text:
            if not q:
                continue
            q_str = str(q).strip()
            if q_str in {"[", "]", "{", "}", "`", "```", ""}:
                continue
            cleaned.append(q_str)
        questions_text = cleaned

        if not questions_text:
            questions_text = [
                "Tell me about a time you faced a major challenge at work.",
                "Describe a situation where you had to learn something quickly.",
            ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {exc}",
        )

    # Store questions for this user
    preps: list[InterviewPrep] = []
    for question in questions_text:
        if not question:
            continue
        prep = InterviewPrep(
            user_id=current_user.id,
            question=question,
            answer=None,
        )
        db.add(prep)
        preps.append(prep)

    db.commit()

    return {
        "total_questions": len(preps),
        "questions": [{"id": p.id, "question": p.question} for p in preps],
    }


@router.get("/list")
def list_interview_preps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all interview prep questions for current user."""
    preps = db.query(InterviewPrep).filter(
        InterviewPrep.user_id == current_user.id
    ).all()
    
    return [
        {
            "id": p.id,
            "question": p.question,
            "answer": p.answer,
            "created_at": p.created_at
        }
        for p in preps
    ]


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_interview_preps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all interview prep questions for the current user."""

    db.query(InterviewPrep).filter(InterviewPrep.user_id == current_user.id).delete()
    db.commit()

    return None


@router.get("/{prep_id}")
def get_interview_prep(
    prep_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific interview prep question."""
    prep = db.query(InterviewPrep).filter(
        (InterviewPrep.id == prep_id) & (InterviewPrep.user_id == current_user.id)
    ).first()
    
    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found"
        )
    
    return {
        "id": prep.id,
        "question": prep.question,
        "answer": prep.answer,
        "created_at": prep.created_at
    }


@router.post("/{prep_id}/answer")
def save_interview_answer(
    prep_id: int,
    answer: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save an answer to an interview question."""
    prep = db.query(InterviewPrep).filter(
        (InterviewPrep.id == prep_id) & (InterviewPrep.user_id == current_user.id)
    ).first()

    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found",
        )

    prep.answer = answer.get("answer")
    db.commit()

    return {"message": "Answer saved"}


@router.post("/{prep_id}/analyze")
def analyze_interview_answer(
    prep_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze an answer using STAR criteria and filler-word detection."""

    prep = db.query(InterviewPrep).filter(
        (InterviewPrep.id == prep_id) & (InterviewPrep.user_id == current_user.id)
    ).first()

    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found",
        )

    answer_text = (payload.get("answer") or "").strip()
    if not answer_text:
        raise HTTPException(status_code=400, detail="Answer text is required")

    client = _get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is not configured",
        )

    system_prompt = (
        "You are an expert interview coach. Given a behavioral question and a "
        "candidate's spoken answer (transcribed), you will:\n"
        "1) Count obvious filler words (um, uh, like, you know, so, basically, actually).\n"
        "2) Evaluate whether the answer covers STAR: Situation, Task, Action, Result.\n"
        "3) Provide 3-5 bullet points of critique and improvement suggestions.\n"
        "Respond as a JSON object with keys: filler_word_count (number), "
        "filler_examples (array of strings), star_coverage (object with keys "
        "situation/task/action/result and values present|partial|missing), "
        "critique (array of strings)."
    )

    user_prompt = (
        f"QUESTION: {prep.question}\n\n"
        f"ANSWER (transcribed): {answer_text}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content if resp.choices else "{}"
        feedback = json.loads(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze answer: {exc}",
        )

    return feedback


@router.post("/{prep_id}/whisper-transcribe")
async def whisper_transcribe_answer(
    prep_id: int,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transcribe a recorded audio answer using OpenAI Whisper and return the text.

    The frontend uploads an audio file (e.g. webm/ogg/mpeg) from MediaRecorder.
    We transcribe it, optionally save it as the answer, and return the transcript.
    """

    prep = db.query(InterviewPrep).filter(
        (InterviewPrep.id == prep_id) & (InterviewPrep.user_id == current_user.id)
    ).first()

    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found",
        )

    client = _get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is not configured",
        )

    try:
        # Read the uploaded audio into memory
        contents = await audio.read()
        from io import BytesIO

        audio_file = BytesIO(contents)
        audio_file.name = audio.filename or "answer.webm"

        # Use Whisper for transcription
        transcript_resp = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )

        transcript_text = transcript_resp.text.strip() if getattr(transcript_resp, "text", None) else ""
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {exc}",
        )

    if not transcript_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription returned empty text",
        )

    # Save transcript as the answer for this prep
    prep.answer = transcript_text
    db.commit()

    return {"transcript": transcript_text}


@router.delete("/{prep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview_prep(
    prep_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an interview prep question."""
    prep = db.query(InterviewPrep).filter(
        (InterviewPrep.id == prep_id) & (InterviewPrep.user_id == current_user.id)
    ).first()
    
    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found"
        )
    
    db.delete(prep)
    db.commit()
    
    return None
