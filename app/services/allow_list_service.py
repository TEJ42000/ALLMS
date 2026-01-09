"""Allow List Service for User Access Management.

Provides CRUD operations for the allow list stored in Firestore.
External users on the allow list can access the application.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote, unquote

from app.models.allow_list_models import (
    AllowListEntry,
    AllowListCreateRequest,
    AllowListUpdateRequest,
)
from app.services.gcp_service import get_firestore_client, is_firestore_available

logger = logging.getLogger(__name__)

# Firestore collection name
ALLOW_LIST_COLLECTION = "allowed_users"


def _email_to_doc_id(email: str) -> str:
    """Convert email to URL-safe Firestore document ID."""
    return quote(email.lower().strip(), safe='')


def _doc_id_to_email(doc_id: str) -> str:
    """Convert Firestore document ID back to email."""
    return unquote(doc_id)


class AllowListService:
    """Service for managing the user allow list in Firestore."""

    def __init__(self):
        """Initialize the allow list service."""
        self.db = get_firestore_client()
        self._collection = None
        if self.db is not None:
            self._collection = self.db.collection(ALLOW_LIST_COLLECTION)
        else:
            logger.warning("Firestore not available - allow list will be disabled")

    @property
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self.db is not None

    def is_user_allowed(self, email: str) -> bool:
        """Check if a user is on the active, non-expired allow list.

        Args:
            email: Email address to check

        Returns:
            True if user has effective access, False otherwise
        """
        if not self.is_available:
            return False

        entry = self.get_user(email)
        if entry is None:
            return False

        return entry.is_effective

    def get_user(self, email: str) -> Optional[AllowListEntry]:
        """Get an allow list entry by email.

        Args:
            email: Email address to look up

        Returns:
            AllowListEntry if found, None otherwise
        """
        if not self.is_available:
            return None

        doc_id = _email_to_doc_id(email)

        try:
            doc = self._collection.document(doc_id).get()
            if not doc.exists:
                return None

            data = doc.to_dict()
            return AllowListEntry(**data)
        except Exception as e:
            logger.error("Error getting allow list entry for %s: %s", email, e)
            return None

    def get_all_users(
        self,
        include_expired: bool = False,
        include_inactive: bool = False
    ) -> List[AllowListEntry]:
        """Get all allow list entries.

        Args:
            include_expired: Include expired entries
            include_inactive: Include inactive entries

        Returns:
            List of AllowListEntry objects
        """
        if not self.is_available:
            return []

        try:
            docs = self._collection.stream()
            entries = []

            for doc in docs:
                try:
                    data = doc.to_dict()
                    entry = AllowListEntry(**data)

                    # Filter based on parameters
                    if not include_inactive and not entry.active:
                        continue
                    if not include_expired and entry.is_expired:
                        continue

                    entries.append(entry)
                except Exception as e:
                    logger.warning("Error parsing allow list entry %s: %s", doc.id, e)
                    continue

            # Sort by added_at descending (newest first)
            entries.sort(key=lambda x: x.added_at, reverse=True)
            return entries
        except Exception as e:
            logger.error("Error getting all allow list entries: %s", e)
            return []

    def add_user(
        self,
        request: AllowListCreateRequest,
        added_by: str
    ) -> AllowListEntry:
        """Add a user to the allow list.

        If the user already exists:
        - If active and effective: raises ValueError
        - If inactive (soft-deleted): reactivates the user with new details
        - If expired: updates with new expiration and reactivates

        Args:
            request: Create request with email, reason, etc.
            added_by: Email of admin adding the user

        Returns:
            Created or reactivated AllowListEntry

        Raises:
            ValueError: If user is already active or service unavailable
        """
        if not self.is_available:
            raise ValueError("Allow list service is not available")

        email = request.email.lower().strip()
        doc_id = _email_to_doc_id(email)

        # Check if already exists
        existing = self.get_user(email)
        if existing is not None:
            # If user is already active and effective, don't allow duplicate
            if existing.is_effective:
                raise ValueError(
                    f"User {email} is already on the allow list and has active access. "
                    f"Use the update endpoint to modify their entry."
                )

            # User exists but is inactive or expired - reactivate them
            logger.info(
                "Reactivating previously removed/expired user: %s (was active=%s, expired=%s)",
                email, existing.active, existing.is_expired
            )

            # Update existing entry with new details
            now = datetime.now(timezone.utc)
            updates = {
                "active": True,
                "reason": request.reason,
                "expires_at": request.expires_at,
                "notes": request.notes,
                "updated_at": now,
                "added_by": added_by.lower().strip(),  # Update who reactivated
                "added_at": now,  # Update when reactivated
            }

            try:
                self._collection.document(doc_id).update(updates)
                logger.info("Reactivated user on allow list: %s (by %s)", email, added_by)
                return self.get_user(email)
            except Exception as e:
                logger.error("Error reactivating user %s: %s", email, e)
                raise ValueError(f"Failed to reactivate user: {e}") from e

        # User doesn't exist - create new entry
        now = datetime.now(timezone.utc)
        entry = AllowListEntry(
            email=email,
            added_by=added_by.lower().strip(),
            added_at=now,
            reason=request.reason,
            expires_at=request.expires_at,
            active=True,
            notes=request.notes,
            updated_at=now,
        )

        try:
            self._collection.document(doc_id).set(entry.model_dump_for_firestore())
            logger.info("Added new user to allow list: %s (by %s)", email, added_by)
            return entry
        except Exception as e:
            logger.error("Error adding user to allow list %s: %s", email, e)
            raise ValueError(f"Failed to add user: {e}") from e

    def update_user(
        self,
        email: str,
        request: AllowListUpdateRequest,
    ) -> Optional[AllowListEntry]:
        """Update an allow list entry.

        Args:
            email: Email of user to update
            request: Update request with fields to change

        Returns:
            Updated AllowListEntry or None if not found

        Raises:
            ValueError: If service unavailable
        """
        if not self.is_available:
            raise ValueError("Allow list service is not available")

        existing = self.get_user(email)
        if existing is None:
            return None

        doc_id = _email_to_doc_id(email)

        # Build update dict with only provided fields
        updates = {"updated_at": datetime.now(timezone.utc)}
        if request.reason is not None:
            updates["reason"] = request.reason
        if request.expires_at is not None:
            updates["expires_at"] = request.expires_at
        if request.active is not None:
            updates["active"] = request.active
        if request.notes is not None:
            updates["notes"] = request.notes

        try:
            self._collection.document(doc_id).update(updates)
            logger.info("Updated allow list entry: %s", email)
            return self.get_user(email)
        except Exception as e:
            logger.error("Error updating allow list entry %s: %s", email, e)
            raise ValueError(f"Failed to update user: {e}") from e

    def remove_user(self, email: str, soft_delete: bool = True) -> bool:
        """Remove a user from the allow list.

        Args:
            email: Email of user to remove
            soft_delete: If True, set active=False; if False, delete document

        Returns:
            True if removed, False if not found
        """
        if not self.is_available:
            return False

        doc_id = _email_to_doc_id(email)

        try:
            doc_ref = self._collection.document(doc_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            if soft_delete:
                doc_ref.update({
                    "active": False,
                    "updated_at": datetime.now(timezone.utc)
                })
                logger.info("Soft-deleted allow list entry: %s", email)
            else:
                doc_ref.delete()
                logger.info("Hard-deleted allow list entry: %s", email)

            return True
        except Exception as e:
            logger.error("Error removing user from allow list %s: %s", email, e)
            return False


def get_allow_list_service() -> AllowListService:
    """Get an AllowListService instance."""
    return AllowListService()

