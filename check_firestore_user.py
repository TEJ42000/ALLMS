#!/usr/bin/env python3
"""Quick script to check if a user exists in Firestore allowed_users collection."""

import sys
from google.cloud import firestore

def check_user(email: str):
    """Check if user exists in Firestore."""
    try:
        db = firestore.Client(project="vigilant-axis-483119-r8")
        doc_id = email.replace("@", "%40")
        doc_ref = db.collection("allowed_users").document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ User EXISTS in Firestore:")
            print(f"   Email: {data.get('email')}")
            print(f"   Active: {data.get('active')}")
            print(f"   Expires At: {data.get('expires_at')}")
            print(f"   Added By: {data.get('added_by')}")
            print(f"   Added At: {data.get('added_at')}")
            print(f"   Reason: {data.get('reason')}")
            return True
        else:
            print(f"❌ User does NOT exist in Firestore")
            return False
    except Exception as e:
        print(f"❌ Error checking Firestore: {e}")
        return False

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "amberunal13@gmail.com"
    check_user(email)

