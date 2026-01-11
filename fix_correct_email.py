#!/usr/bin/env python3
"""
Fix: Add the CORRECT email to Firestore.
The user's actual email is amberunal2013@gmail.com (with "2013"), not amberunal13@gmail.com
"""

from google.cloud import firestore
from datetime import datetime, timezone

def fix_email():
    db = firestore.Client(project='vigilant-axis-483119-r8')
    
    # The CORRECT email (with "2013")
    correct_email = 'amberunal2013@gmail.com'
    correct_doc_id = correct_email.replace('@', '%40')
    
    # The WRONG email we added before (without "2013")
    wrong_email = 'amberunal13@gmail.com'
    wrong_doc_id = wrong_email.replace('@', '%40')
    
    print("=" * 70)
    print("FIXING EMAIL ADDRESS IN FIRESTORE")
    print("=" * 70)
    print()
    print(f"❌ Wrong email (what we added): {wrong_email}")
    print(f"✅ Correct email (what user uses): {correct_email}")
    print()
    
    # Add the CORRECT email
    user_data = {
        'email': correct_email,
        'active': True,
        'added_by': 'matej@mgms.eu',
        'added_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'reason': 'External student access - corrected email address',
        'expires_at': None,
        'notes': 'Email corrected from amberunal13 to amberunal2013'
    }
    
    print(f"Adding CORRECT email to Firestore...")
    print(f"  Document ID: {correct_doc_id}")
    print()
    
    db.collection('allowed_users').document(correct_doc_id).set(user_data)
    
    print("✅ CORRECT email added successfully!")
    print()
    print("=" * 70)
    print("USER CAN NOW ACCESS THE APPLICATION")
    print("=" * 70)
    print()
    print("The user (amberunal2013@gmail.com) can now:")
    print("1. Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app")
    print("2. Click 'Login with Google'")
    print("3. Log in with amberunal2013@gmail.com")
    print("4. Access the application ✅")
    print()
    print("Note: The wrong email (amberunal13@gmail.com) is still in Firestore")
    print("      but it won't cause any issues. You can delete it later if needed.")
    print()

if __name__ == "__main__":
    fix_email()

