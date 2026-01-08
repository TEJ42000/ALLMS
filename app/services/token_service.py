"""
Token Service for Secure Operations

Generates and validates secure tokens for sensitive operations like
account deletion, email verification, and password resets.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Secret key for token generation
# IMPORTANT: In production, set GDPR_TOKEN_SECRET environment variable
# This should be a long, random string stored securely (e.g., in Google Secret Manager)
TOKEN_SECRET = os.getenv('GDPR_TOKEN_SECRET')

# Check if we're in production
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT in ['production', 'prod']

# Development secret file path (for persistent tokens in dev)
DEV_SECRET_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.dev_token_secret')

if not TOKEN_SECRET:
    if IS_PRODUCTION:
        # CRITICAL: In production, TOKEN_SECRET is required
        error_msg = (
            "CRITICAL: GDPR_TOKEN_SECRET environment variable is not set in production! "
            "This is a security requirement. Generate a secret with: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\" "
            "and store it in Google Secret Manager or environment variables."
        )
        logger.critical(error_msg)
        raise ValueError(error_msg)
    else:
        # Development fallback: use persistent secret file
        # This prevents token invalidation on restart
        try:
            if os.path.exists(DEV_SECRET_FILE):
                with open(DEV_SECRET_FILE, 'r') as f:
                    TOKEN_SECRET = f.read().strip()
                logger.info("Loaded development token secret from .dev_token_secret file")
            else:
                # Generate new secret and save it
                TOKEN_SECRET = secrets.token_hex(32)
                with open(DEV_SECRET_FILE, 'w') as f:
                    f.write(TOKEN_SECRET)
                logger.warning(
                    "GDPR_TOKEN_SECRET not set in environment. Generated new development secret "
                    "and saved to .dev_token_secret file. This secret will persist across restarts. "
                    "For production, set GDPR_TOKEN_SECRET environment variable."
                )
        except Exception as e:
            # Fallback to random secret if file operations fail
            TOKEN_SECRET = secrets.token_hex(32)
            logger.warning(
                f"Failed to read/write development secret file: {e}. "
                "Using random secret (tokens will be invalidated on restart). "
                "For production, set GDPR_TOKEN_SECRET environment variable."
            )
else:
    # Validate token secret length
    if len(TOKEN_SECRET) < 64:
        error_msg = (
            f"GDPR_TOKEN_SECRET is too short ({len(TOKEN_SECRET)} chars). "
            "It must be at least 64 characters (32 bytes hex-encoded) for security. "
            "Generate a new secret with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )
        if IS_PRODUCTION:
            logger.critical(error_msg)
            raise ValueError(error_msg)
        else:
            logger.warning(error_msg)
    else:
        logger.info(f"GDPR_TOKEN_SECRET loaded successfully ({len(TOKEN_SECRET)} chars)")

# Token expiration times
TOKEN_EXPIRY_MINUTES = {
    "account_deletion": 30,  # 30 minutes to confirm deletion
    "email_verification": 60,  # 1 hour to verify email
    "password_reset": 15,  # 15 minutes to reset password
}


def generate_secure_token(
    user_id: str,
    operation: str = "account_deletion",
    expiry_minutes: Optional[int] = None
) -> Tuple[str, datetime]:
    """Generate a secure token for a specific operation.
    
    Args:
        user_id: User ID
        operation: Type of operation (account_deletion, email_verification, etc.)
        expiry_minutes: Custom expiry time in minutes (overrides default)
        
    Returns:
        Tuple of (token, expiry_datetime)
    """
    # Get expiry time
    if expiry_minutes is None:
        expiry_minutes = TOKEN_EXPIRY_MINUTES.get(operation, 30)
    
    expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    expiry_timestamp = int(expiry_time.timestamp())
    
    # Generate random component
    random_component = secrets.token_urlsafe(32)
    
    # Create token payload
    payload = f"{user_id}:{operation}:{expiry_timestamp}:{random_component}"
    
    # Generate HMAC signature
    signature = hmac.new(
        TOKEN_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Combine payload and signature
    token = f"{payload}:{signature}"
    
    logger.info(f"Generated {operation} token for user {user_id}, expires at {expiry_time}")
    
    return token, expiry_time


def validate_token(
    token: str,
    user_id: str,
    operation: str = "account_deletion"
) -> Tuple[bool, Optional[str]]:
    """Validate a secure token.
    
    Args:
        token: Token to validate
        user_id: Expected user ID
        operation: Expected operation type
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    try:
        # Split token into payload and signature
        parts = token.split(':')
        if len(parts) != 5:
            return False, "Invalid token format"
        
        token_user_id, token_operation, expiry_timestamp_str, random_component, provided_signature = parts
        
        # Verify user ID matches
        if token_user_id != user_id:
            logger.warning(f"Token user ID mismatch: expected {user_id}, got {token_user_id}")
            return False, "Token user ID mismatch"
        
        # Verify operation matches
        if token_operation != operation:
            logger.warning(f"Token operation mismatch: expected {operation}, got {token_operation}")
            return False, "Token operation mismatch"
        
        # Check expiry
        try:
            expiry_timestamp = int(expiry_timestamp_str)
            expiry_time = datetime.fromtimestamp(expiry_timestamp)
            
            if datetime.utcnow() > expiry_time:
                logger.warning(f"Token expired for user {user_id}")
                return False, "Token has expired"
        except (ValueError, OSError) as e:
            logger.error(f"Invalid expiry timestamp: {e}")
            return False, "Invalid token expiry"
        
        # Reconstruct payload
        payload = f"{token_user_id}:{token_operation}:{expiry_timestamp_str}:{random_component}"
        
        # Verify signature
        expected_signature = hmac.new(
            TOKEN_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, provided_signature):
            logger.warning(f"Token signature mismatch for user {user_id}")
            return False, "Invalid token signature"
        
        logger.info(f"Token validated successfully for user {user_id}, operation {operation}")
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating token: {e}", exc_info=True)
        return False, "Token validation error"


