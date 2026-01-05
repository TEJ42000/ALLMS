"""Dependencies package for LLS Study Portal.

Contains FastAPI dependencies for authentication and authorization.
"""

from app.dependencies.auth import (
    get_current_user,
    require_authenticated,
    require_mgms_domain,
    require_allowed_user,
)

__all__ = [
    "get_current_user",
    "require_authenticated",
    "require_mgms_domain",
    "require_allowed_user",
]

