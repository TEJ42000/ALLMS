#!/usr/bin/env python3
"""
Diagnostic script to check allow list user status.

Usage:
    python scripts/check_allow_list_user.py amberunal13@gmail.com
"""

import sys
import os
from pathlib import Path
from urllib.parse import quote

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gcp_service import get_firestore_client
from app.services.allow_list_service import get_allow_list_service


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
    
    # Check using AllowListService
    print(f"\n{'='*80}")
    print("CHECKING VIA ALLOWLISTSERVICE")
    print(f"{'='*80}\n")
    
    try:
        service = get_allow_list_service()
        
        if not service.is_available:
            print("❌ AllowListService is NOT available")
            return
        
        print("✅ AllowListService is available")
        
        # Get user entry
        entry = service.get_user(normalized_email)
        
        if entry is None:
            print(f"\n❌ User NOT FOUND in allow list")
            print(f"   Email: {normalized_email}")
            print(f"   Document ID: {doc_id}")
            print(f"\n✅ User can be added to allow list")
        else:
            print(f"\n✅ User FOUND in allow list")
            print(f"\nUser Details:")
            print(f"  - Email: {entry.email}")
            print(f"  - Active: {entry.active}")
            print(f"  - Expires At: {entry.expires_at}")
            print(f"  - Is Expired: {entry.is_expired}")
            print(f"  - Is Effective: {entry.is_effective}")
            print(f"  - Added By: {entry.added_by}")
            print(f"  - Added At: {entry.added_at}")
            print(f"  - Updated At: {entry.updated_at}")
            print(f"  - Reason: {entry.reason}")
            print(f"  - Notes: {entry.notes}")
            
            print(f"\nStatus Analysis:")
            if entry.is_effective:
                print(f"  ⚠️  User is ACTIVE and EFFECTIVE")
                print(f"  ⚠️  Cannot add - user already has access")
                print(f"  ℹ️  Use UPDATE endpoint to modify entry")
            elif not entry.active:
                print(f"  ✅ User is INACTIVE (soft-deleted)")
                print(f"  ✅ Can be REACTIVATED by adding again")
            elif entry.is_expired:
                print(f"  ✅ User is EXPIRED")
                print(f"  ✅ Can be RENEWED by adding again")
            else:
                print(f"  ⚠️  Unexpected state")
        
        # Check if user is allowed
        print(f"\n{'='*80}")
        print("CHECKING AUTHENTICATION STATUS")
        print(f"{'='*80}\n")
        
        is_allowed = service.is_user_allowed(normalized_email)
        
        if is_allowed:
            print(f"✅ User IS ALLOWED (has effective access)")
        else:
            print(f"❌ User IS NOT ALLOWED (no effective access)")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Check Firestore directly
    print(f"\n{'='*80}")
    print("CHECKING FIRESTORE DIRECTLY")
    print(f"{'='*80}\n")
    
    try:
        db = get_firestore_client()
        
        if db is None:
            print("❌ Firestore client is None")
            return
        
        print("✅ Firestore client available")
        
        # Get document
        doc_ref = db.collection("allowed_users").document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"\n❌ Document NOT FOUND in Firestore")
            print(f"   Collection: allowed_users")
            print(f"   Document ID: {doc_id}")
        else:
            print(f"\n✅ Document FOUND in Firestore")
            print(f"\nRaw Firestore Data:")
            data = doc.to_dict()
            for key, value in sorted(data.items()):
                print(f"  - {key}: {value}")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_allow_list_user.py <email>")
        print("Example: python scripts/check_allow_list_user.py amberunal13@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    check_user_status(email)

