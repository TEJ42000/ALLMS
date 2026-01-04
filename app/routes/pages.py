# app/routes/pages.py - Page Rendering Routes

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pages"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Serve the main study portal page.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "LLS Study Portal",
            "version": "2.0.0"
        }
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Cloud Run.
    """
    return {
        "status": "healthy",
        "service": "lls-study-portal",
        "version": "2.0.0"
    }

