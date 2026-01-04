#!/usr/bin/env python3
"""
Upload Course Materials to Anthropic Files API
Run this once to upload all your course PDFs to Anthropic.

This script automatically discovers files from the three-tier Materials structure:
- Tier 1: Syllabus/ - Official course syllabi
- Tier 2: Course_Materials/ - Primary learning materials
- Tier 3: Supplementary_Sources/ - External and supplementary materials
"""

from anthropic import Anthropic
import os
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.md', '.txt'}

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
        if tier_name not in TIER_PRIORITIES:
            continue

        # Recursively find all supported files in this tier
        for file_path in tier_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
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

    print(f"   Found {len(discovered_files)} files across all tiers")

    # Group by tier for display
    tier_counts = {}
    for file_info in discovered_files.values():
        tier = file_info["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier, count in sorted(tier_counts.items(), key=lambda x: TIER_PRIORITIES[x[0]]):
        print(f"   - Tier {TIER_PRIORITIES[tier]} ({tier}): {count} files")

    print()

    # Check what's already uploaded
    print("📋 Checking existing files...")
    try:
        existing_files = client.beta.files.list()
        existing_filenames = {f.filename: f.id for f in existing_files.data}
        print(f"   Found {len(existing_filenames)} files already uploaded")
    except Exception as e:
        print(f"   Warning: Could not check existing files: {e}")
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
            print(f"✓  Already uploaded: {filename}")
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
        print(f"📤 Uploading: {filename} (Tier {file_info['tier_priority']} - {file_info['tier']})")
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
            print(f"   ✅ Success! ID: {uploaded_file.id} ({size_mb:.2f} MB)")
            uploaded_count += 1

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_count += 1

        print()

    # Save file IDs to JSON
    output_file = "file_ids.json"
    with open(output_file, "w") as f:
        json.dump(file_ids, f, indent=2, default=str)

    # Print summary
    print("=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print(f"✅ Uploaded: {uploaded_count}")
    print(f"⏭️  Skipped:  {skipped_count}")
    print(f"❌ Errors:   {error_count}")
    print(f"📁 Total:    {len(file_ids)}")
    print()
    print(f"💾 File IDs saved to: {output_file}")
    print()

    # Print tier summary
    print("📊 Files by Tier:")
    print("-" * 60)
    for tier in sorted(TIER_PRIORITIES.keys(), key=lambda x: TIER_PRIORITIES[x]):
        tier_files = [k for k, v in file_ids.items() if v.get("tier") == tier]
        print(f"Tier {TIER_PRIORITIES[tier]} ({tier}): {len(tier_files)} files")
    print("-" * 60)

    return file_ids


def list_uploaded_files():
    """List all files currently uploaded to Anthropic"""
    
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
        
        for i, file in enumerate(files.data, 1):
            size_mb = file.size_bytes / (1024 * 1024)
            print(f"{i}. {file.filename}")
            print(f"   ID: {file.id}")
            print(f"   Size: {size_mb:.2f} MB")
            print(f"   Created: {file.created_at}")
            print()
        
        print(f"Total: {len(files.data)} files")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def delete_all_files():
    """Delete all uploaded files (use with caution!)"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set!")
        return
    
    client = Anthropic(api_key=api_key)
    
    # Confirmation
    response = input("⚠️  Delete ALL uploaded files? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        return
    
    try:
        files = client.beta.files.list()
        
        if not files.data:
            print("No files to delete.")
            return
        
        print(f"Deleting {len(files.data)} files...")
        
        for file in files.data:
            try:
                client.beta.files.delete(file.id)
                print(f"✅ Deleted: {file.filename}")
            except Exception as e:
                print(f"❌ Error deleting {file.filename}: {e}")
        
        print("Done!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


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
