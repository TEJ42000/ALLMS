"""Unified Course Materials Service.

Provides CRUD operations for the unified materials collection.
Replaces the fragmented uploadedMaterials + MaterialsRegistry approach.

Firestore structure: courses/{course_id}/materials/{material_id}
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.models.course_models import CourseMaterial
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Collection name for unified materials
MATERIALS_COLLECTION = "materials"

# Firestore batch limit
FIRESTORE_BATCH_LIMIT = 500


def generate_material_id(storage_path: str) -> str:
    """Generate a unique ID from the storage path.

    Uses SHA-256 hash of the path to ensure:
    - Same file always gets same ID (deduplication)
    - ID is URL-safe and consistent length
    - Cryptographically secure (unlike MD5)
    """
    return hashlib.sha256(storage_path.encode()).hexdigest()[:32]


class CourseMaterialsService:
    """Service for managing unified course materials."""

    def __init__(self):
        """Initialize the service."""
        self.db = get_firestore_client()

    def _get_collection(self, course_id: str):
        """Get the materials subcollection for a course."""
        return self.db.collection("courses").document(course_id).collection(MATERIALS_COLLECTION)

    def get_material(self, course_id: str, material_id: str) -> Optional[CourseMaterial]:
        """Get a single material by ID."""
        doc = self._get_collection(course_id).document(material_id).get()
        if doc.exists:
            return CourseMaterial(**doc.to_dict())
        return None

    def get_material_by_path(self, course_id: str, storage_path: str) -> Optional[CourseMaterial]:
        """Get a material by its storage path."""
        material_id = generate_material_id(storage_path)
        return self.get_material(course_id, material_id)

    def list_materials(
        self,
        course_id: str,
        tier: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        text_extracted: Optional[bool] = None,
        summary_generated: Optional[bool] = None,
        limit: int = 500
    ) -> List[CourseMaterial]:
        """List materials with optional filters."""
        query = self._get_collection(course_id)

        if tier:
            query = query.where("tier", "==", tier)
        if category:
            query = query.where("category", "==", category)
        if source:
            query = query.where("source", "==", source)
        if text_extracted is not None:
            query = query.where("textExtracted", "==", text_extracted)
        if summary_generated is not None:
            query = query.where("summaryGenerated", "==", summary_generated)

        query = query.limit(limit)
        
        materials = []
        for doc in query.stream():
            materials.append(CourseMaterial(**doc.to_dict()))
        
        return materials

    def upsert_material(self, course_id: str, material: CourseMaterial) -> CourseMaterial:
        """Create or update a material.
        
        Uses the material ID (hash of path) for deduplication.
        """
        material.updatedAt = datetime.now(timezone.utc)
        doc_ref = self._get_collection(course_id).document(material.id)
        doc_ref.set(material.model_dump(mode="json"))
        logger.info("Upserted material %s in course %s", material.id, course_id)
        return material

    def delete_material(self, course_id: str, material_id: str) -> bool:
        """Delete a material by ID."""
        doc_ref = self._get_collection(course_id).document(material_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False
        doc_ref.delete()
        logger.info("Deleted material %s from course %s", material_id, course_id)
        return True

    def update_text_extraction(
        self,
        course_id: str,
        material_id: str,
        extracted_text: str,
        text_length: int,
        error: Optional[str] = None
    ) -> Optional[CourseMaterial]:
        """Update text extraction results for a material."""
        doc_ref = self._get_collection(course_id).document(material_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        update_data = {
            "textExtracted": error is None,
            "extractedText": extracted_text if error is None else None,
            "textLength": text_length if error is None else 0,
            "extractionError": error,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        doc_ref.update(update_data)
        
        return self.get_material(course_id, material_id)

    def update_summary(
        self,
        course_id: str,
        material_id: str,
        summary: str,
        error: Optional[str] = None
    ) -> Optional[CourseMaterial]:
        """Update AI summary for a material."""
        doc_ref = self._get_collection(course_id).document(material_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        update_data = {
            "summary": summary if error is None else None,
            "summaryGenerated": error is None,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        doc_ref.update(update_data)

        return self.get_material(course_id, material_id)

    def update_storage_path(
        self,
        course_id: str,
        material_id: str,
        new_storage_path: str
    ) -> Optional[CourseMaterial]:
        """Update the storagePath for a material.

        This is used to fix incomplete storage paths that were saved incorrectly.

        Args:
            course_id: Course ID
            material_id: Material document ID
            new_storage_path: The corrected storage path

        Returns:
            Updated material or None if not found
        """
        doc_ref = self._get_collection(course_id).document(material_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        update_data = {
            "storagePath": new_storage_path,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        doc_ref.update(update_data)
        logger.info("Updated storagePath for material %s: %s", material_id, new_storage_path)

        return self.get_material(course_id, material_id)

    def get_materials_stats(self, course_id: str) -> Dict[str, Any]:
        """Get statistics about materials for a course."""
        materials = self.list_materials(course_id)

        stats = {
            "total": len(materials),
            "by_source": {"scanned": 0, "uploaded": 0},
            "by_tier": {},
            "by_category": {},
            "text_extracted": 0,
            "text_pending": 0,
            "summary_generated": 0,
            "summary_pending": 0,
        }

        for m in materials:
            stats["by_source"][m.source] = stats["by_source"].get(m.source, 0) + 1
            stats["by_tier"][m.tier] = stats["by_tier"].get(m.tier, 0) + 1
            if m.category:
                stats["by_category"][m.category] = stats["by_category"].get(m.category, 0) + 1
            if m.textExtracted:
                stats["text_extracted"] += 1
            else:
                stats["text_pending"] += 1
            if m.summaryGenerated:
                stats["summary_generated"] += 1
            elif m.textExtracted:  # Can only generate summary if text exists
                stats["summary_pending"] += 1

        return stats

    def bulk_upsert_materials(
        self,
        course_id: str,
        materials: List[CourseMaterial]
    ) -> int:
        """Bulk upsert multiple materials efficiently."""
        batch = self.db.batch()
        count = 0

        for material in materials:
            material.updatedAt = datetime.now(timezone.utc)
            doc_ref = self._get_collection(course_id).document(material.id)
            batch.set(doc_ref, material.model_dump(mode="json"))
            count += 1

            # Firestore batch limit
            if count % FIRESTORE_BATCH_LIMIT == 0:
                batch.commit()
                batch = self.db.batch()

        if count % FIRESTORE_BATCH_LIMIT != 0:
            batch.commit()

        logger.info("Bulk upserted %d materials in course %s", count, course_id)
        return count


# Singleton instance
_service_instance: Optional[CourseMaterialsService] = None


def get_course_materials_service() -> CourseMaterialsService:
    """Get or create the singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = CourseMaterialsService()
    return _service_instance

