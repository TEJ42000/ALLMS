#!/usr/bin/env python3
"""
Upload Course Materials to Anthropic Files API.

Run this once to upload all your course PDFs to Anthropic.
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic

# Course files to upload
COURSE_FILES = {
    "lls_reader": "LLSReaderwithcoursecontentandquestions_20252026.pdf",
    "readings_week_1": "Readings_Law__week_1_compressed.pdf",
    "readings_week_2": "Readings20Law2020week202_compressed.pdf",
    "lecture_week_3": "LLS_2526_Lecture_week_3_Administrative_law_Final.pdf",
    "lecture_week_4": "LLS_2526_Lecture_week_4_Criminal_law__Copy.pdf",
    "lecture_week_6": "LLS20256International20law20wk6.pdf",
    "elsa_notes": "ELSA_NOTES_.pdf",
    "mock_exam": "Mock_Exam_Skills.pdf",
    "mock_answers": "AnswersMockexamLAW2425.pdf",
    "legal_skills_review": "Copy_of_Legal_skills_review.docx",
    "law_review": "Law_review-tijana.docx"
}


def upload_course_files(files_directory: str = "./course-materials"):
    """
    Upload all course files to Anthropic Files API.

    Args:
        files_directory: Directory containing course files

    Returns:
        Dictionary of file_ids
    """
    # Initialize client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return {}

    client = Anthropic(api_key=api_key)
    files_dir = Path(files_directory)

    if not files_dir.exists():
        print("❌ Error: Directory not found: %s" % files_directory)
        return {}

    print("=" * 60)
    print("📚 LLS Course Materials Upload")
    print("=" * 60)
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

    for key, filename in COURSE_FILES.items():
        filepath = files_dir / filename

        # Check if file exists
        if not filepath.exists():
            print("⚠️  Skipped: %s (not found)" % filename)
            skipped_count += 1
            continue

        # Check if already uploaded
        if filename in existing_filenames:
            print("✓  Already uploaded: %s" % filename)
            file_ids[key] = {
                "file_id": existing_filenames[filename],
                "filename": filename,
                "status": "existing"
            }
            skipped_count += 1
            continue

        # Upload file
        print("📤 Uploading: %s" % filename)
        try:
            uploaded_file = client.beta.files.upload(
                file=filepath
            )

            file_ids[key] = {
                "file_id": uploaded_file.id,
                "filename": uploaded_file.filename,
                "size_bytes": uploaded_file.size_bytes,
                "created_at": uploaded_file.created_at,
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

    # Print file IDs table
    if file_ids:
        print("📋 Uploaded Files:")
        print("-" * 60)
        for key, info in file_ids.items():
            print("%-20s %s" % (key, info['file_id']))
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
            directory = sys.argv[2] if len(sys.argv) > 2 else "./course-materials"
            upload_course_files(directory)
        else:
            print("Usage:")
            print("  python upload_files.py upload [directory]  - Upload files")
            print("  python upload_files.py list                - List uploaded files")
            print("  python upload_files.py delete              - Delete all files")
    else:
        # Default: upload files
        upload_course_files()
