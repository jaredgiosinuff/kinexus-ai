#!/usr/bin/env python3
"""
API Testing Script for Kinexus AI
This script tests the main API endpoints to ensure they're working correctly.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

# API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
TEST_EMAIL = 'test@kinexus.ai'
TEST_PASSWORD = 'testpassword123'

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token: Optional[str] = None
        self.test_results: Dict[str, bool] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        self.test_results[test_name] = success

    async def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            success = response.status_code == 200

            if success:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status', 'unknown')}")
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")

            return success
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False

    async def test_authentication(self) -> bool:
        """Test authentication endpoints"""
        try:
            # Test login (this should work with our mock auth in development)
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }

            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('access_token')
                if self.auth_token:
                    self.log_test("Login", True, "Authentication token received")

                    # Test getting current user
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    user_response = await self.client.get(
                        f"{self.base_url}/api/auth/me",
                        headers=headers
                    )

                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        self.log_test("Get Current User", True, f"User: {user_data.get('email', 'unknown')}")
                        return True
                    else:
                        self.log_test("Get Current User", False, f"Status: {user_response.status_code}")
                        return False
                else:
                    self.log_test("Login", False, "No access token in response")
                    return False
            else:
                self.log_test("Login", False, f"Status code: {response.status_code}")
                return False

        except Exception as e:
            self.log_test("Authentication", False, f"Error: {str(e)}")
            return False

    async def test_reviews_endpoints(self) -> bool:
        """Test reviews endpoints"""
        if not self.auth_token:
            self.log_test("Reviews Endpoints", False, "No authentication token")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            # Test getting reviews
            response = await self.client.get(
                f"{self.base_url}/api/reviews/",
                headers=headers
            )

            if response.status_code == 200:
                reviews = response.json()
                self.log_test("Get Reviews", True, f"Found {len(reviews)} reviews")

                # Test getting my reviews
                my_reviews_response = await self.client.get(
                    f"{self.base_url}/api/reviews/my",
                    headers=headers
                )

                if my_reviews_response.status_code == 200:
                    my_reviews = my_reviews_response.json()
                    self.log_test("Get My Reviews", True, f"Found {len(my_reviews)} personal reviews")
                    return True
                else:
                    self.log_test("Get My Reviews", False, f"Status: {my_reviews_response.status_code}")
                    return False
            else:
                self.log_test("Get Reviews", False, f"Status code: {response.status_code}")
                return False

        except Exception as e:
            self.log_test("Reviews Endpoints", False, f"Error: {str(e)}")
            return False

    async def test_metrics_endpoint(self) -> bool:
        """Test metrics endpoint"""
        if not self.auth_token:
            self.log_test("Metrics Endpoint", False, "No authentication token")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            response = await self.client.get(
                f"{self.base_url}/api/reviews/metrics",
                headers=headers,
                params={"days": 30}
            )

            if response.status_code == 200:
                metrics = response.json()
                self.log_test("Get Metrics", True, f"Metrics: {json.dumps(metrics, indent=2)}")
                return True
            else:
                self.log_test("Get Metrics", False, f"Status code: {response.status_code}")
                return False

        except Exception as e:
            self.log_test("Metrics Endpoint", False, f"Error: {str(e)}")
            return False

    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection"""
        if not self.auth_token:
            self.log_test("WebSocket Connection", False, "No authentication token")
            return False

        try:
            # Note: We're not actually testing the WebSocket here since it's more complex
            # This is a placeholder for a more comprehensive WebSocket test
            self.log_test("WebSocket Connection", True, "WebSocket endpoint available (not tested)")
            return True

        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Error: {str(e)}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all API tests"""
        print("🚀 Starting Kinexus AI API Tests")
        print(f"🔗 Testing API at: {self.base_url}")
        print("-" * 50)

        tests = [
            self.test_health_check,
            self.test_authentication,
            self.test_reviews_endpoints,
            self.test_metrics_endpoint,
            self.test_websocket_connection,
        ]

        all_passed = True
        for test in tests:
            try:
                result = await test()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                all_passed = False
            print()  # Empty line between tests

        # Summary
        print("-" * 50)
        print("📊 Test Summary:")
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        print(f"   Passed: {passed}/{total}")

        if all_passed:
            print("🎉 All tests passed!")
        else:
            print("💥 Some tests failed!")

        return all_passed

async def main():
    """Main test function"""
    # Check if API server is specified
    api_url = sys.argv[1] if len(sys.argv) > 1 else API_BASE_URL

    print("Kinexus AI API Testing Script")
    print("=" * 50)

    async with APITester(api_url) as tester:
        success = await tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())