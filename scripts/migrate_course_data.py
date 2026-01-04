#!/usr/bin/env python3
"""Migrate course_data.json files to Firestore.

This script reads existing course_data.json files and migrates them
to the Firestore database using batch writes for atomicity.

Usage:
    python scripts/migrate_course_data.py [--dry-run]

Options:
    --dry-run    Preview changes without actually writing to Firestore

Prerequisites:
    - ADC configured: gcloud auth application-default login
    - Firestore database created in GCP project
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.api_core import exceptions as google_exceptions
from app.services.gcp_service import get_firestore_client, GCP_PROJECT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
RETRY_MULTIPLIER = 2.0

# Firestore batch limit
FIRESTORE_BATCH_LIMIT = 500


def retry_on_transient_error(func):
    """Decorator that retries a function on transient Firestore errors."""
    def wrapper(*args, **kwargs):
        last_exception: Optional[Exception] = None
        delay = INITIAL_RETRY_DELAY

        for attempt in range(MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except google_exceptions.GoogleAPIError as e:
                last_exception = e

                # Check if retryable
                is_retryable = isinstance(e, (
                    google_exceptions.ServiceUnavailable,
                    google_exceptions.DeadlineExceeded,
                    google_exceptions.ResourceExhausted,
                    google_exceptions.Aborted,
                ))

                if not is_retryable or attempt >= MAX_RETRIES:
                    raise

                logger.warning(
                    "Transient error (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1, MAX_RETRIES + 1, str(e), delay
                )
                time.sleep(delay)
                delay *= RETRY_MULTIPLIER

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")

    return wrapper


@retry_on_transient_error
def migrate_lls_course(dry_run: bool = False):
    """Migrate LLS course data to Firestore using batch writes.

    Args:
        dry_run: If True, only preview changes without writing to Firestore
    """
    # Path to course_data.json
    course_data_path = project_root / "Materials" / "Course_Materials" / "LLS" / "LLS Essential " / "course_data.json"

    if not course_data_path.exists():
        logger.error("course_data.json not found at: %s", course_data_path)
        return False

    # Load JSON data
    logger.info("Loading course data from: %s", course_data_path)
    try:
        with open(course_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in course_data.json: %s", str(e))
        return False
    except IOError as e:
        logger.error("Error reading course_data.json: %s", str(e))
        return False

    # Get Firestore client
    db = get_firestore_client()
    if db is None:
        logger.error("Firestore not available. Run: gcloud auth application-default login")
        return False

    logger.info("Connected to Firestore project: %s", GCP_PROJECT_ID)

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be written to Firestore")

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
    try:
        existing = course_ref.get()
        if existing.exists:
            logger.warning("Course %s already exists. Updating...", course_id)
    except google_exceptions.GoogleAPIError as e:
        logger.error("Firestore error checking existing course: %s", str(e))
        raise

    # Collect weeks and skills for batch write
    weeks = data.get("weeks", [])
    legal_skills = data.get("legalSkills", {})

    # Filter valid weeks
    valid_weeks = []
    for week in weeks:
        week_number = week.get("weekNumber")
        if week_number is None:
            logger.warning("Skipping week without weekNumber")
            continue
        valid_weeks.append((week_number, week))

    # Filter valid skills (those with 'name' and 'steps')
    valid_skills = []
    for skill_id, skill_data in legal_skills.items():
        if isinstance(skill_data, dict) and "name" in skill_data and "steps" in skill_data:
            valid_skills.append((skill_id, skill_data))
        else:
            logger.info("   - Skipped config data: %s (not a skill framework)", skill_id)

    # Calculate total operations
    total_ops = 1 + len(valid_weeks) + len(valid_skills)  # course + weeks + skills

    if dry_run:
        # Preview changes
        print("\n" + "=" * 60)
        print("🔍 DRY RUN - PREVIEW OF CHANGES")
        print("=" * 60)
        print(f"Course ID: {course_id}")
        print(f"Course Name: {course_info.get('name', 'Unknown')}")
        print(f"Academic Year: {course_info.get('academicYear', 'Unknown')}")
        print(f"Weeks to migrate: {len(valid_weeks)}")
        print(f"Legal skills to migrate: {len(valid_skills)}")
        print(f"Abbreviations: {len(data.get('abbreviations', {}))}")
        print(f"Total Firestore operations: {total_ops}")
        print("=" * 60)
        print("\n✅ Dry run complete. No changes were made.")
        return True

    # Use batch writes for atomicity (max 500 operations per batch)
    try:
        batch = db.batch()
        ops_in_batch = 0
        batches_committed = 0

        # Add course document
        batch.set(course_ref, course_doc)
        ops_in_batch += 1

        # Add weeks
        for week_number, week in valid_weeks:
            if ops_in_batch >= FIRESTORE_BATCH_LIMIT:
                batch.commit()
                batches_committed += 1
                batch = db.batch()
                ops_in_batch = 0

            week_ref = course_ref.collection("weeks").document(f"week-{week_number}")
            batch.set(week_ref, week)
            ops_in_batch += 1

        # Add skills
        for skill_id, skill_data in valid_skills:
            if ops_in_batch >= FIRESTORE_BATCH_LIMIT:
                batch.commit()
                batches_committed += 1
                batch = db.batch()
                ops_in_batch = 0

            skill_ref = course_ref.collection("legalSkills").document(skill_id)
            batch.set(skill_ref, skill_data)
            ops_in_batch += 1
            logger.info("   - Prepared skill: %s", skill_id)

        # Commit final batch
        if ops_in_batch > 0:
            batch.commit()
            batches_committed += 1

        logger.info("✅ Committed %d batch(es) with %d total operations", batches_committed, total_ops)

    except google_exceptions.GoogleAPIError as e:
        logger.error("Firestore error during batch write: %s", str(e))
        raise

    # Summary
    print("\n" + "=" * 60)
    print("🎓 MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Course ID: {course_id}")
    print(f"Course Name: {course_info.get('name', 'Unknown')}")
    print(f"Academic Year: {course_info.get('academicYear', 'Unknown')}")
    print(f"Weeks migrated: {len(valid_weeks)}")
    print(f"Legal skills migrated: {len(valid_skills)}")
    print(f"Abbreviations: {len(data.get('abbreviations', {}))}")
    print(f"Batches committed: {batches_committed}")
    print("=" * 60)

    return True


@retry_on_transient_error
def verify_migration():
    """Verify the migration was successful."""
    db = get_firestore_client()
    if db is None:
        return False

    try:
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

    except google_exceptions.GoogleAPIError as e:
        logger.error("Firestore error during verification: %s", str(e))
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate course_data.json files to Firestore"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to Firestore"
    )
    args = parser.parse_args()

    print("🚀 Course Data Migration Tool")
    print("=" * 60)

    # Run migration
    try:
        success = migrate_lls_course(dry_run=args.dry_run)

        if success:
            # Verify (skip if dry run)
            if not args.dry_run:
                verify_migration()
            print("\n✅ Migration completed successfully!")
        else:
            print("\n❌ Migration failed. Check logs above.")
            sys.exit(1)

    except google_exceptions.GoogleAPIError as e:
        logger.error("Migration failed with Firestore error: %s", str(e))
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Migration failed with unexpected error")
        print(f"\n❌ Migration failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

