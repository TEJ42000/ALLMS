"""FastAPI Application Entry Point for LLS Study Portal."""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import routers
from app.routes import ai_tutor, assessment, pages, files_content, admin_courses, admin_pages, admin_users, admin_usage, echr, text_cache, quiz_management, study_guide_routes, gamification, gdpr, upload

# Import authentication middleware
from app.middleware import AuthMiddleware
from app.services.auth_service import get_auth_config

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLS Study Portal",
    description="AI-powered Law & Legal Skills study platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add Authentication middleware (runs first, before CORS)
# This validates IAP headers and attaches user to request.state
app.add_middleware(AuthMiddleware)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers for Auth Errors
# =============================================================================

# Template engine for error pages
error_templates = Jinja2Templates(directory="templates")


@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    """Handle 401 Unauthorized errors with custom HTML page."""
    # Return JSON for API requests, HTML for browser requests
    accept = request.headers.get("accept", "")
    if "application/json" in accept or request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": exc.detail if hasattr(exc, 'detail') else "Not authenticated"}
        )

    return HTMLResponse(
        content=error_templates.get_template("errors/401.html").render({"request": request}),
        status_code=401
    )


@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    """Handle 403 Forbidden errors with custom HTML page."""
    # Return JSON for API requests, HTML for browser requests
    accept = request.headers.get("accept", "")
    if "application/json" in accept or request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail if hasattr(exc, 'detail') else "Forbidden"}
        )

    return HTMLResponse(
        content=error_templates.get_template("errors/403.html").render({"request": request}),
        status_code=403
    )


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(pages.router)
app.include_router(ai_tutor.router)
app.include_router(assessment.router)
app.include_router(files_content.router)
app.include_router(upload.router)  # MVP: Upload and analysis
app.include_router(admin_courses.router)
app.include_router(admin_pages.router)
app.include_router(admin_users.router)
app.include_router(admin_usage.router)
app.include_router(echr.router)
app.include_router(text_cache.router)
app.include_router(quiz_management.router)
app.include_router(study_guide_routes.router)
app.include_router(gamification.router)
app.include_router(gdpr.router)  # GDPR compliance routes


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("🚀 LLS Study Portal starting up...")

    # Log authentication status
    auth_config = get_auth_config()
    env = os.getenv("ENV", "development").lower()

    if auth_config.auth_enabled:
        print(f"🔐 Authentication: ENABLED (domain: @{auth_config.auth_domain})")
        if not auth_config.google_client_id:
            if env == "production":
                print("🚨 CRITICAL: GOOGLE_CLIENT_ID not set in production!")
                print("🚨 Without JWT verification, IAP headers can be spoofed!")
                print("🚨 Set GOOGLE_CLIENT_ID or set AUTH_ENABLED=false for testing only.")
                # Don't fail startup, but log prominently
            else:
                print("⚠️  WARNING: GOOGLE_CLIENT_ID not set - JWT verification unavailable")
    else:
        print("⚠️  Authentication: DISABLED (development mode)")
        if env == "production":
            print("🚨 CRITICAL: AUTH_ENABLED=false in production environment!")
            print("🚨 This is a security risk - all users get mock admin access!")
        else:
            print("⚠️  WARNING: Do NOT use AUTH_ENABLED=false in production!")

    # Verify Anthropic API key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    else:
        print("✅ Anthropic API key loaded")

    print("✅ Application ready!")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("👋 LLS Study Portal shutting down...")


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable (Cloud Run sets PORT)
    port = int(os.getenv("PORT", "8080"))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Set to False in production
        log_level="info"
    )
