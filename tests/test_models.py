"""Unit-style tests for SQLAlchemy models (basic CRUD)."""

from app.models import User, Resume, JobMatch, InterviewPrep


def test_user_crud(db_session):
    """Create, read, update, and delete a User using the ORM only."""

    user = User(
        email="crud@example.com",
        username="cruduser",
        full_name="CRUD User",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    fetched = db_session.query(User).filter_by(email="crud@example.com").first()
    assert fetched is not None
    assert fetched.username == "cruduser"

    fetched.full_name = "Updated Name"
    db_session.commit()

    updated = db_session.query(User).get(fetched.id)
    assert updated.full_name == "Updated Name"

    db_session.delete(updated)
    db_session.commit()
    assert db_session.query(User).get(fetched.id) is None


def test_resume_crud(db_session, test_user):
    """Basic CRUD operations for the Resume model."""

    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        content="Sample content",
        analysis="Analysis",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    fetched = db_session.query(Resume).filter_by(user_id=test_user.id).first()
    assert fetched is not None
    assert fetched.filename == "resume.pdf"


def test_job_match_crud(db_session, test_user):
    """Basic CRUD for JobMatch model to ensure mappings are valid."""

    match = JobMatch(
        user_id=test_user.id,
        title="Engineer",
        company="Acme",
        location="Remote",
        url="http://example.com/job",
        score=0.9,
    )
    db_session.add(match)
    db_session.commit()

    fetched = db_session.query(JobMatch).filter_by(user_id=test_user.id).first()
    assert fetched is not None
    assert fetched.company == "Acme"


def test_interview_prep_crud(db_session, test_user):
    """Create and query InterviewPrep records to validate relationships."""

    prep = InterviewPrep(
        user_id=test_user.id,
        question="Tell me about a challenge you faced.",
        answer=None,
    )
    db_session.add(prep)
    db_session.commit()

    fetched = db_session.query(InterviewPrep).filter_by(user_id=test_user.id).first()
    assert fetched is not None
    assert "challenge" in fetched.question.lower()
