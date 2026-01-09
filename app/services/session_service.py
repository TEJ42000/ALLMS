"""Session Service for OAuth Authentication.

Provides session management functionality including:
- Session creation with encrypted token storage
- Session validation and retrieval
- Session invalidation (logout)
- Token encryption/decryption
- Expired session cleanup
"""

import base64
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.models.auth_models import AuthConfig, User
from app.models.session_models import OAuthTokens, Session
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Firestore collection name
SESSIONS_COLLECTION = "sessions"

# Salt for key derivation (constant, but secret key provides security)
_KEY_DERIVATION_SALT = b"lls_session_encryption_v1"


@lru_cache(maxsize=1)
def get_auth_config() -> AuthConfig:
    """Get the authentication configuration singleton."""
    return AuthConfig()


def _get_encryption_key(secret_key: str) -> bytes:
    """Derive a Fernet-compatible key from the secret key.

    Args:
        secret_key: The session secret key from config

    Returns:
        32-byte key suitable for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KEY_DERIVATION_SALT,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))


class SessionService:
    """Service for managing user sessions in Firestore."""

    def __init__(self):
        """Initialize the session service."""
        self.config = get_auth_config()
        self.db = get_firestore_client()
        self._collection = None
        self._fernet: Optional[Fernet] = None

        if self.db is not None:
            self._collection = self.db.collection(SESSIONS_COLLECTION)
        else:
            logger.warning("Firestore not available - sessions will not persist")

        if self.config.session_secret_key:
            key = _get_encryption_key(self.config.session_secret_key)
            self._fernet = Fernet(key)
        else:
            logger.warning("Session secret key not configured - tokens will not be encrypted")

    @property
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self.db is not None

    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for storage.

        Args:
            token: Plain text token

        Returns:
            Encrypted token (base64 encoded)
        """
        if self._fernet is None:
            logger.warning("Encryption not available, storing token in plain text")
            return token
        return self._fernet.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted: str) -> str:
        """Decrypt a stored token.

        Args:
            encrypted: Encrypted token

        Returns:
            Plain text token
        """
        if self._fernet is None:
            return encrypted
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except Exception as e:
            logger.error("Failed to decrypt token: %s", e)
            raise ValueError("Token decryption failed") from e

    async def create_session(
        self,
        user: User,
        tokens: OAuthTokens,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Session:
        """Create a new session for an authenticated user.

        Args:
            user: Authenticated user
            tokens: OAuth tokens from Google
            user_agent: Browser user agent
            ip_address: Client IP address

        Returns:
            Created Session object

        Raises:
            ValueError: If session creation fails
        """
        if not self.is_available:
            raise ValueError("Session service is not available")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.config.session_expiry_days)
        token_expiry = now + timedelta(seconds=tokens.expires_in)

        # Encrypt tokens before storage
        access_token_encrypted = self._encrypt_token(tokens.access_token)
        refresh_token_encrypted = None
        if tokens.refresh_token:
            refresh_token_encrypted = self._encrypt_token(tokens.refresh_token)

        session = Session(
            user_email=user.email,
            user_id=user.user_id,
            domain=user.domain,
            is_admin=user.is_admin,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expiry=token_expiry,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        try:
            self._collection.document(session.session_id).set(
                session.to_firestore_dict()
            )
            logger.info("Created new session successfully")
            return session
        except Exception as e:
            logger.error("Failed to create session: %s", e)
            raise ValueError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session if found and valid, None otherwise
        """
        if not self.is_available:
            return None

        try:
            doc = self._collection.document(session_id).get()
            if not doc.exists:
                return None

            session = Session.from_firestore_dict(doc.to_dict())
            return session
        except Exception as e:
            logger.error("Error getting session %s: %s", session_id, e)
            return None

    async def validate_session(self, session_id: str) -> tuple[bool, Optional[User]]:
        """Validate a session and return the user.

        Args:
            session_id: Session ID to validate

        Returns:
            Tuple of (is_valid, User or None)
        """
        session = await self.get_session(session_id)

        if session is None:
            logger.debug("Session not found: %s", session_id[:8] if session_id else "None")
            return False, None

        if session.is_expired:
            logger.info("Session expired: %s", session_id[:8])
            await self.invalidate_session(session_id)
            return False, None

        # Create User from session data
        user = User(
            email=session.user_email,
            user_id=session.user_id,
            domain=session.domain,
            is_admin=session.is_admin,
        )

        return True, user

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate (delete) a session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if invalidated, False if not found
        """
        if not self.is_available:
            return False

        try:
            doc_ref = self._collection.document(session_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            doc_ref.delete()
            logger.info("Invalidated session: %s", session_id[:8])
            return True
        except Exception as e:
            logger.error("Error invalidating session %s: %s", session_id, e)
            return False

    async def update_session_activity(self, session_id: str) -> bool:
        """Update the last_accessed timestamp for a session.

        Args:
            session_id: Session ID to update

        Returns:
            True if updated, False if not found
        """
        if not self.is_available:
            return False

        try:
            doc_ref = self._collection.document(session_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            doc_ref.update({"last_accessed": datetime.now(timezone.utc)})
            return True
        except Exception as e:
            logger.error("Error updating session activity %s: %s", session_id, e)
            return False

    async def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions.

        Returns:
            Number of sessions deleted
        """
        if not self.is_available:
            return 0

        now = datetime.now(timezone.utc)
        deleted_count = 0

        try:
            # Query for expired sessions
            expired_docs = self._collection.where(
                "expires_at", "<", now
            ).stream()

            for doc in expired_docs:
                doc.reference.delete()
                deleted_count += 1

            if deleted_count > 0:
                logger.info("Cleaned up %d expired sessions", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("Error cleaning up expired sessions: %s", e)
            return deleted_count

    def get_decrypted_tokens(self, session: Session) -> OAuthTokens:
        """Get decrypted OAuth tokens from a session.

        Args:
            session: Session with encrypted tokens

        Returns:
            OAuthTokens with decrypted values
        """
        access_token = self._decrypt_token(session.access_token_encrypted)
        refresh_token = None
        if session.refresh_token_encrypted:
            refresh_token = self._decrypt_token(session.refresh_token_encrypted)

        # Calculate remaining time
        now = datetime.now(timezone.utc)
        expires_in = max(0, int((session.token_expiry - now).total_seconds()))

        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )


def get_session_service() -> SessionService:
    """Get a SessionService instance."""
    return SessionService()

