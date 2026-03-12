"""
CallCoach CRM - Main Application

AI-powered call tracking CRM for medical and aesthetic clinics.
Full clinic growth operating system with WhatsApp AI Employee,
nurture automation, lead management, and social media tools.
Built with FastAPI + Anthropic Claude.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

from app.config import APP_NAME, APP_VERSION, DATABASE_URL, is_r2_configured
from app.database import init_db
from app.routers import auth_router, calls_router, pipeline_router, coaching_router, live_coaching_router, contacts_router, learning_router, reports_router
from app.routers import admin_router, settings_router
from app.routers import whatsapp_router, leads_router, nurture_router, meta_router, social_router
from app.routers import inbox_router, hiring_router, consultations_router, operations_router, marketing_router, legal_finance_router
from app.routers import feedback_router, distribution_router, notes_router
from app.routers import google_ads_router, seo_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-powered call tracking CRM with real-time sales coaching for clinics"
)

# HTTPS redirect middleware (Nginx sets X-Forwarded-Proto header)
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        forwarded_proto = request.headers.get("x-forwarded-proto", "https")
        if forwarded_proto == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)
        return await call_next(request)

app.add_middleware(HTTPSRedirectMiddleware)

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
app.include_router(learning_router.router)
app.include_router(reports_router.router)
app.include_router(admin_router.router)
app.include_router(settings_router.router)

# v2.0 - Growth Platform routers
app.include_router(whatsapp_router.router)
app.include_router(leads_router.router)
app.include_router(nurture_router.router)
app.include_router(meta_router.router)
app.include_router(social_router.router)
app.include_router(distribution_router.router)

# v2.1 - CRM Expansion routers
app.include_router(inbox_router.router)
app.include_router(hiring_router.router)
app.include_router(consultations_router.router)
app.include_router(operations_router.router)
app.include_router(marketing_router.router)
app.include_router(legal_finance_router.router)
app.include_router(feedback_router.router)
app.include_router(notes_router.router)

# v2.2 - Google Ads, SEO & GMB
app.include_router(google_ads_router.router)
app.include_router(seo_router.router)

# v2.3 - Meta Ads Content, HR & MIS
from app.routers import meta_ads_content_router, hr_mis_router
app.include_router(meta_ads_content_router.router)
app.include_router(hr_mis_router.router)

# v2.4 - Activity Logging
from app.routers import activity_router
app.include_router(activity_router.router)

# v2.5 - SBA AI Business Coach
from app.routers import sba_ai_router
app.include_router(sba_ai_router.router)

# v2.6 - Telephony Integration
from app.routers import telephony_router
app.include_router(telephony_router.router)

# Static files (frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def startup():
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Log infrastructure status
    db_type = "PostgreSQL" if DATABASE_URL.startswith("postgresql") else "SQLite (dev)"
    logger.info(f"Database: {db_type}")
    logger.info(f"File storage: {'Cloudflare R2' if is_r2_configured() else 'Local disk (dev)'}")

    if DATABASE_URL.startswith("sqlite"):
        logger.warning("Using SQLite. Set DATABASE_URL to PostgreSQL for production.")
    if not is_r2_configured():
        logger.warning("R2 not configured. Recordings stored on local disk. Set R2_* env vars for cloud storage.")

    init_db()
    logger.info("Database initialized")

    # Start nurture automation scheduler
    _start_nurture_scheduler()


def _start_nurture_scheduler():
    """Start the background scheduler for nurture sequence automation."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.database import SessionLocal
        from app.services.nurture_service import process_nurture_sends

        def _run_nurture_job():
            """Execute nurture sends in a fresh DB session."""
            db = SessionLocal()
            try:
                sent = process_nurture_sends(db)
                if sent > 0:
                    logger.info(f"Nurture scheduler: sent {sent} messages")
            except Exception as e:
                logger.error(f"Nurture scheduler error: {e}")
            finally:
                db.close()

        scheduler = BackgroundScheduler()
        scheduler.add_job(_run_nurture_job, "interval", minutes=5, id="nurture_sends")
        scheduler.start()
        logger.info("Nurture automation scheduler started (every 5 minutes)")
    except ImportError:
        logger.warning("apscheduler not installed. Nurture automation disabled. Run: pip install apscheduler")
    except Exception as e:
        logger.error(f"Failed to start nurture scheduler: {e}")


@app.get("/")
async def root():
    """Serve the frontend."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"app": APP_NAME, "version": APP_VERSION, "status": "running", "docs": "/docs"}


@app.get("/admin")
async def admin_portal():
    """Serve the admin portal."""
    admin_path = static_dir / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    return {"error": "Admin portal not available", "hint": "admin.html not found in static directory"}


@app.get("/reset-password")
async def reset_password_page():
    """Serve the password reset page."""
    reset_path = static_dir / "reset-password.html"
    if reset_path.exists():
        return FileResponse(str(reset_path))
    return {"error": "Reset password page not available"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
    }
