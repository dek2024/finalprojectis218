from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.job_match import JobMatch
from app.models.resume import Resume
from app.auth.dependencies import get_current_user
from app.services.job_search import search_jobs_with_jsearch

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/search")
async def search_jobs(
    num_pages: int = Query(10, ge=1, le=20, description="How many JSearch pages to fetch"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search for jobs using RapidAPI JSearch and store matches.

    This version automatically builds the query from the user's latest
    resume summary/advice instead of manual filters, and prefers the
    explicit "Best-Fit Roles" section when available.
    """

    # Look at latest resume to infer a suitable title/keywords
    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )

    best_fit_titles: list[str] = []
    inferred_industry = None

    # Prefer using the AI-generated "Best-Fit Roles" section when present.
    if latest_resume and latest_resume.content:
        text = latest_resume.content
        lower = text.lower()

        marker = "### Best-Fit Roles"
        idx = text.find(marker)
        if idx != -1:
            roles_block = text[idx + len(marker) :]
            # Stop at the next markdown heading if present
            for stop in ["### ", "\n## "]:
                stop_idx = roles_block.find(stop)
                if stop_idx != -1:
                    roles_block = roles_block[:stop_idx]
                    break

            lines = roles_block.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Strip leading list markers like "1.", "-", "*"
                if line[0].isdigit():
                    dot_idx = line.find(".")
                    if dot_idx != -1 and dot_idx + 1 < len(line):
                        line = line[dot_idx + 1 :].strip()
                elif line[0] in {"-", "*"}:
                    line = line[1:].strip()

                # Keep only the role title before any dash/description
                dash_idx = line.find(" - ")
                if dash_idx != -1:
                    line = line[:dash_idx].strip()

                if line and line not in best_fit_titles:
                    best_fit_titles.append(line)

        # Fallback heuristic if we couldn't parse any explicit roles
        if not best_fit_titles:
            if "data scientist" in lower:
                best_fit_titles.append("Data Scientist")
            elif "machine learning" in lower or "ml engineer" in lower:
                best_fit_titles.append("Machine Learning Engineer")
            elif "backend" in lower or "back-end" in lower:
                best_fit_titles.append("Backend Engineer")
            elif "frontend" in lower or "front-end" in lower or "ui engineer" in lower:
                best_fit_titles.append("Frontend Engineer")
            elif "full stack" in lower:
                best_fit_titles.append("Full Stack Engineer")
            elif "product manager" in lower or "product management" in lower:
                best_fit_titles.append("Product Manager")

    # Always have at least one generic title so the search still works
    if not best_fit_titles:
        best_fit_titles.append("Software Engineer")

    all_jobs: list[dict] = []
    seen_ids: set[str] = set()

    for title in best_fit_titles:
        jobs = await search_jobs_with_jsearch(
            title=title,
            company=None,
            industry=inferred_industry,
            location=None,
            num_pages=max(1, num_pages // len(best_fit_titles)) if num_pages > 1 else 1,
        )
        for job in jobs or []:
            job_id = str(job.get("id") or "")
            if job_id and job_id in seen_ids:
                continue
            if job_id:
                seen_ids.add(job_id)
            all_jobs.append(job)

    if not all_jobs:
        return {"total_matches": 0, "matches": []}

    created_matches: list[dict] = []
    for job in all_jobs:
        match = JobMatch(
            user_id=current_user.id,
            title=job.get("title") or "Untitled role",
            company=job.get("company") or "Unknown company",
            location=job.get("location") or "",
            url=job.get("url"),
            score=None,
        )
        db.add(match)
        db.flush()
        created_matches.append(
            {
                "id": match.id,
                "title": match.title,
                "company": match.company,
                "location": match.location,
                "url": match.url,
            }
        )

    db.commit()

    return {"total_matches": len(created_matches), "matches": created_matches}


@router.get("/matches")
def get_job_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all job matches for current user."""
    matches = db.query(JobMatch).filter(
        JobMatch.user_id == current_user.id
    ).order_by(JobMatch.score.desc()).all()
    
    return [
        {
            "id": m.id,
            "title": m.title,
            "company": m.company,
            "location": m.location,
            "url": m.url,
            "score": m.score,
            "created_at": m.created_at,
        }
        for m in matches
    ]


@router.get("/match/{match_id}")
def get_job_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific job match details."""
    match = db.query(JobMatch).filter(
        (JobMatch.id == match_id) & (JobMatch.user_id == current_user.id)
    ).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found"
        )
    
    return {
        "id": match.id,
        "title": match.title,
        "company": match.company,
        "location": match.location,
        "url": match.url,
        "score": match.score,
        "created_at": match.created_at,
    }


@router.delete("/match/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job match."""
    match = db.query(JobMatch).filter(
        (JobMatch.id == match_id) & (JobMatch.user_id == current_user.id)
    ).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found"
        )
    
    db.delete(match)
    db.commit()

    return None
