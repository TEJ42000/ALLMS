"""Background Task Processing Service.

Provides abstraction for background task execution with support for:
- Synchronous execution (development/testing)
- Google Cloud Tasks (production)

Environment Variables:
    BACKGROUND_PROCESSING: 'sync' or 'cloud_tasks' (default: 'sync')
    GCP_PROJECT_ID: Google Cloud project ID (required if BACKGROUND_PROCESSING=cloud_tasks)
    GCP_REGION: Google Cloud region (default: 'europe-west4')
    CLOUD_TASKS_QUEUE: Cloud Tasks queue name (default: 'upload-processing')
    SERVICE_URL: Base URL of the service for task callbacks (required for cloud_tasks)
"""

import logging
import os
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BackgroundTaskProcessor:
    """Base class for background task processing."""
    
    def enqueue_task(self, task_name: str, payload: Dict[str, Any], handler_url: str) -> str:
        """
        Enqueue a background task.
        
        Args:
            task_name: Unique name for the task
            payload: Task payload (must be JSON-serializable)
            handler_url: URL endpoint to handle the task
            
        Returns:
            Task ID or identifier
        """
        raise NotImplementedError


class SyncTaskProcessor(BackgroundTaskProcessor):
    """Synchronous task processor for development/testing.
    
    Executes tasks immediately in the same process.
    """
    
    def __init__(self):
        logger.warning("Using synchronous task processor - tasks will block requests!")
    
    def enqueue_task(self, task_name: str, payload: Dict[str, Any], handler_url: str) -> str:
        """Execute task synchronously (blocking)."""
        logger.info(f"Executing task synchronously: {task_name}")
        
        # In sync mode, we can't actually call the handler URL
        # The caller should handle the task directly
        task_id = f"sync_{task_name}_{datetime.now(timezone.utc).timestamp()}"
        
        logger.info(f"Task {task_id} will be executed synchronously by caller")
        return task_id


class CloudTasksProcessor(BackgroundTaskProcessor):
    """Google Cloud Tasks processor for production.
    
    Enqueues tasks to Cloud Tasks for async execution.
    """
    
    def __init__(self):
        try:
            from google.cloud import tasks_v2
            
            self.project_id = os.getenv("GCP_PROJECT_ID")
            if not self.project_id:
                raise ValueError("GCP_PROJECT_ID environment variable not set")
            
            self.region = os.getenv("GCP_REGION", "europe-west4")
            self.queue_name = os.getenv("CLOUD_TASKS_QUEUE", "upload-processing")
            self.service_url = os.getenv("SERVICE_URL")
            
            if not self.service_url:
                raise ValueError("SERVICE_URL environment variable not set (required for Cloud Tasks)")
            
            self.client = tasks_v2.CloudTasksClient()
            self.queue_path = self.client.queue_path(
                self.project_id,
                self.region,
                self.queue_name
            )
            
            logger.info(f"Using Cloud Tasks processor: {self.queue_path}")
            
        except ImportError:
            logger.error("google-cloud-tasks package not installed. Install with: pip install google-cloud-tasks")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Tasks: {e}")
            raise
    
    def enqueue_task(self, task_name: str, payload: Dict[str, Any], handler_url: str) -> str:
        """Enqueue task to Cloud Tasks."""
        from google.cloud import tasks_v2
        
        # Construct full URL
        full_url = f"{self.service_url.rstrip('/')}/{handler_url.lstrip('/')}"
        
        # Create task
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=full_url,
                headers={
                    "Content-Type": "application/json",
                },
                body=json.dumps(payload).encode()
            )
        )
        
        # Enqueue task
        response = self.client.create_task(
            request={
                "parent": self.queue_path,
                "task": task
            }
        )
        
        task_id = response.name.split("/")[-1]
        logger.info(f"Enqueued task {task_id} to Cloud Tasks: {full_url}")
        
        return task_id


# Singleton instance
_task_processor: Optional[BackgroundTaskProcessor] = None


def get_task_processor() -> BackgroundTaskProcessor:
    """Get the configured task processor (singleton)."""
    global _task_processor
    
    if _task_processor is not None:
        return _task_processor
    
    backend = os.getenv("BACKGROUND_PROCESSING", "sync").lower()
    
    if backend == "cloud_tasks":
        try:
            _task_processor = CloudTasksProcessor()
            logger.info("Using Cloud Tasks for background processing (production mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Tasks: {e}")
            logger.warning("Falling back to synchronous processing")
            _task_processor = SyncTaskProcessor()
    else:
        _task_processor = SyncTaskProcessor()
        logger.info("Using synchronous processing (development mode)")
    
    return _task_processor


def enqueue_text_extraction(course_id: str, material_id: str) -> str:
    """
    Enqueue a text extraction task.
    
    Args:
        course_id: Course identifier
        material_id: Material identifier
        
    Returns:
        Task ID
    """
    processor = get_task_processor()
    
    payload = {
        "course_id": course_id,
        "material_id": material_id,
        "task_type": "text_extraction"
    }
    
    task_id = processor.enqueue_task(
        task_name=f"extract_{material_id}",
        payload=payload,
        handler_url="api/upload/process-extraction"
    )
    
    return task_id


def is_background_processing_enabled() -> bool:
    """Check if background processing is enabled."""
    backend = os.getenv("BACKGROUND_PROCESSING", "sync").lower()
    return backend == "cloud_tasks"

