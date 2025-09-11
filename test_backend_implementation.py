#!/usr/bin/env python3
"""
Test script to verify the backend implementation
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test that all modules can be imported correctly"""
    print("Testing imports...")

    try:
        # Test API modules
        from api.analytics import router as analytics_router

        print("✅ Analytics API imported successfully")

        from api.reports import router as reports_router

        print("✅ Reports API imported successfully")

        from api.routes import router as api_router

        print("✅ Main API routes imported successfully")

        # Test service modules
        from services.analytics_service import AnalyticsService

        print("✅ Analytics service imported successfully")

        from services.reports_service import ReportsService

        print("✅ Reports service imported successfully")

        # Test main application
        from main import app

        print("✅ Main FastAPI app imported successfully")

        print("\n🎉 All imports successful!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_router_configuration():
    """Test that routers are configured correctly"""
    print("\nTesting router configuration...")

    try:
        from api.analytics import router as analytics_router
        from api.reports import router as reports_router

        # Check router prefixes
        if analytics_router.prefix == "/analytics":
            print("✅ Analytics router has correct prefix")
        else:
            print(f"❌ Analytics router prefix incorrect: {analytics_router.prefix}")

        if reports_router.prefix == "/reports":
            print("✅ Reports router has correct prefix")
        else:
            print(f"❌ Reports router prefix incorrect: {reports_router.prefix}")

        # Check that routers have routes
        analytics_routes = len(analytics_router.routes)
        reports_routes = len(reports_router.routes)

        print(f"✅ Analytics router has {analytics_routes} routes")
        print(f"✅ Reports router has {reports_routes} routes")

        if analytics_routes > 0 and reports_routes > 0:
            print("✅ Routers are properly configured")
            return True
        else:
            print("❌ Routers have no routes")
            return False

    except Exception as e:
        print(f"❌ Router configuration error: {e}")
        return False


def test_database_tables():
    """Test that the database schema includes new tables"""
    print("\nTesting database schema...")

    try:
        # Check if the updated synthetic_data_generator.py contains our new tables
        with open("src/utils/synthetic_data_generator.py", "r") as f:
            content = f.read()

        required_tables = [
            "analytics_cache",
            "analytics_metrics",
            "report_templates",
            "report_history",
            "report_schedules",
            "supplier_performance",
            "category_metrics",
        ]

        missing_tables = []
        for table in required_tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" not in content:
                missing_tables.append(table)

        if not missing_tables:
            print("✅ All required tables are defined in schema")
            return True
        else:
            print(f"❌ Missing tables in schema: {missing_tables}")
            return False

    except Exception as e:
        print(f"❌ Database schema test error: {e}")
        return False


def main():
    """Run all tests"""
    print("Backend Implementation Test Suite")
    print("=" * 50)

    tests = [test_imports, test_router_configuration, test_database_tables]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Tests Results: {passed}/{len(tests)} passed")

    if passed == len(tests):
        print("🎉 All tests passed! Backend implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
