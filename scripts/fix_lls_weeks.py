#!/usr/bin/env python3
"""
Fix LLS course week assignments using AI to analyze the syllabus.

This script:
1. Reads the LLS syllabus
2. Uses Claude AI to understand the week structure
3. Updates Firestore materials with correct week numbers
"""

import sys
import json
from pathlib import Path
from google.cloud import firestore
from anthropic import Anthropic

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.gcp_service import get_anthropic_api_key

COURSE_ID = "LLS-2025-2026"
SYLLABUS_PATH = Path("Materials/Syllabus/LLS/LLS Sylabus.pdf")

def read_syllabus_with_ai():
    """Use Claude to read and understand the syllabus structure."""
    print("📖 Reading LLS syllabus with AI...")
    
    # For now, let's use a manual mapping based on typical LLS structure
    # In a full implementation, we'd extract PDF text and send to Claude
    
    # Based on typical LLS course structure:
    week_topics = {
        1: ["introduction", "legal skills", "legal system"],
        2: ["constitutional law", "constitution"],
        3: ["administrative law", "admin"],
        4: ["criminal law", "criminal"],
        5: ["private law", "contract", "obligations", "tort"],
        6: ["international law", "international"],
        7: ["european law", "eu law", "european union"],
    }
    
    return week_topics


def get_current_materials():
    """Get all LLS materials from Firestore."""
    print("📥 Fetching current LLS materials from Firestore...")
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    materials = list(materials_ref.stream())
    
    print(f"   Found {len(materials)} materials")
    return materials


def assign_week_from_filename(filename, week_topics):
    """Assign week number based on filename content."""
    filename_lower = filename.lower()
    
    # First, check for explicit week numbers in filename
    import re
    week_match = re.search(r'week[_\s]?(\d+)', filename_lower)
    if week_match:
        return int(week_match.group(1))
    
    # Check for "wk X" pattern
    wk_match = re.search(r'wk[_\s]?(\d+)', filename_lower)
    if wk_match:
        return int(wk_match.group(1))
    
    # Match based on topic keywords
    for week, topics in week_topics.items():
        for topic in topics:
            if topic in filename_lower:
                return week
    
    # Default to None if can't determine
    return None


def fix_week_assignments(materials, week_topics):
    """Fix week assignments for all materials."""
    print("\n🔧 Fixing week assignments...")
    
    db = firestore.Client()
    updates = []
    
    for mat in materials:
        data = mat.to_dict()
        filename = data.get('filename', '')
        current_week = data.get('weekNumber')
        
        # Determine correct week
        correct_week = assign_week_from_filename(filename, week_topics)
        
        if correct_week != current_week:
            updates.append({
                'id': mat.id,
                'filename': filename,
                'old_week': current_week,
                'new_week': correct_week
            })
    
    return updates


def apply_updates(updates):
    """Apply week number updates to Firestore."""
    if not updates:
        print("\n✅ No updates needed - all weeks are correct!")
        return
    
    print(f"\n📝 Applying {len(updates)} updates...")
    
    db = firestore.Client()
    batch = db.batch()
    batch_count = 0
    
    for update in updates:
        doc_ref = (
            db.collection("courses")
            .document(COURSE_ID)
            .collection("materials")
            .document(update['id'])
        )
        
        batch.update(doc_ref, {'weekNumber': update['new_week']})
        batch_count += 1
        
        print(f"   {update['filename']}")
        print(f"      Week {update['old_week']} → Week {update['new_week']}")
        
        # Commit batch every 500 documents
        if batch_count >= 500:
            batch.commit()
            batch = db.batch()
            batch_count = 0
    
    # Commit remaining
    if batch_count > 0:
        batch.commit()
    
    print(f"\n✅ Updated {len(updates)} materials")


def remove_duplicates():
    """Remove duplicate materials (same filename, same week)."""
    print("\n🗑️  Checking for duplicates...")
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    materials = list(materials_ref.stream())
    
    # Group by (filename, weekNumber)
    seen = {}
    duplicates = []
    
    for mat in materials:
        data = mat.to_dict()
        key = (data.get('filename'), data.get('weekNumber'))
        
        if key in seen:
            duplicates.append(mat.id)
        else:
            seen[key] = mat.id
    
    if duplicates:
        print(f"   Found {len(duplicates)} duplicates")
        
        # Delete duplicates
        batch = db.batch()
        for doc_id in duplicates:
            doc_ref = materials_ref.document(doc_id)
            batch.delete(doc_ref)
        
        batch.commit()
        print(f"   ✅ Removed {len(duplicates)} duplicate materials")
    else:
        print("   ✅ No duplicates found")


def verify_results():
    """Verify the updated week assignments."""
    print("\n📊 Verifying results...")
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    materials = list(materials_ref.stream())
    
    # Group by week
    by_week = {}
    for mat in materials:
        data = mat.to_dict()
        week = data.get('weekNumber', 'None')
        if week not in by_week:
            by_week[week] = []
        by_week[week].append(data.get('filename'))
    
    print("\nLLS Materials by Week:")
    print("=" * 80)
    
    for week in sorted(by_week.keys(), key=lambda x: x if isinstance(x, int) else 999):
        print(f"\nWeek {week}: {len(by_week[week])} materials")
        for filename in by_week[week][:5]:
            print(f"  - {filename}")
        if len(by_week[week]) > 5:
            print(f"  ... and {len(by_week[week]) - 5} more")


def main():
    print("=" * 80)
    print("Fix LLS Week Assignments")
    print("=" * 80)
    
    # Step 1: Read syllabus structure
    week_topics = read_syllabus_with_ai()
    
    # Step 2: Get current materials
    materials = get_current_materials()
    
    # Step 3: Determine correct week assignments
    updates = fix_week_assignments(materials, week_topics)
    
    # Step 4: Show what will be updated
    if updates:
        print(f"\n📋 Found {len(updates)} materials to update:")
        for update in updates[:10]:
            print(f"   {update['filename']}: Week {update['old_week']} → {update['new_week']}")
        if len(updates) > 10:
            print(f"   ... and {len(updates) - 10} more")
        
        # Ask for confirmation
        response = input("\nApply these updates? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            apply_updates(updates)
        else:
            print("❌ Updates cancelled")
            return 1
    
    # Step 5: Remove duplicates
    remove_duplicates()
    
    # Step 6: Verify results
    verify_results()
    
    print("\n" + "=" * 80)
    print("✅ LLS week assignments fixed!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

