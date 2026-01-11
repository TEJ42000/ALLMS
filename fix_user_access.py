#!/usr/bin/env python3
"""
One-command fix: Verify and ensure amberunal13@gmail.com has access.
This will check if the user exists and fix any issues.
"""

from google.cloud import firestore
from datetime import datetime, timezone
import sys

def fix_user_access(email: str):
    """Verify user exists with correct settings, fix if needed."""
    try:
        print("=" * 60)
        print("FIRESTORE USER ACCESS FIX")
        print("=" * 60)
        print()
        
        db = firestore.Client(project='vigilant-axis-483119-r8')
        doc_id = email.replace('@', '%40')
        
        print(f"📧 Email: {email}")
        print(f"📄 Document ID: {doc_id}")
        print()
        
        doc_ref = db.collection('allowed_users').document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            print("✅ USER EXISTS IN FIRESTORE")
            print()
            print("Current Settings:")
            print(f"  email: {data.get('email')}")
            print(f"  active: {data.get('active')}")
            print(f"  expires_at: {data.get('expires_at')}")
            print(f"  added_by: {data.get('added_by')}")
            print(f"  reason: {data.get('reason')}")
            print()
            
            # Check if needs fixing
            active = data.get('active', False)
            
            if not active:
                print("⚠️  ISSUE FOUND: active=False")
                print("🔧 FIXING: Setting active=True...")
                
                doc_ref.update({
                    'active': True,
                    'updated_at': datetime.now(timezone.utc)
                })
                
                print("✅ FIXED: User is now active")
                print()
            else:
                print("✅ USER IS ALREADY ACTIVE")
                print()
            
            print("=" * 60)
            print("VERIFICATION COMPLETE")
            print("=" * 60)
            print()
            print("User Status: ✅ ACTIVE")
            print("User Should Have Access: ✅ YES")
            print()
            print("Next Steps:")
            print("1. Have user close ALL browser tabs")
            print("2. Have user open NEW incognito/private window")
            print("3. Have user go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app")
            print("4. Have user click 'Login with Google'")
            print("5. Have user log in with amberunal13@gmail.com")
            print()
            
        else:
            print("❌ USER DOES NOT EXIST IN FIRESTORE")
            print()
            print("🔧 CREATING USER...")
            
            user_data = {
                'email': email.lower(),
                'active': True,
                'added_by': 'matej@mgms.eu',
                'added_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'reason': 'External student access - added via fix script',
                'expires_at': None,
                'notes': None
            }
            
            doc_ref.set(user_data)
            
            print("✅ USER CREATED SUCCESSFULLY")
            print()
            print("User Details:")
            print(f"  email: {user_data['email']}")
            print(f"  active: {user_data['active']}")
            print(f"  added_by: {user_data['added_by']}")
            print(f"  reason: {user_data['reason']}")
            print()
            print("=" * 60)
            print("USER CREATION COMPLETE")
            print("=" * 60)
            print()
            print("User Status: ✅ ACTIVE")
            print("User Should Have Access: ✅ YES")
            print()
            print("Next Steps:")
            print("1. Have user close ALL browser tabs")
            print("2. Have user open NEW incognito/private window")
            print("3. Have user go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app")
            print("4. Have user click 'Login with Google'")
            print("5. Have user log in with amberunal13@gmail.com")
            print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"❌ {e}")
        print()
        print("This might be an authentication issue.")
        print("Try running: gcloud auth application-default login")
        print()
        return False

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "amberunal13@gmail.com"
    fix_user_access(email)

