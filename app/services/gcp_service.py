"""Google Cloud Platform Services using Application Default Credentials.

This module provides centralized access to GCP services (Secret Manager, Firestore)
using Application Default Credentials (ADC). ADC works seamlessly in both:
- Local development: `gcloud auth application-default login`
- Cloud Run: Automatic service account credentials

For secrets, it attempts to retrieve from Secret Manager first, then falls back
to environment variables if Secret Manager is unavailable.
"""

import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Project configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "vigilant-axis-483119-r8")

# ============================================================================
# Secret Manager (using ADC with .env fallback)
# ============================================================================

_secret_manager_client = None
_secret_manager_available = None


def _get_secret_manager_client():
    """Get Secret Manager client, checking availability once."""
    global _secret_manager_client, _secret_manager_available
    
    if _secret_manager_available is False:
        return None
    
    if _secret_manager_client is None:
        try:
            from google.cloud import secretmanager
            _secret_manager_client = secretmanager.SecretManagerServiceClient()
            _secret_manager_available = True
            logger.info("Secret Manager client initialized for project: %s", GCP_PROJECT_ID)
        except Exception as e:
            _secret_manager_available = False
            logger.warning("Secret Manager not available, will use .env fallback: %s", str(e))
            return None
    
    return _secret_manager_client


@lru_cache(maxsize=10)
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """
    Retrieve a secret from Google Secret Manager using ADC.
    
    Falls back to environment variable if Secret Manager is unavailable.
    
    Works with:
    - Local dev: `gcloud auth application-default login`
    - Cloud Run: Automatic service account credentials
    - Fallback: Environment variable with same name (uppercase, hyphens to underscores)
    
    Args:
        secret_id: Name of the secret (e.g., "anthropic-api-key")
        version: Version to retrieve (default: "latest")
    
    Returns:
        The secret value as a string, or None if not found
    """
    client = _get_secret_manager_client()
    
    if client is not None:
        try:
            name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version}"
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info("Retrieved secret '%s' from Secret Manager", secret_id)
            return secret_value
        except Exception as e:
            logger.warning("Failed to get secret '%s' from Secret Manager: %s", secret_id, str(e))
    
    # Fallback to environment variable
    # Convert secret-id to ENV_VAR format: anthropic-api-key -> ANTHROPIC_API_KEY
    env_var_name = secret_id.upper().replace("-", "_")
    env_value = os.getenv(env_var_name)
    
    if env_value:
        logger.info("Using '%s' from environment variable", env_var_name)
        return env_value
    
    logger.error("Secret '%s' not found in Secret Manager or environment (%s)", secret_id, env_var_name)
    return None


def get_anthropic_api_key() -> str:
    """
    Get Anthropic API key from Secret Manager or environment.
    
    Priority:
    1. Secret Manager (via ADC) - secret name: "anthropic-api-key"
    2. Environment variable: ANTHROPIC_API_KEY
    
    Returns:
        The Anthropic API key
        
    Raises:
        ValueError: If no API key is found
    """
    api_key = get_secret("anthropic-api-key")
    
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Either:\n"
            "1. Set up ADC and store key in Secret Manager as 'anthropic-api-key'\n"
            "2. Set ANTHROPIC_API_KEY environment variable"
        )
    
    return api_key


# ============================================================================
# Firestore Client (using ADC)
# ============================================================================

_firestore_client = None
_firestore_available = None


def get_firestore_client():
    """
    Get Firestore client using ADC.
    
    Singleton pattern to reuse connection.
    
    Returns:
        Firestore Client instance, or None if unavailable
    """
    global _firestore_client, _firestore_available
    
    if _firestore_available is False:
        return None
    
    if _firestore_client is None:
        try:
            from google.cloud import firestore
            _firestore_client = firestore.Client(project=GCP_PROJECT_ID)
            _firestore_available = True
            logger.info("Firestore client initialized for project: %s", GCP_PROJECT_ID)
        except Exception as e:
            _firestore_available = False
            logger.warning("Firestore not available: %s", str(e))
            return None
    
    return _firestore_client


def is_firestore_available() -> bool:
    """Check if Firestore is available."""
    client = get_firestore_client()
    return client is not None

