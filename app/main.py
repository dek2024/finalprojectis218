from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import logging
from pathlib import Path

from app.core.config import get_settings
from app.database import engine, Base
from app.models.user import User
from app.models.resume import Resume
from app.models.job_match import JobMatch
from app.models.interview import InterviewPrep
from app.api import auth_router, resume_router, job_router, interview_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get absolute path to app directory
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
if not STATIC_DIR.exists():
    logger.error(f"Static directory not found: {STATIC_DIR}")
if not TEMPLATES_DIR.exists():
    logger.error(f"Templates directory not found: {TEMPLATES_DIR}")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(job_router)
app.include_router(interview_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve homepage."""
    return templates.TemplateResponse("index.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/upload-resume", response_class=HTMLResponse)
async def upload_resume_page(request: Request):
    """Serve resume upload page."""
    return templates.TemplateResponse("upload_resume.html", {"request": request})


@app.get("/job-matches", response_class=HTMLResponse)
async def job_matches_page(request: Request):
    """Serve job matches page."""
    return templates.TemplateResponse("job_matches.html", {"request": request})


@app.get("/interview-prep", response_class=HTMLResponse)
async def interview_prep_page(request: Request):
    """Serve interview preparation page."""
    return templates.TemplateResponse("interview_prep.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info(f"{settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