def generate_deletion_token(user_id: str, email: str) -> Tuple[str, datetime]:
    """Generate a secure token for account deletion.
    
    This is a convenience wrapper around generate_secure_token specifically
    for account deletion operations.
    
    Args:
        user_id: User ID
        email: User email (for logging purposes)
        
    Returns:
        Tuple of (token, expiry_datetime)
    """
    token, expiry = generate_secure_token(user_id, "account_deletion")
    logger.info(f"Generated deletion token for {email} (user {user_id})")
    return token, expiry


def validate_deletion_token(token: str, user_id: str, email: str) -> Tuple[bool, Optional[str]]:
    """Validate an account deletion token.
    
    This is a convenience wrapper around validate_token specifically
    for account deletion operations.
    
    Args:
        token: Token to validate
        user_id: User ID
        email: User email (for logging purposes)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_token(token, user_id, "account_deletion")
    
    if is_valid:
        logger.info(f"Deletion token validated for {email} (user {user_id})")
    else:
        logger.warning(f"Deletion token validation failed for {email} (user {user_id}): {error}")
    
    return is_valid, error


# Email sending functionality
async def send_deletion_confirmation_email(
    email: str,
    user_id: str,
    token: str,
    expiry: datetime
) -> bool:
    """Send account deletion confirmation email.

    Uses configured email service (SendGrid, AWS SES, or console for development).
    Email provider is configured via EMAIL_SERVICE_PROVIDER environment variable.

    Args:
        email: User's email address
        user_id: User ID
        token: Deletion confirmation token
        expiry: Token expiry datetime

    Returns:
        True if email sent successfully, False otherwise
    """
    # Log email details for debugging
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"Sending deletion confirmation email to {email} (expires: {expiry_str})")
    
    # Use real email service
    try:
        from app.services.email_service import get_email_service

        email_service = get_email_service()
        success = await email_service.send_deletion_confirmation_email(
            to_email=email,
            user_id=user_id,
            token=token,
            expiry=expiry
        )

        if success:
            logger.info(f"Deletion confirmation email sent successfully to {email}")
        else:
            logger.error(f"Failed to send deletion confirmation email to {email}")

        return success

    except Exception as e:
        logger.error(f"Error sending deletion confirmation email: {e}", exc_info=True)
        return False

