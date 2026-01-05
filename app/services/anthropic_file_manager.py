"""Anthropic File Manager Service.

Manages the lifecycle of files in Anthropic's Files API:
- Upload files from local storage to Anthropic
- Track file IDs and expiry in Firestore
- Ensure files are available before API calls
- Refresh files before they expire
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from anthropic import Anthropic, NotFoundError as AnthropicNotFoundError, APIError

from app.models.course_models import CourseMaterial
from app.services.gcp_service import get_anthropic_api_key, get_firestore_client

logger = logging.getLogger(__name__)

# Configuration from environment with sensible defaults and validation
def _get_validated_retention_days() -> int:
    """Get FILE_RETENTION_DAYS from env, ensuring positive value."""
    try:
        value = int(os.getenv("ANTHROPIC_FILE_RETENTION_DAYS", "30"))
        return max(1, value)  # Ensure at least 1 day
    except ValueError:
        return 30  # Default if env var is not a valid integer

def _get_validated_refresh_days(retention_days: int) -> int:
    """Get REFRESH_BEFORE_EXPIRY_DAYS from env, ensuring positive and less than retention."""
    try:
        value = int(os.getenv("ANTHROPIC_REFRESH_BEFORE_EXPIRY_DAYS", "7"))
        # Ensure positive and at most retention_days - 1
        return max(1, min(retention_days - 1, value))
    except ValueError:
        return min(7, retention_days - 1)  # Default if env var is not valid

FILE_RETENTION_DAYS = _get_validated_retention_days()
REFRESH_BEFORE_EXPIRY_DAYS = _get_validated_refresh_days(FILE_RETENTION_DAYS)

# File upload limits with validation
def _get_validated_max_file_size() -> int:
    """Get MAX_FILE_SIZE_MB from env, ensuring positive and reasonable value."""
    try:
        value = int(os.getenv("ANTHROPIC_MAX_FILE_SIZE_MB", "100"))
        return max(1, min(1000, value))  # Cap between 1MB and 1GB
    except ValueError:
        return 100  # Default if env var is not a valid integer

MAX_FILE_SIZE_MB = _get_validated_max_file_size()
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported file extensions for upload
SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.pptx', '.html', '.htm'}

# Local materials root directory
MATERIALS_ROOT = Path("Materials").resolve()


class AnthropicFileManagerError(Exception):
    """Base exception for Anthropic File Manager errors."""
    pass


class LocalFileNotFoundError(AnthropicFileManagerError):
    """Local file not found."""
    pass


class UploadError(AnthropicFileManagerError):
    """Failed to upload file to Anthropic."""
    pass


class PathTraversalError(AnthropicFileManagerError):
    """Attempted path traversal attack detected."""
    pass


class FileValidationError(AnthropicFileManagerError):
    """File validation failed (size, type, etc.)."""
    pass


class AnthropicFileManager:
    """Manages files in Anthropic's Files API.
    
    This service bridges the gap between local/GCS storage and Anthropic's
    Files API, ensuring materials are uploaded and available for AI processing.
    """
    
    def __init__(self):
        """Initialize the file manager."""
        self.client = Anthropic(api_key=get_anthropic_api_key())
        self._firestore = None
    
    @property
    def firestore(self):
        """Lazy-load Firestore client."""
        if self._firestore is None:
            self._firestore = get_firestore_client()
        return self._firestore
    
    def get_local_file_path(self, material: CourseMaterial) -> Path:
        """Get the local file path for a material with path traversal protection.

        Args:
            material: The course material

        Returns:
            Path to the local file (validated to be within MATERIALS_ROOT)

        Raises:
            PathTraversalError: If the path attempts to escape MATERIALS_ROOT
        """
        # Resolve the path to prevent path traversal attacks
        file_path = (MATERIALS_ROOT / material.storagePath).resolve()

        # Ensure the resolved path is within MATERIALS_ROOT
        try:
            file_path.relative_to(MATERIALS_ROOT)
        except ValueError:
            raise PathTraversalError(
                f"Invalid storage path (path traversal detected): {material.storagePath}"
            )

        return file_path

    def _validate_file_for_upload(self, file_path: Path) -> None:
        """Validate a file before uploading to Anthropic.

        Args:
            file_path: Path to the file to validate

        Raises:
            LocalFileNotFoundError: If file doesn't exist
            FileValidationError: If file fails validation
        """
        if not file_path.exists():
            raise LocalFileNotFoundError(f"Local file not found: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise FileValidationError(
                f"File too large: {file_size / (1024*1024):.1f}MB "
                f"(max: {MAX_FILE_SIZE_MB}MB)"
            )

        if file_size == 0:
            raise FileValidationError("File is empty")

        # Check file extension
        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise FileValidationError(
                f"Unsupported file type: {suffix}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

    def upload_file(self, material: CourseMaterial) -> str:
        """Upload a file to Anthropic's Files API.

        Args:
            material: The course material to upload

        Returns:
            The Anthropic file ID

        Raises:
            LocalFileNotFoundError: If local file doesn't exist
            FileValidationError: If file fails validation
            PathTraversalError: If path traversal detected
            UploadError: If upload fails
        """
        file_path = self.get_local_file_path(material)

        # Validate file before upload
        self._validate_file_for_upload(file_path)

        try:
            logger.info("Uploading file to Anthropic: %s", material.filename)

            uploaded_file = self.client.beta.files.upload(file=file_path)

            logger.info(
                "Successfully uploaded %s -> %s",
                material.filename,
                uploaded_file.id
            )

            return uploaded_file.id

        except (LocalFileNotFoundError, FileValidationError, PathTraversalError):
            # Re-raise our custom exceptions
            raise
        except APIError as e:
            logger.error("Anthropic API error uploading %s: %s", material.filename, str(e))
            raise UploadError(f"Anthropic API error: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error uploading %s: %s", material.filename, str(e))
            raise UploadError(f"Failed to upload {material.filename}: {str(e)}") from e
    
    def check_file_exists(self, file_id: str) -> bool:
        """Check if a file still exists in Anthropic's storage.

        Args:
            file_id: The Anthropic file ID

        Returns:
            True if file exists, False otherwise
        """
        print(f"DEBUG check_file_exists: Checking {file_id}")
        try:
            result = self.client.beta.files.retrieve_metadata(file_id)
            print(f"DEBUG check_file_exists: File exists, result={result}")
            return True
        except AnthropicNotFoundError as e:
            print(f"DEBUG check_file_exists: NotFoundError - {e}")
            logger.debug("File not found in Anthropic: %s", file_id)
            return False
        except APIError as e:
            print(f"DEBUG check_file_exists: APIError - {e}")
            logger.warning("API error checking file %s: %s", file_id, str(e))
            return False
        except Exception as e:
            print(f"DEBUG check_file_exists: Exception ({type(e).__name__}) - {e}")
            logger.error("Unexpected error checking file %s: %s", file_id, str(e))
            return False

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Anthropic's storage.

        Args:
            file_id: The Anthropic file ID

        Returns:
            True if deleted, False if file didn't exist
        """
        try:
            self.client.beta.files.delete(file_id)
            logger.info("Deleted file from Anthropic: %s", file_id)
            return True
        except AnthropicNotFoundError:
            logger.debug("File already deleted or not found: %s", file_id)
            return False
        except APIError as e:
            logger.warning("API error deleting file %s: %s", file_id, str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error deleting file %s: %s", file_id, str(e))
            return False

    def ensure_file_available(
        self,
        material: CourseMaterial,
        course_id: str
    ) -> str:
        """Ensure a file is available in Anthropic, uploading if needed.

        This method:
        1. Checks if material has a valid anthropicFileId
        2. Verifies the file still exists in Anthropic
        3. Re-uploads if expired or missing
        4. Updates Firestore with new file ID

        Note on concurrency:
            This method does not use distributed locking. Concurrent calls for
            the same material are safe (won't corrupt data), but may trigger
            redundant uploads. This is acceptable given the infrequent nature
            of uploads and the automatic expiry refresh mechanism. If high
            concurrency becomes an issue, consider using Firestore transactions
            or distributed locks.

        Args:
            material: The course material
            course_id: The course ID (for Firestore update)

        Returns:
            The Anthropic file ID (existing or newly uploaded)

        Raises:
            LocalFileNotFoundError: If local file doesn't exist
            UploadError: If upload fails
        """
        now = datetime.now(timezone.utc)

        # Check if we have a valid, non-expired file ID
        if material.anthropicFileId:
            print(f"DEBUG: Material {material.filename} has existing file_id={material.anthropicFileId}")
            print(f"DEBUG:   expiry={material.anthropicFileExpiry}, now={now}")
            # Check expiry
            if material.anthropicFileExpiry and material.anthropicFileExpiry > now:
                print(f"DEBUG:   File not expired, checking if exists...")
                # File should still be valid, but verify it exists
                exists = self.check_file_exists(material.anthropicFileId)
                print(f"DEBUG:   check_file_exists returned: {exists}")
                if exists:
                    logger.debug(
                        "File %s still valid in Anthropic: %s",
                        material.filename,
                        material.anthropicFileId
                    )
                    return material.anthropicFileId
            else:
                print(f"DEBUG:   File expired or no expiry set")

            # File expired or doesn't exist - need to re-upload
            print(f"DEBUG:   Will re-upload {material.filename}")
            logger.info(
                "File %s expired or missing, re-uploading...",
                material.filename
            )
        else:
            print(f"DEBUG: Material {material.filename} has no existing file_id")

        # Upload the file
        print(f"DEBUG: Uploading file {material.filename}...")
        file_id = self.upload_file(material)
        print(f"DEBUG: Uploaded {material.filename} -> {file_id}")

        # Calculate expiry
        expiry = now + timedelta(days=FILE_RETENTION_DAYS)

        # Update material record in Firestore
        self._update_material_anthropic_fields(
            course_id=course_id,
            material_id=material.id,
            file_id=file_id,
            uploaded_at=now,
            expiry=expiry,
            error=None
        )

        return file_id

    def _update_material_anthropic_fields(
        self,
        course_id: str,
        material_id: str,
        file_id: Optional[str] = None,
        uploaded_at: Optional[datetime] = None,
        expiry: Optional[datetime] = None,
        error: Optional[str] = None
    ) -> None:
        """Update Anthropic-related fields on a material document.

        Args:
            course_id: Course ID
            material_id: Material document ID
            file_id: Anthropic file ID
            uploaded_at: Upload timestamp
            expiry: Expiry timestamp
            error: Error message if upload failed
        """
        if not self.firestore:
            logger.warning("Firestore not available, skipping material update")
            return

        update_data: Dict[str, Any] = {
            "updatedAt": datetime.now(timezone.utc)
        }

        if file_id is not None:
            update_data["anthropicFileId"] = file_id
        if uploaded_at is not None:
            update_data["anthropicUploadedAt"] = uploaded_at
        if expiry is not None:
            update_data["anthropicFileExpiry"] = expiry
        if error is not None:
            update_data["anthropicUploadError"] = error
        elif file_id is not None:
            # Clear error if upload succeeded
            update_data["anthropicUploadError"] = None

        try:
            doc_ref = (
                self.firestore
                .collection("courses")
                .document(course_id)
                .collection("materials")
                .document(material_id)
            )
            doc_ref.update(update_data)
            logger.debug("Updated material %s with Anthropic fields", material_id)
        except Exception as e:
            logger.error(
                "Failed to update material %s: %s",
                material_id,
                str(e)
            )
            # Re-raise to notify caller that Firestore update failed
            # This prevents silent failures where file ID is lost
            raise AnthropicFileManagerError(
                f"Failed to update Firestore for material {material_id}: {e}"
            ) from e

    def get_materials_needing_upload(
        self,
        course_id: str
    ) -> List[Dict[str, Any]]:
        """Get materials that need to be uploaded to Anthropic.

        Returns materials that either:
        - Have no anthropicFileId
        - Have expired or soon-to-expire files

        Args:
            course_id: Course ID

        Returns:
            List of material documents
        """
        if not self.firestore:
            return []

        now = datetime.now(timezone.utc)
        refresh_threshold = now + timedelta(days=REFRESH_BEFORE_EXPIRY_DAYS)

        materials_ref = (
            self.firestore
            .collection("courses")
            .document(course_id)
            .collection("materials")
        )

        # Get all materials
        docs = materials_ref.stream()

        needing_upload = []
        for doc in docs:
            data = doc.to_dict()
            if not data:
                logger.warning("Material %s has no data, skipping", doc.id)
                continue
            data["id"] = doc.id

            # Check if needs upload
            file_id = data.get("anthropicFileId")
            expiry = data.get("anthropicFileExpiry")

            if not file_id:
                needing_upload.append(data)
            elif expiry and expiry < refresh_threshold:
                needing_upload.append(data)

        return needing_upload

    def refresh_course_files(
        self,
        course_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """Refresh all files for a course that are expired or expiring soon.

        Args:
            course_id: Course ID
            force: If True, re-upload all files regardless of expiry

        Returns:
            Summary dict with counts of uploaded, skipped, failed
        """
        if not self.firestore:
            return {"error": "Firestore not available"}

        materials_ref = (
            self.firestore
            .collection("courses")
            .document(course_id)
            .collection("materials")
        )

        docs = list(materials_ref.stream())

        results = {
            "total": len(docs),
            "uploaded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

        now = datetime.now(timezone.utc)
        refresh_threshold = now + timedelta(days=REFRESH_BEFORE_EXPIRY_DAYS)

        for doc in docs:
            data = doc.to_dict()
            if not data:
                logger.warning("Material %s has no data, skipping", doc.id)
                results["skipped"] += 1
                continue
            material = CourseMaterial(**data, id=doc.id)

            # Check if needs upload
            needs_upload = force or not material.anthropicFileId
            if not needs_upload and material.anthropicFileExpiry:
                needs_upload = material.anthropicFileExpiry < refresh_threshold

            if not needs_upload:
                results["skipped"] += 1
                continue

            try:
                file_id = self.upload_file(material)
                expiry = now + timedelta(days=FILE_RETENTION_DAYS)

                self._update_material_anthropic_fields(
                    course_id=course_id,
                    material_id=doc.id,
                    file_id=file_id,
                    uploaded_at=now,
                    expiry=expiry
                )

                results["uploaded"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "material_id": doc.id,
                    "filename": material.filename,
                    "error": str(e)
                })

                # Record error in Firestore
                self._update_material_anthropic_fields(
                    course_id=course_id,
                    material_id=doc.id,
                    error=str(e)
                )

        logger.info(
            "Refreshed course %s: %d uploaded, %d skipped, %d failed",
            course_id,
            results["uploaded"],
            results["skipped"],
            results["failed"]
        )

        return results


# Singleton instance
_file_manager: Optional[AnthropicFileManager] = None


def get_anthropic_file_manager() -> AnthropicFileManager:
    """Get the singleton AnthropicFileManager instance."""
    global _file_manager
    if _file_manager is None:
        _file_manager = AnthropicFileManager()
    return _file_manager

