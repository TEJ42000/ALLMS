#!/usr/bin/env python3
"""
Upload Course Materials to Anthropic Files API
Run this once to upload all your course PDFs to Anthropic.
"""

from anthropic import Anthropic
import os
from pathlib import Path
import json
from datetime import datetime

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
        print(f"❌ Error: Directory not found: {files_directory}")
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
    
    for key, filename in COURSE_FILES.items():
        filepath = files_dir / filename
        
        # Check if file exists
        if not filepath.exists():
            print(f"⚠️  Skipped: {filename} (not found)")
            skipped_count += 1
            continue
        
        # Check if already uploaded
        if filename in existing_filenames:
            print(f"✓  Already uploaded: {filename}")
            file_ids[key] = {
                "file_id": existing_filenames[filename],
                "filename": filename,
                "status": "existing"
            }
            skipped_count += 1
            continue
        
        # Upload file
        print(f"📤 Uploading: {filename}")
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
    
    # Print file IDs table
    if file_ids:
        print("📋 Uploaded Files:")
        print("-" * 60)
        for key, info in file_ids.items():
            print(f"{key:20} {info['file_id']}")
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
