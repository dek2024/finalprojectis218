from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.auth.dependencies import get_current_user
from app.services.resume_analysis import summarize_resume

router = APIRouter(prefix="/api/resume", tags=["resume"])

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "resumes"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a resume file."""
    # Validate file type
    allowed_types = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be PDF or DOCX"
        )
    
    # If the user already has a resume, remove it so there is only
    # ever one active resume driving analysis and job matches.
    existing_resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    for existing in existing_resumes:
        old_path = UPLOADS_DIR / f"{current_user.id}_{existing.filename}"
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                # If we can't delete the old file, continue but still
                # replace the DB row so the app stays consistent.
                pass
        db.delete(existing)
    db.commit()

    # Save new file on disk, namespaced by user
    file_location = UPLOADS_DIR / f"{current_user.id}_{file.filename}"
    with open(file_location, "wb") as f:
        contents = await file.read()
        f.write(contents)
    
    # Call OpenAI to generate a summary and job-fit advice (best effort)
    summary_text, advice_text = summarize_resume(file_location)

    # Create resume record
    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        content=summary_text,
        analysis=advice_text,
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return {
        "id": resume.id,
        "filename": resume.filename,
        "created_at": resume.created_at,
        "summary": resume.content,
        "analysis": resume.analysis,
    }


@router.get("/list")
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all resumes for the current user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "created_at": r.created_at
        }
        for r in resumes
    ]


@router.get("/{resume_id}")
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details and download URL for a specific resume."""
    resume = db.query(Resume).filter(
        (Resume.id == resume_id) & (Resume.user_id == current_user.id)
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    file_location = UPLOADS_DIR / f"{current_user.id}_{resume.filename}"
    file_exists = file_location.exists()

    return {
        "id": resume.id,
        "filename": resume.filename,
        "content": resume.content,
        "analysis": resume.analysis,
        "created_at": resume.created_at,
        "file_exists": file_exists,
    }


@router.get("/download/{resume_id}")
def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the resume file for the given ID."""
    resume = db.query(Resume).filter(
        (Resume.id == resume_id) & (Resume.user_id == current_user.id)
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    file_location = UPLOADS_DIR / f"{current_user.id}_{resume.filename}"
    if not file_location.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found on disk",
        )

    # Try to infer correct media type for embedding
    media_type = "application/pdf" if resume.filename.lower().endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=file_location,
        filename=resume.filename,
        media_type=media_type,
    )


@router.delete("/delete/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a resume record and its file."""
    resume = db.query(Resume).filter(
        (Resume.id == resume_id) & (Resume.user_id == current_user.id)
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Remove file from disk if present
    file_location = UPLOADS_DIR / f"{current_user.id}_{resume.filename}"
    if file_location.exists():
        try:
            file_location.unlink()
        except Exception:
            # If file delete fails, still remove DB row but return warning
            db.delete(resume)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Resume record deleted but file could not be removed",
            )

    db.delete(resume)
    db.commit()

    return {"message": "Resume deleted"}
