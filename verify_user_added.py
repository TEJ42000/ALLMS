#!/usr/bin/env python3
"""
Verify that amberunal13@gmail.com was added correctly to Firestore.
"""

from google.cloud import firestore

def verify_user(email: str):
    """Verify user exists in Firestore with correct settings."""
    try:
        db = firestore.Client(project='vigilant-axis-483119-r8')
        doc_id = email.replace('@', '%40')
        
        print(f"🔍 Checking Firestore for: {email}")
        print(f"   Document ID: {doc_id}")
        print()
        
        doc_ref = db.collection('allowed_users').document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            print("✅ USER EXISTS IN FIRESTORE")
            print()
            print("📋 User Details:")
            print(f"   Email: {data.get('email')}")
            print(f"   Active: {data.get('active')}")
            print(f"   Expires At: {data.get('expires_at')}")
            print(f"   Added By: {data.get('added_by')}")
            print(f"   Added At: {data.get('added_at')}")
            print(f"   Reason: {data.get('reason')}")
            print()
            
            # Check if user is effective
            active = data.get('active', False)
            expires_at = data.get('expires_at')
            
            if active and expires_at is None:
                print("✅ USER IS ACTIVE AND NOT EXPIRED")
                print("✅ User SHOULD have access")
            elif not active:
                print("❌ USER IS INACTIVE (active=False)")
                print("❌ User will NOT have access")
                print()
                print("FIX: Set active=True in Firestore")
            elif expires_at:
                print(f"⚠️  USER HAS EXPIRATION: {expires_at}")
                print("   Check if expired")
            
            return data
        else:
            print("❌ USER DOES NOT EXIST IN FIRESTORE")
            print()
            print("This means the 'Add User' action failed or didn't save.")
            print()
            print("FIX: Try adding the user again via admin UI")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    verify_user("amberunal13@gmail.com")

