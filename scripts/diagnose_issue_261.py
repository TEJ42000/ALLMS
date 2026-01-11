#!/usr/bin/env python3
"""
Diagnostic script for Issue #261: Study Guide shows 'No materials found'

This script checks:
1. If course exists in Firestore
2. If materials exist in local Materials folder
3. If materials exist in Firestore subcollection
4. What the mismatch is and how to fix it
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    course_id = "LLS-2025-2026"
    
    print("=" * 70)
    print(f"🔍 Diagnostic Report for Issue #261")
    print(f"   Course: {course_id}")
    print("=" * 70)
    
    # Check 1: Local Materials Folder
    print("\n📁 Step 1: Checking Local Materials Folder")
    print("-" * 70)
    
    materials_base = Path("Materials")
    course_materials_dir = materials_base / "Course_Materials" / course_id
    
    if course_materials_dir.exists():
        print(f"✅ Course folder exists: {course_materials_dir}")
        
        # Count files
        files = list(course_materials_dir.rglob("*"))
        pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
        txt_files = [f for f in files if f.suffix.lower() == '.txt']
        all_files = [f for f in files if f.is_file()]
        
        print(f"   📊 Total files: {len(all_files)}")
        print(f"   📄 PDF files: {len(pdf_files)}")
        print(f"   📝 TXT files: {len(txt_files)}")
        
        if all_files:
            print(f"\n   Sample files:")
            for f in all_files[:5]:
                rel_path = f.relative_to(materials_base)
                print(f"   - {rel_path}")
        
        local_materials_exist = len(all_files) > 0
    else:
        print(f"❌ Course folder NOT found: {course_materials_dir}")
        local_materials_exist = False
    
    # Check 2: Firestore Course Document
    print("\n🔥 Step 2: Checking Firestore Course Document")
    print("-" * 70)
    
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        course_ref = db.collection("courses").document(course_id)
        course_doc = course_ref.get()
        
        if course_doc.exists:
            print(f"✅ Course document exists in Firestore")
            course_data = course_doc.to_dict()
            print(f"   Name: {course_data.get('name', 'N/A')}")
            print(f"   Material Subjects: {course_data.get('materialSubjects', [])}")
            course_exists = True
        else:
            print(f"❌ Course document NOT found in Firestore")
            course_exists = False
    except Exception as e:
        print(f"⚠️  Could not connect to Firestore: {e}")
        print(f"   (This is OK for local development)")
        course_exists = None
    
    # Check 3: Firestore Materials Subcollection
    print("\n📚 Step 3: Checking Firestore Materials Subcollection")
    print("-" * 70)
    
    if course_exists is not None:
        try:
            materials_ref = course_ref.collection("materials")
            materials = list(materials_ref.limit(10).stream())
            
            print(f"   Materials in Firestore: {len(materials)}")
            
            if materials:
                print(f"✅ Materials found in Firestore subcollection")
                print(f"\n   Sample materials:")
                for i, mat in enumerate(materials[:5], 1):
                    data = mat.to_dict()
                    print(f"   {i}. {data.get('filename', 'N/A')}")
                    print(f"      - Week: {data.get('weekNumber', 'N/A')}")
                    print(f"      - Tier: {data.get('tier', 'N/A')}")
                    print(f"      - Path: {data.get('storagePath', 'N/A')}")
                
                # Check for week 5 specifically
                week5_materials = list(materials_ref.where("weekNumber", "==", 5).stream())
                print(f"\n   📅 Week 5 materials: {len(week5_materials)}")
                
                firestore_materials_exist = True
            else:
                print(f"❌ No materials found in Firestore subcollection")
                firestore_materials_exist = False
        except Exception as e:
            print(f"⚠️  Error querying materials: {e}")
            firestore_materials_exist = None
    else:
        firestore_materials_exist = None
    
    # Diagnosis
    print("\n" + "=" * 70)
    print("🔬 DIAGNOSIS")
    print("=" * 70)
    
    if local_materials_exist and not firestore_materials_exist:
        print("\n❌ ROOT CAUSE IDENTIFIED:")
        print("   Materials exist locally but NOT in Firestore!")
        print("\n💡 SOLUTION:")
        print("   Run the materials population script:")
        print(f"\n   python scripts/populate_firestore_materials.py")
        print("\n   This will:")
        print("   1. Scan Materials/Course_Materials/LLS-2025-2026/")
        print("   2. Create Firestore documents in courses/LLS-2025-2026/materials")
        print("   3. Materials will appear in Study Guide immediately")
        return 1
    
    elif not local_materials_exist and firestore_materials_exist:
        print("\n⚠️  UNUSUAL SITUATION:")
        print("   Materials exist in Firestore but NOT locally!")
        print("\n💡 SOLUTION:")
        print("   1. Check if materials were deleted from local folder")
        print("   2. Re-upload materials to Materials/Course_Materials/LLS-2025-2026/")
        return 1
    
    elif not local_materials_exist and not firestore_materials_exist:
        print("\n❌ NO MATERIALS FOUND:")
        print("   Materials don't exist locally OR in Firestore!")
        print("\n💡 SOLUTION:")
        print("   1. Upload materials to Materials/Course_Materials/LLS-2025-2026/")
        print("   2. Run: python scripts/populate_firestore_materials.py")
        return 1
    
    elif local_materials_exist and firestore_materials_exist:
        print("\n✅ MATERIALS EXIST IN BOTH PLACES")
        print("   This is the correct state!")
        print("\n🤔 If Study Guide still shows 'No materials found':")
        print("   1. Check if week filter is correct (week 5 exists?)")
        print("   2. Check browser console for errors")
        print("   3. Check Cloud Run logs for API errors")
        return 0
    
    else:
        print("\n⚠️  Could not complete diagnosis (Firestore connection issue)")
        print("   Run this script with Firestore credentials to complete diagnosis")
        return 1

if __name__ == "__main__":
    sys.exit(main())

