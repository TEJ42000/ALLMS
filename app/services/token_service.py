"""
Token Service for Secure Operations

Generates and validates secure tokens for sensitive operations like
account deletion, email verification, and password resets.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Secret key for token generation (in production, load from environment/secrets)
# This should be a long, random string stored securely
TOKEN_SECRET = secrets.token_hex(32)  # Generate a random secret on startup

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


# Email sending functionality (placeholder - implement with actual email service)
async def send_deletion_confirmation_email(
    email: str,
    user_id: str,
    token: str,
    expiry: datetime
) -> bool:
    """Send account deletion confirmation email.
    
    In production, this should use an email service like SendGrid, AWS SES, etc.
    For now, this is a placeholder that logs the email content.
    
    Args:
        email: User's email address
        user_id: User ID
        token: Deletion confirmation token
        expiry: Token expiry datetime
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # TODO: Implement actual email sending
    # For now, just log the email content
    
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    email_content = f"""
    Subject: Confirm Account Deletion - ALLMS
    
    To: {email}
    
    Dear User,
    
    You have requested to delete your ALLMS account. This action is permanent and cannot be undone.
    
    To confirm account deletion, please use the following token:
    
    {token}
    
    This token will expire at: {expiry_str}
    
    If you did not request this deletion, please ignore this email and your account will remain active.
    
    For security reasons, this token can only be used once and will expire in 30 minutes.
    
    Best regards,
    ALLMS Team
    
    ---
    This is an automated message. Please do not reply to this email.
    """
    
    logger.info(f"[EMAIL PLACEHOLDER] Deletion confirmation email for {email}:")
    logger.info(email_content)
    
    # In production, replace with actual email sending:
    # try:
    #     email_service.send(
    #         to=email,
    #         subject="Confirm Account Deletion - ALLMS",
    #         body=email_content
    #     )
    #     return True
    # except Exception as e:
    #     logger.error(f"Failed to send deletion email: {e}")
    #     return False
    
    return True  # Placeholder success

