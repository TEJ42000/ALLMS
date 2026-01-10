#!/usr/bin/env python3
"""
Populate Firestore with course materials from local Materials directory.

This script scans the Materials directory and creates Firestore documents
in the courses/{course_id}/materials collection so materials appear in the UI.

Usage:
    python scripts/populate_firestore_materials.py [--dry-run]
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import Firestore directly to avoid Anthropic client initialization
from google.cloud import firestore

def get_firestore_client():
    """Get Firestore client without initializing Anthropic."""
    return firestore.Client()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Course ID mapping (directory name -> Firestore course ID)
COURSE_MAPPING = {
    "Criminal_Law": "CRIM-2025-2026",  # Fixed: was "Criminal-Law---Part--2025-2026"
    "LLS": "LLS-2025-2026",
    "LH": "Legal-History-2025-2026",
}

# Tier mapping
TIER_MAPPING = {
    "Syllabus": "syllabus",
    "Course_Materials": "course_materials",
    "Supplementary_Sources": "supplementary"
}


def get_week_number_from_path(file_path: Path) -> int:
    """Extract week number from file path or filename."""
    path_str = str(file_path).lower()
    
    # Check for "week_X" or "week X" patterns
    import re
    week_match = re.search(r'week[_\s](\d+)', path_str)
    if week_match:
        return int(week_match.group(1))
    
    # Default to week 1 if no week found
    return 1


def discover_materials(materials_dir: Path = Path("Materials")):
    """Discover all materials from the Materials directory."""
    if not materials_dir.exists():
        logger.error(f"Materials directory not found: {materials_dir}")
        return []
    
    materials = []
    supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.html'}
    
    # Scan each tier
    for tier_dir in materials_dir.iterdir():
        if not tier_dir.is_dir():
            continue
        
        tier_name = tier_dir.name
        if tier_name not in TIER_MAPPING:
            logger.debug(f"Skipping non-tier directory: {tier_name}")
            continue
        
        tier = TIER_MAPPING[tier_name]
        
        # Scan for course directories
        for course_dir in tier_dir.iterdir():
            if not course_dir.is_dir():
                continue
            
            course_name = course_dir.name
            course_id = COURSE_MAPPING.get(course_name)
            
            if not course_id:
                logger.warning(f"No course mapping for: {course_name}")
                continue
            
            # Find all files recursively
            for ext in supported_extensions:
                for file_path in course_dir.rglob(f"*{ext}"):
                    # Skip hidden files and system files
                    if file_path.name.startswith('.') or file_path.name.startswith('~'):
                        continue
                    
                    # Get relative path from course directory
                    rel_path = file_path.relative_to(materials_dir)
                    storage_path = str(rel_path)
                    
                    # Extract week number
                    week_number = get_week_number_from_path(file_path)
                    
                    # Determine category from subdirectory
                    parts = list(file_path.relative_to(course_dir).parts)
                    category = parts[0] if len(parts) > 1 else "General"
                    
                    material = {
                        "id": str(uuid.uuid4()),
                        "filename": file_path.name,
                        "title": file_path.stem,
                        "storagePath": storage_path,
                        "weekNumber": week_number,
                        "tier": tier,
                        "category": category,
                        "source": "local",
                        "uploadedAt": datetime.utcnow(),
                        "textExtracted": False,
                        "summaryGenerated": False,
                        "course_id": course_id
                    }
                    
                    materials.append(material)
    
    return materials


def populate_firestore(materials, dry_run=False):
    """Populate Firestore with materials."""
    if dry_run:
        logger.info("DRY RUN - No changes will be made to Firestore")
    
    db = get_firestore_client()
    
    # Group materials by course
    by_course = {}
    for material in materials:
        course_id = material.pop("course_id")
        if course_id not in by_course:
            by_course[course_id] = []
        by_course[course_id].append(material)
    
    # Upload to Firestore
    total_uploaded = 0
    
    for course_id, course_materials in by_course.items():
        logger.info(f"\nCourse: {course_id}")
        logger.info(f"  Materials: {len(course_materials)}")
        
        if dry_run:
            # Just show what would be uploaded
            for mat in course_materials[:5]:  # Show first 5
                logger.info(f"    - {mat['filename']} (Week {mat['weekNumber']}, {mat['tier']})")
            if len(course_materials) > 5:
                logger.info(f"    ... and {len(course_materials) - 5} more")
            continue
        
        # Upload to Firestore
        batch = db.batch()
        batch_count = 0
        
        for material in course_materials:
            doc_ref = (
                db.collection("courses")
                .document(course_id)
                .collection("materials")
                .document(material["id"])
            )
            
            batch.set(doc_ref, material)
            batch_count += 1
            
            # Commit batch every 500 documents (Firestore limit)
            if batch_count >= 500:
                batch.commit()
                logger.info(f"  Committed batch of {batch_count} materials")
                batch = db.batch()
                batch_count = 0
        
        # Commit remaining
        if batch_count > 0:
            batch.commit()
            logger.info(f"  Committed final batch of {batch_count} materials")
        
        total_uploaded += len(course_materials)
    
    logger.info(f"\n✅ Total materials uploaded: {total_uploaded}")
    return total_uploaded


def main():
    parser = argparse.ArgumentParser(description="Populate Firestore with course materials")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Populate Firestore Materials")
    logger.info("=" * 60)
    
    # Discover materials
    logger.info("\n🔍 Discovering materials...")
    materials = discover_materials()
    
    if not materials:
        logger.error("No materials found!")
        return 1
    
    logger.info(f"Found {len(materials)} materials")
    
    # Group by course for summary
    by_course = {}
    for mat in materials:
        course_id = mat["course_id"]
        by_course[course_id] = by_course.get(course_id, 0) + 1
    
    logger.info("\nMaterials by course:")
    for course_id, count in by_course.items():
        logger.info(f"  {course_id}: {count} materials")
    
    # Populate Firestore
    logger.info("\n📤 Uploading to Firestore...")
    populate_firestore(materials, dry_run=args.dry_run)
    
    if args.dry_run:
        logger.info("\n✅ Dry run complete - no changes made")
    else:
        logger.info("\n✅ Upload complete!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

