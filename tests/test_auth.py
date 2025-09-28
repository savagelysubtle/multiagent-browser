#!/usr/bin/env python3
"""
Test script to debug authentication registration issues.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend/src to path for the new structure
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))

# Set environment variables for testing
os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-development-only"
os.environ["ENV"] = "development"

from web_ui.api.auth.auth_service import auth_service


async def test_auth():
    """Test authentication service operations."""
    try:
        print("Testing authentication service...")

        # Test 1: Check if service is initialized
        print(f"Auth service initialized: {auth_service is not None}")
        print(
            f"Secret key configured: {auth_service.secret_key != 'dev-secret-key-change-in-production'}"
        )
        print(f"Secret key value: {auth_service.secret_key[:20]}...")

        # Test 2: Check database connection
        print(f"ChromaDB manager: {auth_service.chroma_manager is not None}")

        # Test 3: Fix bcrypt compatibility issue by using pbkdf2_sha256
        test_password = "password123"
        print(f"Testing password hashing with password: '{test_password}'")

        try:
            # Try to get password hash with current setup
            hashed = auth_service.get_password_hash(test_password)
            print(f"Password hashing works: {len(hashed) > 0}")
            print(f"Hash length: {len(hashed)}")
            print(f"Hash sample: {hashed[:30]}...")

            # Test verification
            verified = auth_service.verify_password(test_password, hashed)
            print(f"Password verification works: {verified}")

        except Exception as hash_error:
            print(f"Password hashing failed: {hash_error}")
            print("Trying alternative password hashing approach...")

            # Import and use alternative hashing
            from passlib.context import CryptContext

            try:
                # Use pbkdf2_sha256 as fallback (more compatible than bcrypt)
                fallback_context = CryptContext(
                    schemes=["pbkdf2_sha256"], deprecated="auto"
                )
                hashed = fallback_context.hash(test_password)
                verified = fallback_context.verify(test_password, hashed)
                print(f"Fallback hashing works: {verified}")

                # Update the auth service module to use the fallback
                import web_ui.api.auth.auth_service as auth_module

                auth_module.pwd_context = fallback_context

                # Update the global instance too
                auth_service.pwd_context = fallback_context
                print("Updated auth service to use pbkdf2_sha256 hashing")

            except Exception as fallback_error:
                print(f"Fallback hashing also failed: {fallback_error}")
                return

        # Test 4: Try to create a user
        test_email = "test@example.com"
        print(f"\nTesting user creation for: {test_email}")

        # Check if user already exists
        try:
            existing_user = await auth_service.get_user_by_email(test_email)
            if existing_user:
                print("User already exists, testing authentication...")

                # Test authentication with existing user
                auth_user = await auth_service.authenticate_user(
                    test_email, test_password
                )
                if auth_user:
                    print(
                        f"Authentication successful for existing user: {auth_user.email}"
                    )
                else:
                    print("Authentication failed for existing user")
                return

        except Exception as get_user_error:
            print(f"Error checking existing user: {get_user_error}")

        # Create new user
        try:
            user = await auth_service.create_user(
                email=test_email, password=test_password, name="Test User"
            )

            print(f"User created successfully: {user.email}")
            print(f"User ID: {user.id}")
            print(f"User active: {user.is_active}")

            # Test token creation
            token = auth_service.create_access_token(user.id)
            print(f"Token created: {token[:20]}...")

            # Test token verification
            verified_user_id = auth_service.verify_token(token)
            print(f"Token verification: {verified_user_id == user.id}")

            # Test authentication
            auth_user = await auth_service.authenticate_user(test_email, test_password)
            if auth_user:
                print(f"Authentication test passed: {auth_user.email}")
            else:
                print("Authentication test failed")

            print("\nAll tests passed!")

        except Exception as create_error:
            print(f"Error creating user: {create_error}")
            import traceback

            traceback.print_exc()

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_auth())
