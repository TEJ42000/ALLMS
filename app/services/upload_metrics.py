"""Upload Metrics and Monitoring Service.

Provides structured logging and metrics for upload operations.
Integrates with Google Cloud Monitoring in production.

Environment Variables:
    ENABLE_CLOUD_MONITORING: 'true' or 'false' (default: 'false')
    GCP_PROJECT_ID: Google Cloud project ID (required if ENABLE_CLOUD_MONITORING=true)
"""

import logging
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class UploadStatus(str, Enum):
    """Upload operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    INVALID_FILE = "invalid_file"
    STORAGE_ERROR = "storage_error"


class ExtractionStatus(str, Enum):
    """Text extraction status."""
    SUCCESS = "success"
    FAILED = "failed"
    QUEUED = "queued"
    PROCESSING = "processing"


class UploadMetrics:
    """Metrics collector for upload operations."""
    
    def __init__(self):
        self.cloud_monitoring_enabled = os.getenv("ENABLE_CLOUD_MONITORING", "false").lower() == "true"
        
        if self.cloud_monitoring_enabled:
            try:
                from google.cloud import monitoring_v3
                
                project_id = os.getenv("GCP_PROJECT_ID")
                if not project_id:
                    raise ValueError("GCP_PROJECT_ID not set")
                
                self.client = monitoring_v3.MetricServiceClient()
                self.project_name = f"projects/{project_id}"
                logger.info("Cloud Monitoring enabled for upload metrics")
                
            except ImportError:
                logger.warning("google-cloud-monitoring not installed, using logging only")
                self.cloud_monitoring_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Cloud Monitoring: {e}")
                self.cloud_monitoring_enabled = False
    
    def record_upload(
        self,
        status: UploadStatus,
        file_size: int,
        file_type: str,
        duration_ms: float,
        user_id: str,
        course_id: str,
        error: Optional[str] = None
    ):
        """
        Record an upload operation.
        
        Args:
            status: Upload status
            file_size: File size in bytes
            file_type: File extension
            duration_ms: Upload duration in milliseconds
            user_id: User identifier
            course_id: Course identifier
            error: Error message if failed
        """
        # Structured logging
        log_data = {
            "event": "upload",
            "status": status.value,
            "file_size_bytes": file_size,
            "file_type": file_type,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "course_id": course_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error:
            log_data["error"] = error
        
        if status == UploadStatus.SUCCESS:
            logger.info(f"Upload successful", extra=log_data)
        else:
            logger.warning(f"Upload {status.value}", extra=log_data)
        
        # Cloud Monitoring (if enabled)
        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("upload_count", 1, {
                "status": status.value,
                "file_type": file_type,
                "course_id": course_id
            })
            
            self._write_cloud_metric("upload_size_bytes", file_size, {
                "file_type": file_type,
                "course_id": course_id
            })
            
            self._write_cloud_metric("upload_duration_ms", duration_ms, {
                "status": status.value,
                "course_id": course_id
            })
    
    def record_extraction(
        self,
        status: ExtractionStatus,
        material_id: str,
        course_id: str,
        text_length: int = 0,
        duration_ms: float = 0,
        error: Optional[str] = None
    ):
        """
        Record a text extraction operation.
        
        Args:
            status: Extraction status
            material_id: Material identifier
            course_id: Course identifier
            text_length: Length of extracted text
            duration_ms: Extraction duration in milliseconds
            error: Error message if failed
        """
        # Structured logging
        log_data = {
            "event": "extraction",
            "status": status.value,
            "material_id": material_id,
            "course_id": course_id,
            "text_length": text_length,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error:
            log_data["error"] = error
        
        if status == ExtractionStatus.SUCCESS:
            logger.info(f"Extraction successful", extra=log_data)
        else:
            logger.warning(f"Extraction {status.value}", extra=log_data)
        
        # Cloud Monitoring (if enabled)
        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("extraction_count", 1, {
                "status": status.value,
                "course_id": course_id
            })
            
            if text_length > 0:
                self._write_cloud_metric("extraction_text_length", text_length, {
                    "course_id": course_id
                })
            
            if duration_ms > 0:
                self._write_cloud_metric("extraction_duration_ms", duration_ms, {
                    "status": status.value,
                    "course_id": course_id
                })
    
    def record_rate_limit(self, user_id: str, client_ip: str):
        """Record a rate limit event."""
        log_data = {
            "event": "rate_limit",
            "user_id": user_id,
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.warning("Rate limit exceeded", extra=log_data)
        
        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("rate_limit_count", 1, {
                "user_id": user_id
            })
    
    def _write_cloud_metric(self, metric_name: str, value: float, labels: Dict[str, str]):
        """Write a metric to Cloud Monitoring."""
        if not self.cloud_monitoring_enabled:
            return
        
        try:
            from google.cloud import monitoring_v3
            from google.api import metric_pb2 as ga_metric
            
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/upload/{metric_name}"
            
            for key, val in labels.items():
                series.metric.labels[key] = str(val)
            
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10 ** 9)
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            point = monitoring_v3.Point(
                {"interval": interval, "value": {"double_value": value}}
            )
            series.points = [point]
            
            self.client.create_time_series(
                name=self.project_name,
                time_series=[series]
            )
            
        except Exception as e:
            logger.error(f"Failed to write Cloud Monitoring metric: {e}")


# Singleton instance
_metrics: Optional[UploadMetrics] = None


def get_upload_metrics() -> UploadMetrics:
    """Get the upload metrics singleton."""
    global _metrics
    if _metrics is None:
        _metrics = UploadMetrics()
    return _metrics

