"""
CallCoach CRM - Main Application

AI-powered call tracking CRM for medical and aesthetic clinics.
Built with FastAPI + Anthropic Claude.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import APP_NAME, APP_VERSION
from app.database import init_db
from app.routers import auth_router, calls_router, pipeline_router, coaching_router, live_coaching_router, contacts_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-powered call tracking CRM with real-time sales coaching for clinics"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(calls_router.router)
app.include_router(pipeline_router.router)
app.include_router(coaching_router.router)
app.include_router(live_coaching_router.router)
app.include_router(contacts_router.router)

# Static files (frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def startup():
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """Serve the frontend."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"app": APP_NAME, "version": APP_VERSION, "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    from app.config import ANTHROPIC_API_KEY, GROQ_API_KEY
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "anthropic_key_set": bool(ANTHROPIC_API_KEY),
        "anthropic_key_prefix": ANTHROPIC_API_KEY[:12] + "..." if ANTHROPIC_API_KEY else "NOT SET",
        "groq_key_set": bool(GROQ_API_KEY),
    }
