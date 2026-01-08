"""Storage Service for File Uploads.

Provides abstraction layer for file storage with support for:
- Local filesystem (development/testing)
- Google Cloud Storage (production)

Environment Variables:
    STORAGE_BACKEND: 'local' or 'gcs' (default: 'local')
    UPLOAD_BUCKET: GCS bucket name for uploads (required if STORAGE_BACKEND=gcs)
    GCP_PROJECT_ID: Google Cloud project ID (required if STORAGE_BACKEND=gcs)
"""

import logging
import os
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from datetime import timedelta

logger = logging.getLogger(__name__)


class StorageBackend:
    """Base class for storage backends."""
    
    def save_file(self, file: BinaryIO, path: str) -> str:
        """
        Save file to storage.
        
        Args:
            file: File-like object to save
            path: Relative path for the file (e.g., "uploads/course-id/filename.pdf")
            
        Returns:
            Storage path/URL for the saved file
        """
        raise NotImplementedError
    
    def get_file_path(self, path: str) -> Path:
        """
        Get local file path for reading.
        
        Args:
            path: Storage path from save_file()
            
        Returns:
            Local Path object for reading the file
        """
        raise NotImplementedError
    
    def delete_file(self, path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            path: Storage path from save_file()
            
        Returns:
            True if deleted successfully, False otherwise
        """
        raise NotImplementedError
    
    def file_exists(self, path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            path: Storage path to check
            
        Returns:
            True if file exists, False otherwise
        """
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development/testing."""

    def __init__(self, base_dir: str = "Materials"):
        self.base_dir = Path(base_dir).resolve()  # Resolve to absolute path
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local storage backend: {self.base_dir.absolute()}")

    def _validate_path(self, path: str) -> Path:
        """
        Validate that a path is within the base directory.

        CRITICAL SECURITY: Prevents path traversal attacks.

        Args:
            path: Relative path to validate

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path would escape base directory
        """
        # Construct full path
        full_path = (self.base_dir / path).resolve()

        # Ensure the resolved path is within base_dir
        try:
            # Check using commonpath
            common = Path(os.path.commonpath([self.base_dir, full_path]))
            if common != self.base_dir:
                raise ValueError(f"Path traversal detected: {path}")
        except ValueError as e:
            raise ValueError(f"Invalid path: {path}") from e

        # Additional string-based check
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected: {path}")

        return full_path

    def save_file(self, file: BinaryIO, path: str) -> str:
        """
        Save file to local filesystem.

        SECURITY: Validates path to prevent directory traversal.
        """
        # Validate path before use
        file_path = self._validate_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        with open(file_path, "wb") as f:
            file.seek(0)
            while chunk := file.read(8192):
                f.write(chunk)

        logger.info(f"Saved file to local storage: {file_path}")
        return str(path)

    def get_file_path(self, path: str) -> Path:
        """
        Get local file path.

        SECURITY: Validates path to prevent directory traversal.
        """
        return self._validate_path(path)

    def delete_file(self, path: str) -> bool:
        """
        Delete file from local filesystem.

        SECURITY: Validates path to prevent directory traversal.
        """
        try:
            file_path = self._validate_path(path)
            file_path.unlink(missing_ok=True)
            logger.info(f"Deleted file from local storage: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False

    def file_exists(self, path: str) -> bool:
        """
        Check if file exists locally.

        SECURITY: Validates path to prevent directory traversal.
        """
        try:
            file_path = self._validate_path(path)
            return file_path.exists()
        except ValueError:
            # Invalid path
            return False


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend for production."""
    
    def __init__(self):
        try:
            from google.cloud import storage
            
            self.bucket_name = os.getenv("UPLOAD_BUCKET")
            if not self.bucket_name:
                raise ValueError("UPLOAD_BUCKET environment variable not set")
            
            project_id = os.getenv("GCP_PROJECT_ID")
            
            self.client = storage.Client(project=project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise ValueError(f"GCS bucket '{self.bucket_name}' does not exist")
            
            logger.info(f"Using GCS storage backend: gs://{self.bucket_name}")
            
            # Create temp directory for downloads
            self.temp_dir = Path("/tmp/upload_cache")
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
        except ImportError:
            logger.error("google-cloud-storage package not installed. Install with: pip install google-cloud-storage")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GCS storage: {e}")
            raise
    
    def save_file(self, file: BinaryIO, path: str) -> str:
        """Save file to Google Cloud Storage."""
        blob = self.bucket.blob(path)
        
        # Upload file
        file.seek(0)
        blob.upload_from_file(file, content_type=self._guess_content_type(path))
        
        logger.info(f"Saved file to GCS: gs://{self.bucket_name}/{path}")
        return f"gs://{self.bucket_name}/{path}"
    
    def get_file_path(self, path: str) -> Path:
        """
        Download file from GCS to temp directory and return local path.
        
        Note: This creates a temporary local copy for processing.
        """
        # Remove gs:// prefix if present
        if path.startswith("gs://"):
            path = path.replace(f"gs://{self.bucket_name}/", "")
        
        # Create temp file path
        temp_path = self.temp_dir / path
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download if not already cached
        if not temp_path.exists():
            blob = self.bucket.blob(path)
            blob.download_to_filename(str(temp_path))
            logger.info(f"Downloaded file from GCS to temp: {temp_path}")
        
        return temp_path
    
    def delete_file(self, path: str) -> bool:
        """Delete file from Google Cloud Storage."""
        try:
            # Remove gs:// prefix if present
            if path.startswith("gs://"):
                path = path.replace(f"gs://{self.bucket_name}/", "")
            
            blob = self.bucket.blob(path)
            blob.delete()
            
            # Also delete from temp cache if exists
            temp_path = self.temp_dir / path
            temp_path.unlink(missing_ok=True)
            
            logger.info(f"Deleted file from GCS: gs://{self.bucket_name}/{path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path} from GCS: {e}")
            return False
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists in GCS."""
        # Remove gs:// prefix if present
        if path.startswith("gs://"):
            path = path.replace(f"gs://{self.bucket_name}/", "")
        
        blob = self.bucket.blob(path)
        return blob.exists()
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
    
    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary file access.
        
        Args:
            path: Storage path
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Signed URL for file access
        """
        # Remove gs:// prefix if present
        if path.startswith("gs://"):
            path = path.replace(f"gs://{self.bucket_name}/", "")
        
        blob = self.bucket.blob(path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET"
        )
        return url


# Singleton instance
_storage_backend: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Get the configured storage backend (singleton)."""
    global _storage_backend
    
    if _storage_backend is not None:
        return _storage_backend
    
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    
    if backend == "gcs":
        try:
            _storage_backend = GCSStorageBackend()
            logger.info("Using GCS storage backend (production mode)")
        except Exception as e:
            logger.error(f"Failed to initialize GCS storage: {e}")
            logger.warning("Falling back to local storage backend")
            _storage_backend = LocalStorageBackend()
    else:
        _storage_backend = LocalStorageBackend()
        logger.info("Using local storage backend (development mode)")
    
    return _storage_backend

