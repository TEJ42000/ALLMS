#!/usr/bin/env python3
"""
Upload Course Materials to Anthropic Files API.

Run this once to upload all your course PDFs to Anthropic.

This script automatically discovers files from the three-tier Materials structure:
- Tier 1: Syllabus/ - Official course syllabi
- Tier 2: Course_Materials/ - Primary learning materials
- Tier 3: Supplementary_Sources/ - External and supplementary materials
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict

from anthropic import Anthropic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.md', '.txt'}

# Files to exclude from upload (documentation files, not course materials)
EXCLUDED_FILENAMES = {'README.md', 'FILE_INDEX.md', 'PACKAGE_CONTENTS.md'}

# Tier priorities for AI system (1 = highest authority)
TIER_PRIORITIES = {
    "Syllabus": 1,
    "Course_Materials": 2,
    "Supplementary_Sources": 3
}


def discover_materials(materials_dir: str = "./Materials") -> Dict[str, Dict]:
    """
    Discover all course materials from the three-tier directory structure.

    Returns:
        Dictionary mapping file keys to file metadata including path, tier, and subject
    """
    materials_path = Path(materials_dir)

    if not materials_path.exists():
        print(f"❌ Error: Materials directory not found: {materials_dir}")
        return {}

    discovered_files = {}

    # Traverse the three-tier structure
    for tier_dir in materials_path.iterdir():
        if not tier_dir.is_dir():
            continue

        tier_name = tier_dir.name

        # Case-insensitive tier name handling with validation
        tier_name_normalized = tier_name.title()
        if tier_name_normalized in TIER_PRIORITIES:
            if tier_name != tier_name_normalized:
                logger.warning("Directory '%s' should be '%s' (case matters)", tier_name, tier_name_normalized)
            # Use the normalized name for consistency
            tier_name = tier_name_normalized
        else:
            logger.debug("Skipping non-tier directory: %s", tier_name)
            continue

        # Recursively find all supported files in this tier
        # Use specific glob patterns for each extension for better performance
        for ext in SUPPORTED_EXTENSIONS:
            for file_path in tier_dir.rglob("*%s" % ext):
                # Skip excluded files (documentation, not course materials)
                if file_path.name in EXCLUDED_FILENAMES:
                    logger.debug("Skipping excluded file: %s", file_path.name)
                    continue

                # Generate a unique key for this file
                # Format: tier_subject_category_filename
                relative_path = file_path.relative_to(tier_dir)
                parts = list(relative_path.parts)

                # Create a readable key
                key_parts = [tier_name.lower()]
                if len(parts) > 1:
                    # Add subject and category
                    key_parts.extend([p.lower().replace(" ", "_").replace("-", "_")
                                     for p in parts[:-1]])

                # Add filename without extension
                filename_base = file_path.stem.lower().replace(" ", "_").replace("-", "_")
                key_parts.append(filename_base)

                key = "_".join(key_parts)

                # Check for duplicate keys
                if key in discovered_files:
                    logger.warning("Duplicate key '%s' for file '%s'", key, file_path)
                    # Add hash suffix to make key unique
                    key = "%s_%s" % (key, hash(str(file_path)) % 100000000)
                    logger.info("Using unique key: '%s'", key)

                # Store file metadata
                discovered_files[key] = {
                    "path": str(file_path),
                    "filename": file_path.name,
                    "tier": tier_name,
                    "tier_priority": TIER_PRIORITIES[tier_name],
                    "subject": parts[0] if len(parts) > 1 else "General",
                    "category": parts[1] if len(parts) > 2 else "General",
                    "size_bytes": file_path.stat().st_size
                }

    return discovered_files


def upload_course_files(materials_directory: str = "./Materials"):
    """
    Upload all course files to Anthropic Files API from the three-tier structure.

    Args:
        materials_directory: Root Materials directory with three-tier structure

    Returns:
        Dictionary of file_ids with metadata
    """
    # Initialize client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return {}

    client = Anthropic(api_key=api_key)

    print("=" * 60)
    print("📚 LLS Course Materials Upload - Three-Tier Structure")
    print("=" * 60)
    print()

    # Discover files from three-tier structure
    print("🔍 Discovering materials from three-tier structure...")
    discovered_files = discover_materials(materials_directory)

    if not discovered_files:
        print("❌ No files found in Materials directory!")
        return {}

    print("   Found %d files across all tiers" % len(discovered_files))

    # Group by tier for display
    tier_counts = {}
    for file_info in discovered_files.values():
        tier = file_info["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier, count in sorted(tier_counts.items(), key=lambda x: TIER_PRIORITIES[x[0]]):
        print("   - Tier %d (%s): %d files" % (TIER_PRIORITIES[tier], tier, count))

    print()

    # Check what's already uploaded
    print("📋 Checking existing files...")
    try:
        existing_files = client.beta.files.list()
        existing_filenames = {f.filename: f.id for f in existing_files.data}
        print("   Found %d files already uploaded" % len(existing_filenames))
    except Exception as e:  # pylint: disable=broad-except
        print("   Warning: Could not check existing files: %s" % e)
        existing_filenames = {}

    print()

    # Upload files
    file_ids = {}
    uploaded_count = 0
    skipped_count = 0
    error_count = 0

    for key, file_info in discovered_files.items():
        filepath = Path(file_info["path"])
        filename = file_info["filename"]

        # Check if already uploaded
        if filename in existing_filenames:
            print("✓  Already uploaded: %s" % filename)
            file_ids[key] = {
                "file_id": existing_filenames[filename],
                "filename": filename,
                "tier": file_info["tier"],
                "tier_priority": file_info["tier_priority"],
                "subject": file_info["subject"],
                "category": file_info["category"],
                "status": "existing"
            }
            skipped_count += 1
            continue

        # Upload file
        print("📤 Uploading: %s (Tier %d - %s)" % (filename, file_info['tier_priority'], file_info['tier']))
        try:
            uploaded_file = client.beta.files.upload(
                file=filepath
            )

            file_ids[key] = {
                "file_id": uploaded_file.id,
                "filename": uploaded_file.filename,
                "size_bytes": uploaded_file.size_bytes,
                "created_at": uploaded_file.created_at,
                "tier": file_info["tier"],
                "tier_priority": file_info["tier_priority"],
                "subject": file_info["subject"],
                "category": file_info["category"],
                "status": "uploaded"
            }

            size_mb = uploaded_file.size_bytes / (1024 * 1024)
            print("   ✅ Success! ID: %s (%.2f MB)" % (uploaded_file.id, size_mb))
            uploaded_count += 1

        except Exception as e:  # pylint: disable=broad-except
            print("   ❌ Error: %s" % str(e))
            error_count += 1

        print()

    # Save file IDs to JSON
    output_file = "file_ids.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(file_ids, f, indent=2, default=str)

    # Print summary
    print("=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print("✅ Uploaded: %d" % uploaded_count)
    print("⏭️  Skipped:  %d" % skipped_count)
    print("❌ Errors:   %d" % error_count)
    print("📁 Total:    %d" % len(file_ids))
    print()
    print("💾 File IDs saved to: %s" % output_file)
    print()

    # Print tier summary
    print("📊 Files by Tier:")
    print("-" * 60)
    for tier in sorted(TIER_PRIORITIES.keys(), key=lambda x: TIER_PRIORITIES[x]):
        tier_files = [k for k, v in file_ids.items() if v.get("tier") == tier]
        print("Tier %d (%s): %d files" % (TIER_PRIORITIES[tier], tier, len(tier_files)))
    print("-" * 60)

    return file_ids


def list_uploaded_files():
    """
    List all files currently uploaded to Anthropic.

    Prints a formatted list of all uploaded files with their IDs,
    sizes, and creation dates.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set!")
        return

    client = Anthropic(api_key=api_key)

    print("📋 Currently Uploaded Files:")
    print("=" * 60)

    try:
        files = client.beta.files.list()

        if not files.data:
            print("No files uploaded yet.")
            return

        for i, file_item in enumerate(files.data, 1):
            size_mb = file_item.size_bytes / (1024 * 1024)
            print("%d. %s" % (i, file_item.filename))
            print("   ID: %s" % file_item.id)
            print("   Size: %.2f MB" % size_mb)
            print("   Created: %s" % file_item.created_at)
            print()

        print("Total: %d files" % len(files.data))

    except Exception as e:  # pylint: disable=broad-except
        print("❌ Error: %s" % str(e))


