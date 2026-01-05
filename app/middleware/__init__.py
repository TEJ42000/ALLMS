"""Middleware package for LLS Study Portal.

Contains authentication and other request processing middleware.
"""

from app.middleware.auth_middleware import AuthMiddleware

__all__ = ["AuthMiddleware"]

