#!/usr/bin/env python3
"""
Quick script to add amberunal13@gmail.com directly to Firestore.
This bypasses the admin UI and adds the user immediately.
"""

from google.cloud import firestore
from datetime import datetime, timezone

def add_user_to_firestore(email: str, added_by: str, reason: str):
    """Add user directly to Firestore allowed_users collection."""
    try:
        db = firestore.Client(project='vigilant-axis-483119-r8')
        doc_id = email.replace('@', '%40')
        
        user_data = {
            'email': email.lower(),
            'active': True,
            'added_by': added_by.lower(),
            'added_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'reason': reason,
            'expires_at': None,
            'notes': None
        }
        
        print(f"Adding user to Firestore...")
        print(f"  Email: {email}")
        print(f"  Document ID: {doc_id}")
        print(f"  Added by: {added_by}")
        print(f"  Reason: {reason}")
        
        db.collection('allowed_users').document(doc_id).set(user_data)
        
        print("\n✅ SUCCESS! User added to Firestore!")
        print(f"\nThe user can now:")
        print(f"1. Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app")
        print(f"2. Click 'Login with Google'")
        print(f"3. Log in with {email}")
        print(f"4. Access the application")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    # Add amberunal13@gmail.com
    add_user_to_firestore(
        email="amberunal13@gmail.com",
        added_by="matej@mgms.eu",
        reason="External student access - added directly via script"
    )