def delete_all_files():
    """
    Delete all uploaded files from Anthropic.

    Use with caution! This will permanently delete all uploaded files.
    Requires user confirmation before proceeding.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set!")
        return

    client = Anthropic(api_key=api_key)

    # Confirmation
    user_response = input("⚠️  Delete ALL uploaded files? (yes/no): ")
    if user_response.lower() != "yes":
        print("Cancelled.")
        return

    try:
        files = client.beta.files.list()

        if not files.data:
            print("No files to delete.")
            return

        print("Deleting %d files..." % len(files.data))

        for file_item in files.data:
            try:
                client.beta.files.delete(file_item.id)
                print("✅ Deleted: %s" % file_item.filename)
            except Exception as delete_error:  # pylint: disable=broad-except
                print("❌ Error deleting %s: %s" % (file_item.filename, delete_error))

        print("Done!")

    except Exception as e:  # pylint: disable=broad-except
        print("❌ Error: %s" % str(e))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            list_uploaded_files()
        elif command == "delete":
            delete_all_files()
        elif command == "upload":
            directory = sys.argv[2] if len(sys.argv) > 2 else "./Materials"
            upload_course_files(directory)
        else:
            print("Usage:")
            print("  python upload_files_script.py upload [directory]  - Upload files from Materials/")
            print("  python upload_files_script.py list                - List uploaded files")
            print("  python upload_files_script.py delete              - Delete all files")
            print()
            print("The script automatically discovers files from the three-tier structure:")
            print("  - Tier 1: Syllabus/ (highest priority)")
            print("  - Tier 2: Course_Materials/")
            print("  - Tier 3: Supplementary_Sources/")
    else:
        # Default: upload files from Materials directory
        upload_course_files()
