#!/usr/bin/env python3
"""Migrate course_data.json files to Firestore.

This script reads existing course_data.json files and migrates them
to the Firestore database using the CourseService.

Usage:
    python scripts/migrate_course_data.py

Prerequisites:
    - ADC configured: gcloud auth application-default login
    - Firestore database created in GCP project
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.gcp_service import get_firestore_client, GCP_PROJECT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_lls_course():
    """Migrate LLS course data to Firestore."""
    # Path to course_data.json
    course_data_path = project_root / "Materials" / "Course_Materials" / "LLS" / "LLS Essential " / "course_data.json"

    if not course_data_path.exists():
        logger.error("course_data.json not found at: %s", course_data_path)
        return False

    # Load JSON data
    logger.info("Loading course data from: %s", course_data_path)
    with open(course_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get Firestore client
    db = get_firestore_client()
    if db is None:
        logger.error("Firestore not available. Run: gcloud auth application-default login")
        return False

    logger.info("Connected to Firestore project: %s", GCP_PROJECT_ID)

    # Extract course info
    course_info = data.get("course", {})
    course_id = course_info.get("id", "LLS-2025-2026")

    # Create main course document
    course_ref = db.collection("courses").document(course_id)

    course_doc = {
        **course_info,
        "materialSubjects": ["LLS"],  # Maps to file_ids.json subjects
        "abbreviations": data.get("abbreviations", {}),
        "externalResources": data.get("externalResources", {}),
        "materials": data.get("materials", {}),
        "active": True,
    }

    # Check if course already exists
    existing = course_ref.get()
    if existing.exists:
        logger.warning("Course %s already exists. Updating...", course_id)

    course_ref.set(course_doc)
    logger.info("✅ Created/updated course document: %s", course_id)

    # Migrate weeks to subcollection
    weeks = data.get("weeks", [])
    weeks_migrated = 0

    for week in weeks:
        week_number = week.get("weekNumber")
        if week_number is None:
            logger.warning("Skipping week without weekNumber")
            continue

        week_ref = course_ref.collection("weeks").document(f"week-{week_number}")
        week_ref.set(week)
        weeks_migrated += 1

    logger.info("✅ Migrated %d weeks", weeks_migrated)

    # Migrate legal skills to subcollection
    # Only migrate actual skill frameworks (those with 'name' and 'steps' fields)
    legal_skills = data.get("legalSkills", {})
    skills_migrated = 0

    for skill_id, skill_data in legal_skills.items():
        # Check if this is a skill framework (has 'name' and 'steps')
        # vs configuration data (like legalCitation, legalResearch)
        if isinstance(skill_data, dict) and "name" in skill_data and "steps" in skill_data:
            skill_ref = course_ref.collection("legalSkills").document(skill_id)
            skill_ref.set(skill_data)
            skills_migrated += 1
            logger.info("   - Migrated skill: %s", skill_id)
        else:
            # Store configuration data directly in course document
            logger.info("   - Skipped config data: %s (not a skill framework)", skill_id)

    logger.info("✅ Migrated %d legal skill frameworks", skills_migrated)

    # Summary
    print("\n" + "=" * 60)
    print("🎓 MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Course ID: {course_id}")
    print(f"Course Name: {course_info.get('name', 'Unknown')}")
    print(f"Academic Year: {course_info.get('academicYear', 'Unknown')}")
    print(f"Weeks migrated: {weeks_migrated}")
    print(f"Legal skills migrated: {skills_migrated}")
    print(f"Abbreviations: {len(data.get('abbreviations', {}))}")
    print("=" * 60)

    return True


def verify_migration():
    """Verify the migration was successful."""
    db = get_firestore_client()
    if db is None:
        return False

    # Check courses collection
    courses = list(db.collection("courses").stream())
    print(f"\n📋 Found {len(courses)} course(s) in Firestore:")

    for course_doc in courses:
        data = course_doc.to_dict()
        weeks = list(course_doc.reference.collection("weeks").stream())
        skills = list(course_doc.reference.collection("legalSkills").stream())

        print(f"\n  📚 {course_doc.id}")
        print(f"     Name: {data.get('name', 'N/A')}")
        print(f"     Program: {data.get('program', 'N/A')}")
        print(f"     Academic Year: {data.get('academicYear', 'N/A')}")
        print(f"     Weeks: {len(weeks)}")
        print(f"     Legal Skills: {len(skills)}")
        print(f"     Active: {data.get('active', False)}")

    return True


def main():
    """Main entry point."""
    print("🚀 Course Data Migration Tool")
    print("=" * 60)

    # Run migration
    success = migrate_lls_course()

    if success:
        # Verify
        verify_migration()
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

