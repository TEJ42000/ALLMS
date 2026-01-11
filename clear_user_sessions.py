#!/usr/bin/env python3
"""
Clear all session data for a specific user from Firestore.
This removes any cached "denied" sessions.
"""

from google.cloud import firestore

def clear_user_sessions(email: str):
    """Clear all sessions for a user from Firestore."""
    try:
        db = firestore.Client(project='vigilant-axis-483119-r8')
        
        print(f"🔍 Searching for sessions for: {email}")
        
        # Check if there's a sessions collection
        sessions_ref = db.collection('sessions')
        
        # Query for sessions belonging to this user
        # Sessions might be stored with email as a field
        sessions = sessions_ref.where('email', '==', email.lower()).stream()
        
        deleted_count = 0
        for session in sessions:
            print(f"  Deleting session: {session.id}")
            session.reference.delete()
            deleted_count += 1
        
        if deleted_count > 0:
            print(f"\n✅ Deleted {deleted_count} session(s) for {email}")
        else:
            print(f"\n✅ No sessions found for {email} (this is normal)")
        
        print(f"\nThe user should now:")
        print(f"1. Close ALL browser tabs")
        print(f"2. Clear browser cookies for lls-study-portal-sarfwmfd3q-ez.a.run.app")
        print(f"3. Open NEW incognito/private window")
        print(f"4. Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app")
        print(f"5. Click 'Login with Google'")
        print(f"6. Log in with {email}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    clear_user_sessions("amberunal13@gmail.com")

