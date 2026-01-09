#!/usr/bin/env python3
"""
Simple diagnostic script to check allow list user status.
Uses direct Firestore access without requiring full app initialization.

Usage:
    python scripts/check_user_simple.py amberunal13@gmail.com
"""

import sys
from urllib.parse import quote
from google.cloud import firestore
from datetime import datetime, timezone


def check_user_status(email: str):
    """Check the status of a user in the allow list."""
    print(f"\n{'='*80}")
    print(f"ALLOW LIST DIAGNOSTIC FOR: {email}")
    print(f"{'='*80}\n")
    
    # Normalize email
    normalized_email = email.lower().strip()
    print(f"1. Normalized email: {normalized_email}")
    
    # Check document ID encoding
    doc_id = quote(normalized_email, safe='')
    print(f"2. Document ID (URL-encoded): {doc_id}")
    
    # Initialize Firestore
    print(f"\n{'='*80}")
    print("CONNECTING TO FIRESTORE")
    print(f"{'='*80}\n")
    
    try:
        db = firestore.Client(project="vigilant-axis-483119-r8")
        print("✅ Connected to Firestore")
    except Exception as e:
        print(f"❌ Failed to connect to Firestore: {e}")
        print("\nPlease authenticate with:")
        print("  gcloud auth application-default login")
        return
    
    # Check if document exists
    print(f"\n{'='*80}")
    print("CHECKING FIRESTORE DOCUMENT")
    print(f"{'='*80}\n")
    
    try:
        doc_ref = db.collection("allowed_users").document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"❌ User NOT FOUND in allow list")
            print(f"   Collection: allowed_users")
            print(f"   Document ID: {doc_id}")
            print(f"\n✅ RESULT: User can be added to allow list")
            return
        
        print(f"✅ User FOUND in allow list")
        
        # Get document data
        data = doc.to_dict()
        
        print(f"\nRaw Firestore Data:")
        for key, value in sorted(data.items()):
            print(f"  {key}: {value}")
        
        # Parse fields
        active = data.get("active", False)
        expires_at = data.get("expires_at")
        added_at = data.get("added_at")
        updated_at = data.get("updated_at")
        added_by = data.get("added_by", "unknown")
        reason = data.get("reason", "")
        notes = data.get("notes", "")
        
        # Check if expired
        is_expired = False
        if expires_at is not None:
            now = datetime.now(timezone.utc)
            # Handle both datetime and timestamp
            if hasattr(expires_at, 'timestamp'):
                expires_dt = expires_at
            else:
                expires_dt = datetime.fromtimestamp(expires_at.timestamp(), tz=timezone.utc)
            is_expired = expires_dt <= now
        
        # Check if effective
        is_effective = active and not is_expired
        
        print(f"\n{'='*80}")
        print("STATUS ANALYSIS")
        print(f"{'='*80}\n")
        
        print(f"Active: {active}")
        print(f"Expired: {is_expired}")
        print(f"Effective (active AND not expired): {is_effective}")
        
        if is_effective:
            print(f"\n⚠️  USER IS ACTIVE AND EFFECTIVE")
            print(f"⚠️  User already has access to the system")
            print(f"⚠️  Cannot add - would create duplicate")
            print(f"\nℹ️  To modify this user:")
            print(f"   - Use the UPDATE endpoint to change details")
            print(f"   - Or REMOVE the user first, then re-add")
        elif not active:
            print(f"\n✅ USER IS INACTIVE (soft-deleted)")
            print(f"✅ User can be REACTIVATED by adding again")
            print(f"\nℹ️  The add_user() function should:")
            print(f"   - Detect user is inactive")
            print(f"   - Reactivate with new details")
            print(f"   - Set active=True")
        elif is_expired:
            print(f"\n✅ USER IS EXPIRED")
            print(f"✅ User can be RENEWED by adding again")
            print(f"\nℹ️  The add_user() function should:")
            print(f"   - Detect user is expired")
            print(f"   - Reactivate with new expiration")
            print(f"   - Set active=True")
        else:
            print(f"\n⚠️  UNEXPECTED STATE")
            print(f"   Active: {active}")
            print(f"   Expired: {is_expired}")
        
        print(f"\n{'='*80}")
        print("RECOMMENDATION")
        print(f"{'='*80}\n")
        
        if is_effective:
            print("❌ DO NOT ADD - User already has effective access")
            print("   Error message should be:")
            print(f"   'User {normalized_email} is already on the allow list and has active access.'")
        else:
            print("✅ CAN ADD - User should be reactivated")
            print("   Expected behavior:")
            print("   - add_user() detects inactive/expired user")
            print("   - Updates document with new details")
            print("   - Sets active=True")
            print("   - Returns 201 Created")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_user_simple.py <email>")
        print("Example: python scripts/check_user_simple.py amberunal13@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    check_user_status(email)

