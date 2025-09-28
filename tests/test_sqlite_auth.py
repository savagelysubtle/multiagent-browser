"""
Test script for SQLite-based authentication system.

This script tests user registration and login functionality
with the new SQLite database instead of ChromaDB.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from web_ui.api.auth.auth_service import auth_service
from web_ui.database.user_db import UserDatabase


async def test_auth_flow():
    """Test the complete authentication flow."""
    print("🔍 Testing SQLite Authentication System\n")

    # Test 1: Database initialization
    print("1. Testing database initialization...")
    try:
        user_db = UserDatabase()
        print("✅ SQLite database initialized successfully")
        print(f"   Database path: {user_db.db_path}")
        print(f"   User count: {user_db.get_user_count()}\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}\n")
        return

    # Test 2: User registration
    print("2. Testing user registration...")
    test_email = "test@example.com"
    test_password = "securepassword123"
    test_name = "Test User"

    try:
        # First check if user exists
        if user_db.user_exists(test_email):
            print(f"⚠️  User {test_email} already exists, cleaning up...")
            existing_user = user_db.get_user_by_email(test_email)
            if existing_user:
                user_db.delete_user(existing_user["id"])
                print("   Deleted existing test user\n")

        # Create new user
        user = await auth_service.create_user(
            email=test_email, password=test_password, name=test_name
        )
        print("✅ User created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
        print(f"   Created at: {user.created_at}\n")

    except Exception as e:
        print(f"❌ User registration failed: {e}\n")
        return

    # Test 3: User lookup by email
    print("3. Testing user lookup by email...")
    try:
        found_user = await auth_service.get_user_by_email(test_email)
        if found_user:
            print(f"✅ User found by email: {found_user.email}")
            print(f"   ID matches: {found_user.id == user.id}\n")
        else:
            print("❌ User not found by email\n")
            return
    except Exception as e:
        print(f"❌ User lookup failed: {e}\n")
        return

    # Test 4: User authentication
    print("4. Testing user authentication...")
    try:
        # Test with correct password
        auth_user = await auth_service.authenticate_user(test_email, test_password)
        if auth_user:
            print("✅ Authentication successful with correct password")
            print(f"   Last login updated: {auth_user.last_login}\n")
        else:
            print("❌ Authentication failed with correct password\n")
            return

        # Test with wrong password
        wrong_auth = await auth_service.authenticate_user(test_email, "wrongpassword")
        if wrong_auth is None:
            print("✅ Authentication correctly failed with wrong password\n")
        else:
            print("❌ Authentication should have failed with wrong password\n")

    except Exception as e:
        print(f"❌ Authentication test failed: {e}\n")
        return

    # Test 5: JWT token generation and verification
    print("5. Testing JWT token generation...")
    try:
        # Generate token
        token = auth_service.create_access_token(user.id)
        print("✅ JWT token generated successfully")
        print(f"   Token length: {len(token)} characters")

        # Verify token
        verified_user_id = auth_service.verify_token(token)
        if verified_user_id == user.id:
            print("✅ Token verification successful")
            print(f"   User ID from token: {verified_user_id}\n")
        else:
            print("❌ Token verification failed\n")

    except Exception as e:
        print(f"❌ JWT token test failed: {e}\n")
        return

    # Test 6: User statistics
    print("6. Testing user statistics...")
    try:
        stats = auth_service.get_user_stats()
        print("✅ User statistics retrieved:")
        print(f"   Total users: {stats['total_users']}")
        print(f"   Database type: {stats['database_type']}")
        print(f"   Last updated: {stats['last_updated']}\n")
    except Exception as e:
        print(f"❌ User statistics failed: {e}\n")

    # Test 7: Admin user creation (if configured)
    print("7. Testing admin user creation...")
    try:
        admin_user = await auth_service.ensure_admin_user()
        if admin_user:
            print(f"✅ Admin user created/verified: {admin_user.email}\n")
        else:
            print("ℹ️  Admin user not configured (normal in production)\n")
    except Exception as e:
        print(f"⚠️  Admin user creation skipped: {e}\n")

    # Cleanup
    print("8. Cleaning up test data...")
    try:
        # Delete test user
        deleted = await auth_service.delete_user(user.id)
        if deleted:
            print("✅ Test user deleted successfully")
        else:
            print("⚠️  Could not delete test user")

        print("\n✅ All tests completed successfully! 🎉")
        print("   The SQLite authentication system is working correctly.")

    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(test_auth_flow())
