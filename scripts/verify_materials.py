#!/usr/bin/env python3
"""
Verify materials were uploaded to Firestore.
"""

from google.cloud import firestore

db = firestore.Client()

courses = [
    "Criminal-Law---Part--2025-2026",
    "LLS-2025-2026",
    "Legal-History-2025-2026"
]

print("=" * 60)
print("Verifying Materials in Firestore")
print("=" * 60)

for course_id in courses:
    materials_ref = db.collection("courses").document(course_id).collection("materials")
    materials = list(materials_ref.limit(10).stream())
    
    print(f"\n{course_id}:")
    print(f"  Total materials: {len(list(materials_ref.stream()))}")
    
    if materials:
        print(f"  Sample materials:")
        for mat in materials[:5]:
            data = mat.to_dict()
            print(f"    - {data.get('filename')} (Week {data.get('weekNumber')}, {data.get('tier')})")
    else:
        print(f"  ⚠️  No materials found!")

print("\n" + "=" * 60)
print("✅ Verification complete!")
print("=" * 60)

