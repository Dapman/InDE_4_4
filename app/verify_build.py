#!/usr/bin/env python3
"""
InDE v3.1 - Build Verification Script
Verifies that all modules can be imported and basic functionality works.
"""

import sys
import os

# Set up the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_result(name, success, error=None):
    """Print test result."""
    if success:
        print(f"  [PASS] {name}")
        return True
    else:
        print(f"  [FAIL] {name}")
        if error:
            print(f"         Error: {error}")
        return False

def main():
    """Run verification tests."""
    print("=" * 60)
    print("InDE v3.1 Build Verification")
    print("=" * 60)

    passed = 0
    failed = 0

    # Test 1: Core Config
    print("\n[Core Imports]")
    try:
        from core.config import VERSION, VERSION_NAME, MATURITY_LEVELS
        if VERSION == "3.5.1" and "Federation Protocol" in VERSION_NAME:
            if test_result("core.config", True):
                passed += 1
        else:
            if not test_result("core.config", False, f"VERSION={VERSION}"):
                failed += 1
    except Exception as e:
        if not test_result("core.config", False, str(e)):
            failed += 1

    # Test 2: Database
    try:
        from core.database import Database
        if test_result("core.database", True):
            passed += 1
    except Exception as e:
        if not test_result("core.database", False, str(e)):
            failed += 1

    # Test 3: LLM Interface
    try:
        from core.llm_interface import LLMInterface
        if test_result("core.llm_interface", True):
            passed += 1
    except Exception as e:
        if not test_result("core.llm_interface", False, str(e)):
            failed += 1

    # Test 4: Auth Password
    print("\n[Auth Imports]")
    try:
        from auth.password import hash_password, verify_password
        if test_result("auth.password", True):
            passed += 1
    except Exception as e:
        if not test_result("auth.password", False, str(e)):
            failed += 1

    # Test 5: Auth JWT
    try:
        from auth.jwt_handler import create_access_token, verify_access_token
        if test_result("auth.jwt_handler", True):
            passed += 1
    except Exception as e:
        if not test_result("auth.jwt_handler", False, str(e)):
            failed += 1

    # Test 6: Auth Middleware
    try:
        from auth.middleware import get_current_user
        if test_result("auth.middleware", True):
            passed += 1
    except Exception as e:
        if not test_result("auth.middleware", False, str(e)):
            failed += 1

    # Test 7: Events
    print("\n[Events Imports]")
    try:
        from events.dispatcher import EventDispatcher, emit_event
        from events.schemas import DomainEvent, PursuitCreatedEvent
        if test_result("events.dispatcher + schemas", True):
            passed += 1
    except Exception as e:
        if not test_result("events.dispatcher + schemas", False, str(e)):
            failed += 1

    # Test 8: Maturity
    print("\n[Feature Imports]")
    try:
        from maturity.model import MaturityCalculator
        if test_result("maturity.model", True):
            passed += 1
    except Exception as e:
        if not test_result("maturity.model", False, str(e)):
            failed += 1

    # Test 9: Crisis
    try:
        from crisis.manager import CrisisManager
        if test_result("crisis.manager", True):
            passed += 1
    except Exception as e:
        if not test_result("crisis.manager", False, str(e)):
            failed += 1

    # Test 10: GII
    try:
        from gii.manager import GIIManager
        if test_result("gii.manager", True):
            passed += 1
    except Exception as e:
        if not test_result("gii.manager", False, str(e)):
            failed += 1

    # Test 11: API Routes
    print("\n[API Routes]")
    try:
        from api import auth, pursuits, coaching, maturity, crisis
        if test_result("api routes (5 modules)", True):
            passed += 1
    except Exception as e:
        if not test_result("api routes", False, str(e)):
            failed += 1

    # Test 12: Password Hashing
    print("\n[Functionality Tests]")
    try:
        from auth.password import hash_password, verify_password
        pw = "test123"
        hashed = hash_password(pw)
        if verify_password(pw, hashed) and not verify_password("wrong", hashed):
            if test_result("password hashing", True):
                passed += 1
        else:
            if not test_result("password hashing", False, "verification failed"):
                failed += 1
    except Exception as e:
        if not test_result("password hashing", False, str(e)):
            failed += 1

    # Test 13: JWT Tokens
    try:
        from auth.jwt_handler import create_access_token, verify_access_token
        token = create_access_token("test_user", "test@example.com", "NOVICE")
        claims = verify_access_token(token)
        if claims["user_id"] == "test_user":
            if test_result("JWT tokens", True):
                passed += 1
        else:
            if not test_result("JWT tokens", False, "claims mismatch"):
                failed += 1
    except Exception as e:
        if not test_result("JWT tokens", False, str(e)):
            failed += 1

    # Test 14: Event Dispatcher
    try:
        from events.dispatcher import EventDispatcher
        from events.schemas import PursuitCreatedEvent

        dispatcher = EventDispatcher(db=None, persist=False)
        handled = []
        dispatcher.register("pursuit.created", lambda e: handled.append(e))

        event = PursuitCreatedEvent(user_id="test", pursuit_id="test")
        dispatcher.emit(event)

        if len(handled) == 1:
            if test_result("event dispatcher", True):
                passed += 1
        else:
            if not test_result("event dispatcher", False, f"expected 1 event, got {len(handled)}"):
                failed += 1
    except Exception as e:
        if not test_result("event dispatcher", False, str(e)):
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} tests passed")
    if failed > 0:
        print(f"         {failed} tests failed")
        return 1
    else:
        print("All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
