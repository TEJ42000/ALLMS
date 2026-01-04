"""FastAPI Application Entry Point for LLS Study Portal."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import routers
from app.routes import ai_tutor, assessment, pages, files_content, admin_courses, admin_pages, text_cache

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="LLS Study Portal",
    description="AI-powered Law & Legal Skills study platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(admin_courses.router)
app.include_router(admin_pages.router)
app.include_router(text_cache.router)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("🚀 LLS Study Portal starting up...")

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
