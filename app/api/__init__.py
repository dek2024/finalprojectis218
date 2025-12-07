# API routes module initialization
from app.api.auth_routes import router as auth_router
from app.api.resume_routes import router as resume_router
from app.api.job_routes import router as job_router
from app.api.interview_routes import router as interview_router
from app.api.chat_routes import router as chat_router

__all__ = ["auth_router", "resume_router", "job_router", "interview_router"]
__all__.append("chat_router")
