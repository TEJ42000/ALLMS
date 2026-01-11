#!/usr/bin/env python3
"""
Test the authentication flow for amberunal13@gmail.com
This simulates what happens when the user tries to log in.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/matejmonteleone/PycharmProjects/LLMRMS')

from app.services.allow_list_service import get_allow_list_service
from app.services.auth_service import check_allow_list

async def test_auth_flow():
    """Test the complete authentication flow."""
    email = "amberunal13@gmail.com"
    
    print("=" * 70)
    print("AUTHENTICATION FLOW TEST")
    print("=" * 70)
    print(f"\nTesting email: {email}\n")
    
    # Step 1: Test AllowListService directly
    print("─" * 70)
    print("STEP 1: Testing AllowListService.is_user_allowed()")
    print("─" * 70)
    
    try:
        service = get_allow_list_service()
        
        if not service.is_available:
            print("❌ FAIL: AllowListService is not available")
            print("   Firestore client is None")
            return False
        
        print("✅ AllowListService is available")
        
        # Get the user entry
        entry = service.get_user(email)
        
        if entry is None:
            print(f"❌ FAIL: User not found in Firestore")
            print(f"   Document ID would be: {email.replace('@', '%40')}")
            return False
        
        print(f"✅ User found in Firestore")
        print(f"   Email: {entry.email}")
        print(f"   Active: {entry.active}")
        print(f"   Expires At: {entry.expires_at}")
        print(f"   Is Expired: {entry.is_expired}")
        print(f"   Is Effective: {entry.is_effective}")
        
        # Check if user is allowed
        is_allowed = service.is_user_allowed(email)
        
        if is_allowed:
            print(f"✅ is_user_allowed() returned: True")
        else:
            print(f"❌ is_user_allowed() returned: False")
            print(f"   This means user will be DENIED access!")
            print(f"   Reason: active={entry.active}, is_expired={entry.is_expired}")
            return False
        
    except Exception as e:
        print(f"❌ EXCEPTION in AllowListService: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Test auth_service.check_allow_list()
    print("\n" + "─" * 70)
    print("STEP 2: Testing auth_service.check_allow_list()")
    print("─" * 70)
    
    try:
        is_allowed = await check_allow_list(email)
        
        if is_allowed:
            print(f"✅ check_allow_list() returned: True")
            print(f"   User SHOULD have access!")
        else:
            print(f"❌ check_allow_list() returned: False")
            print(f"   User will be DENIED access!")
            return False
        
    except Exception as e:
        print(f"❌ EXCEPTION in check_allow_list(): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Success!
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print(f"\nUser {email} SHOULD have access to the application.")
    print("\nIf user still can't access, the issue is:")
    print("1. Browser cache (user needs to use incognito)")
    print("2. OAuth session issue (check session_service)")
    print("3. Middleware issue (check auth_middleware)")
    print()
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_auth_flow())
    sys.exit(0 if result else 1)

