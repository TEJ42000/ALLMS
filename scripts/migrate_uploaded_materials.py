#!/usr/bin/env python3
"""
Migration script to copy existing uploadedMaterials to the unified materials collection.

This script:
1. Iterates through all courses
2. Fetches uploadedMaterials from the legacy subcollection
3. Converts them to CourseMaterial format
4. Upserts them to the unified materials collection

Usage:
    python scripts/migrate_uploaded_materials.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gcp_service import get_firestore_client
from app.services.course_materials_service import (
    CourseMaterialsService,
    generate_material_id
)
from app.models.course_models import CourseMaterial


def migrate_uploaded_materials(dry_run: bool = False):
    """Migrate all uploadedMaterials to the unified collection."""
    db = get_firestore_client()
    service = CourseMaterialsService()
    
    # Get all courses
    courses_ref = db.collection("courses")
    courses = list(courses_ref.stream())
    
    print(f"Found {len(courses)} courses to check")
    
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    
    for course_doc in courses:
        course_id = course_doc.id
        course_data = course_doc.to_dict()
        course_name = course_data.get("name", "Unknown")
        
        # Get uploadedMaterials subcollection
        uploaded_ref = db.collection("courses").document(course_id).collection("uploadedMaterials")
        uploaded_docs = list(uploaded_ref.stream())
        
        if not uploaded_docs:
            continue
            
        print(f"\n📚 Course: {course_name} ({course_id})")
        print(f"   Found {len(uploaded_docs)} uploaded materials")
        
        for um_doc in uploaded_docs:
            um_data = um_doc.to_dict()
            
            try:
                # Convert to CourseMaterial
                storage_path = um_data.get("storagePath", "")
                if storage_path.startswith("Materials/"):
                    storage_path = storage_path[len("Materials/"):]
                
                material_id = generate_material_id(storage_path)
                
                # Check if already exists in unified collection
                existing = service.get_material(course_id, material_id)
                if existing:
                    print(f"   ⏭️  Skipped (exists): {um_data.get('filename')}")
                    total_skipped += 1
                    continue
                
                # Create CourseMaterial
                material = CourseMaterial(
                    id=material_id,
                    filename=um_data.get("filename", ""),
                    storagePath=storage_path,
                    fileSize=um_data.get("fileSize", 0),
                    fileType=um_data.get("fileType", "unknown"),
                    mimeType=um_data.get("mimeType"),
                    tier=um_data.get("tier", "course_materials"),
                    category=um_data.get("category"),
                    title=um_data.get("title") or um_data.get("filename", ""),
                    description=um_data.get("description"),
                    weekNumber=um_data.get("weekNumber"),
                    source="uploaded",
                    uploadedBy=um_data.get("uploadedBy"),
                    textExtracted=um_data.get("textExtracted", False),
                    extractedText=um_data.get("extractedText"),
                    textLength=len(um_data.get("extractedText", "") or ""),
                    summary=um_data.get("summary"),
                    summaryGenerated=um_data.get("summaryGenerated", False),
                    createdAt=um_data.get("uploadedAt", datetime.now(timezone.utc)),
                    updatedAt=datetime.now(timezone.utc)
                )
                
                if dry_run:
                    print(f"   🔍 Would migrate: {material.filename}")
                else:
                    service.upsert_material(course_id, material)
                    print(f"   ✅ Migrated: {material.filename}")
                
                total_migrated += 1
                
            except Exception as e:
                print(f"   ❌ Error migrating {um_data.get('filename')}: {e}")
                total_errors += 1
    
    print(f"\n{'=' * 50}")
    print(f"Migration {'(DRY RUN) ' if dry_run else ''}Complete!")
    print(f"  Migrated: {total_migrated}")
    print(f"  Skipped:  {total_skipped}")
    print(f"  Errors:   {total_errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate uploadedMaterials to unified collection")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    args = parser.parse_args()
    
    migrate_uploaded_materials(dry_run=args.dry_run)

