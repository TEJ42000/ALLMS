#!/usr/bin/env python3
"""Migration script to backfill weekCount on existing course documents.

This script iterates through all courses and sets the weekCount field
based on the actual number of documents in the weeks subcollection.

Usage:
    # Dry run (no changes):
    python scripts/migrate_week_count.py --dry-run

    # Apply changes:
    python scripts/migrate_week_count.py

    # With batch size:
    python scripts/migrate_week_count.py --batch-size 50
"""

import argparse
import logging
import sys
from typing import Optional

# Add project root to path
sys.path.insert(0, ".")

from google.cloud import firestore
from app.services.gcp_service import get_firestore_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

COURSES_COLLECTION = "courses"
WEEKS_SUBCOLLECTION = "weeks"


def migrate_week_counts(
    dry_run: bool = True,
    batch_size: int = 100,
) -> dict:
    """
    Backfill weekCount field on all course documents.

    Args:
        dry_run: If True, only log what would be changed without making updates
        batch_size: Number of courses to process in each batch

    Returns:
        Dictionary with migration statistics
    """
    db = get_firestore_client()
    if not db:
        raise RuntimeError("Firestore client not available")

    stats = {
        "total_courses": 0,
        "updated": 0,
        "already_correct": 0,
        "errors": 0,
    }

    logger.info("Starting weekCount migration (dry_run=%s)", dry_run)

    # Get all courses
    courses_ref = db.collection(COURSES_COLLECTION)
    courses = list(courses_ref.stream())
    stats["total_courses"] = len(courses)

    logger.info("Found %d courses to process", stats["total_courses"])

    batch: Optional[firestore.WriteBatch] = None
    batch_count = 0

    for course_doc in courses:
        try:
            course_data = course_doc.to_dict()
            course_id = course_doc.id

            # Count actual weeks in subcollection
            weeks_ref = course_doc.reference.collection(WEEKS_SUBCOLLECTION)
            actual_week_count = len(list(weeks_ref.select([]).stream()))

            # Get current weekCount (default to None if not set)
            current_week_count = course_data.get("weekCount")

            if current_week_count == actual_week_count:
                logger.debug("Course %s: weekCount already correct (%d)", course_id, actual_week_count)
                stats["already_correct"] += 1
                continue

            logger.info(
                "Course %s: weekCount %s -> %d",
                course_id,
                current_week_count,
                actual_week_count
            )

            if not dry_run:
                if batch is None:
                    batch = db.batch()
                    batch_count = 0

                batch.update(course_doc.reference, {"weekCount": actual_week_count})
                batch_count += 1

                # Commit batch if we've reached batch_size
                if batch_count >= batch_size:
                    batch.commit()
                    logger.info("Committed batch of %d updates", batch_count)
                    batch = None
                    batch_count = 0

            stats["updated"] += 1

        except Exception as e:
            logger.error("Error processing course %s: %s", course_doc.id, e)
            stats["errors"] += 1

    # Commit any remaining updates
    if batch is not None and batch_count > 0:
        batch.commit()
        logger.info("Committed final batch of %d updates", batch_count)

    logger.info("Migration complete: %s", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill weekCount field on course documents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log changes without applying them"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of courses to update per batch (default: 100)"
    )

    args = parser.parse_args()

    try:
        stats = migrate_week_counts(dry_run=args.dry_run, batch_size=args.batch_size)
        if stats["errors"] > 0:
            sys.exit(1)
    except Exception as e:
        logger.error("Migration failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

