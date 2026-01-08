#!/usr/bin/env python3
"""
Clean up LLS materials - fix week 202 and organize materials properly.
"""

import re
from google.cloud import firestore

COURSE_ID = "LLS-2025-2026"

def fix_week_202():
    """Fix the incorrectly assigned week 202."""
    print("🔧 Fixing week 202...")
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    
    # Find materials with week 202
    materials = materials_ref.where("weekNumber", "==", 202).stream()
    
    updates = []
    for mat in materials:
        data = mat.to_dict()
        filename = data.get('filename', '')
        
        # This should be week 2
        updates.append({
            'id': mat.id,
            'filename': filename,
            'new_week': 2
        })
    
    if updates:
        batch = db.batch()
        for update in updates:
            doc_ref = materials_ref.document(update['id'])
            batch.update(doc_ref, {'weekNumber': update['new_week']})
            print(f"   {update['filename']}: Week 202 → Week 2")
        
        batch.commit()
        print(f"✅ Fixed {len(updates)} materials")
    else:
        print("   No materials with week 202 found")


def delete_non_course_materials():
    """Delete materials that aren't actual course content."""
    print("\n🗑️  Removing non-course materials...")
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    
    # Files to remove (not actual course materials)
    to_remove = [
        'COURSE_STRUCTURE_AND_APP_DEV_GUIDE.md',
        'lls-study-portal-FINAL-WORKING.html',
        'README.md',
        'Matej Monteleone Donkersgang 6B.pdf',  # Personal document
    ]
    
    materials = materials_ref.stream()
    deleted = []
    
    batch = db.batch()
    for mat in materials:
        data = mat.to_dict()
        filename = data.get('filename', '')
        
        if filename in to_remove:
            batch.delete(materials_ref.document(mat.id))
            deleted.append(filename)
    
    if deleted:
        batch.commit()
        print(f"   Removed {len(deleted)} non-course files:")
        for filename in deleted:
            print(f"      - {filename}")
    else:
        print("   No non-course files found")


def verify_final_state():
    """Show final state of LLS materials."""
    print("\n📊 Final LLS Materials:")
    print("=" * 80)
    
    db = firestore.Client()
    materials_ref = db.collection("courses").document(COURSE_ID).collection("materials")
    materials = list(materials_ref.stream())
    
    # Group by week
    by_week = {}
    for mat in materials:
        data = mat.to_dict()
        week = data.get('weekNumber', 'General')
        if week not in by_week:
            by_week[week] = []
        by_week[week].append(data.get('filename'))
    
    for week in sorted(by_week.keys(), key=lambda x: x if isinstance(x, int) else 999):
        print(f"\nWeek {week}: {len(by_week[week])} materials")
        for filename in by_week[week]:
            print(f"  - {filename}")
    
    print(f"\n📈 Total: {len(materials)} materials")


def main():
    print("=" * 80)
    print("Clean Up LLS Materials")
    print("=" * 80)
    
    # Fix week 202
    fix_week_202()
    
    # Remove non-course materials
    delete_non_course_materials()
    
    # Show final state
    verify_final_state()
    
    print("\n" + "=" * 80)
    print("✅ LLS materials cleaned up!")
    print("=" * 80)


if __name__ == "__main__":
    main()

