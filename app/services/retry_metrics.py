"""Retry Metrics and Monitoring Service.

Issue #220: Add retry metrics for observability.

Provides structured logging and metrics for retry operations.
Integrates with Google Cloud Monitoring in production.

Metrics tracked:
- retry_attempts: Count of retry attempts by operation and error type
- retry_success: Count of successful retries (recovered from failure)
- retry_failure: Count of failures after max retries exhausted
- retry_duration: Total time spent in retry logic

Environment Variables:
    ENABLE_CLOUD_MONITORING: 'true' or 'false' (default: 'false')
    GCP_PROJECT_ID: Google Cloud project ID (required if ENABLE_CLOUD_MONITORING=true)
"""

import logging
import os
import time
from typing import Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RetryStats:
    """Statistics for a single retry operation."""
    operation: str
    start_time: float = field(default_factory=time.time)
    attempts: int = 0
    success: bool = False
    error_types: list = field(default_factory=list)
    total_delay: float = 0.0

    @property
    def duration_seconds(self) -> float:
        """Total duration of the retry operation."""
        return time.time() - self.start_time


class RetryMetrics:
    """Metrics collector for retry operations.
    
    Issue #220: Follows same pattern as UploadMetrics for consistency.
    """
    
    def __init__(self):
        self.cloud_monitoring_enabled = os.getenv(
            "ENABLE_CLOUD_MONITORING", "false"
        ).lower() == "true"
        
        if self.cloud_monitoring_enabled:
            try:
                from google.cloud import monitoring_v3
                
                project_id = os.getenv("GCP_PROJECT_ID")
                if not project_id:
                    raise ValueError("GCP_PROJECT_ID not set")
                
                self.client = monitoring_v3.MetricServiceClient()
                self.project_name = f"projects/{project_id}"
                logger.info("Cloud Monitoring enabled for retry metrics")
                
            except ImportError:
                logger.warning(
                    "google-cloud-monitoring not installed, using logging only"
                )
                self.cloud_monitoring_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Cloud Monitoring: {e}")
                self.cloud_monitoring_enabled = False
    
    def record_retry_attempt(
        self,
        operation: str,
        attempt: int,
        error_type: str,
        delay: float = 0.0
    ):
        """
        Record a single retry attempt.
        
        Args:
            operation: Name of the function being retried
            attempt: Attempt number (1-based)
            error_type: Type of exception that triggered retry
            delay: Delay before this retry in seconds
        """
        log_data = {
            "event": "retry_attempt",
            "operation": operation,
            "attempt": attempt,
            "error_type": error_type,
            "delay_seconds": delay,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Retry attempt", extra=log_data)
        
        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("retry_attempt_count", 1, {
                "operation": operation,
                "attempt": str(attempt),
                "error_type": error_type
            })
    
    def record_retry_success(
        self,
        operation: str,
        total_attempts: int,
        total_duration: float,
        total_delay: float = 0.0
    ):
        """
        Record a successful retry (operation succeeded after retries).
        
        Args:
            operation: Name of the function that succeeded
            total_attempts: Total number of attempts (including successful one)
            total_duration: Total time spent from first attempt to success
            total_delay: Total delay time spent waiting between retries
        """
        log_data = {
            "event": "retry_success",
            "operation": operation,
            "total_attempts": total_attempts,
            "duration_seconds": total_duration,
            "delay_seconds": total_delay,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Retry succeeded", extra=log_data)
        
        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("retry_success_count", 1, {
                "operation": operation,
                "attempts": str(total_attempts)
            })
            self._write_cloud_metric("retry_duration_seconds", total_duration, {
                "operation": operation,
                "outcome": "success"
            })

    def record_retry_failure(
        self,
        operation: str,
        max_retries: int,
        error_type: str,
        total_duration: float = 0.0,
        total_delay: float = 0.0
    ):
        """
        Record a retry failure (max retries exhausted).

        Args:
            operation: Name of the function that failed
            max_retries: Maximum retries that were attempted
            error_type: Type of the final exception
            total_duration: Total time spent from first attempt to final failure
            total_delay: Total delay time spent waiting between retries
        """
        log_data = {
            "event": "retry_failure",
            "operation": operation,
            "max_retries": max_retries,
            "error_type": error_type,
            "duration_seconds": total_duration,
            "delay_seconds": total_delay,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.warning("Retry failed - max retries exhausted", extra=log_data)

        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("retry_failure_count", 1, {
                "operation": operation,
                "error_type": error_type
            })
            self._write_cloud_metric("retry_duration_seconds", total_duration, {
                "operation": operation,
                "outcome": "failure"
            })

    def record_non_retryable(self, operation: str, error_type: str):
        """
        Record when a non-retryable exception is encountered.

        Args:
            operation: Name of the function that failed
            error_type: Type of the non-retryable exception
        """
        log_data = {
            "event": "retry_non_retryable",
            "operation": operation,
            "error_type": error_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info("Non-retryable exception", extra=log_data)

        if self.cloud_monitoring_enabled:
            self._write_cloud_metric("retry_non_retryable_count", 1, {
                "operation": operation,
                "error_type": error_type
            })

    def _write_cloud_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str]
    ):
        """Write a metric to Cloud Monitoring."""
        if not self.cloud_monitoring_enabled:
            return

        try:
            from google.cloud import monitoring_v3

            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/retry/{metric_name}"

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
_metrics: Optional[RetryMetrics] = None


def get_retry_metrics() -> RetryMetrics:
    """Get the retry metrics singleton."""
    global _metrics
    if _metrics is None:
        _metrics = RetryMetrics()
    return _metrics

