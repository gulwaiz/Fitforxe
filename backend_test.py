#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Gym Management System
Tests all CRUD operations, payment processing, attendance tracking, and dashboard stats
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://f8249600-f57d-4a8e-9aa3-11641ad9f6e0.preview.emergentagent.com/api"

class GymAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_member_id = None
        self.test_payment_id = None
        self.test_attendance_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_api_endpoint(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> Dict[str, Any]:
        """Generic API testing method"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            self.log(f"{method} {endpoint} -> Status: {response.status_code}")
            
            if response.status_code != expected_status:
                self.log(f"Expected status {expected_status}, got {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return {"success": False, "error": f"Status code mismatch", "response": response.text}
                
            try:
                response_data = response.json()
                return {"success": True, "data": response_data, "status_code": response.status_code}
            except json.JSONDecodeError:
                return {"success": True, "data": response.text, "status_code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def test_member_management(self):
        """Test all member management CRUD operations"""
        self.log("=== Testing Member Management APIs ===")
        
        # Test 1: Create a new member
        self.log("Testing member creation...")
        member_data = {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "email": "sarah.johnson@email.com",
            "phone": "+1-555-0123",
            "date_of_birth": "1990-05-15T00:00:00Z",
            "membership_type": "premium",
            "emergency_contact_name": "Mike Johnson",
            "emergency_contact_phone": "+1-555-0124",
            "medical_conditions": "None"
        }
        
        result = self.test_api_endpoint("POST", "/members", member_data, 200)
        if not result["success"]:
            self.log("Member creation failed", "ERROR")
            return False
            
        self.test_member_id = result["data"]["id"]
        self.log(f"Created member with ID: {self.test_member_id}")
        
        # Test 2: Get all members
        self.log("Testing get all members...")
        result = self.test_api_endpoint("GET", "/members")
        if not result["success"]:
            self.log("Get all members failed", "ERROR")
            return False
        
        members = result["data"]
        self.log(f"Retrieved {len(members)} members")
        
        # Test 3: Get specific member
        self.log("Testing get specific member...")
        result = self.test_api_endpoint("GET", f"/members/{self.test_member_id}")
        if not result["success"]:
            self.log("Get specific member failed", "ERROR")
            return False
            
        member = result["data"]
        if member["email"] != member_data["email"]:
            self.log("Member data mismatch", "ERROR")
            return False
        
        # Test 4: Update member
        self.log("Testing member update...")
        update_data = {
            "phone": "+1-555-9999",
            "status": "active"
        }
        
        result = self.test_api_endpoint("PUT", f"/members/{self.test_member_id}", update_data)
        if not result["success"]:
            self.log("Member update failed", "ERROR")
            return False
            
        updated_member = result["data"]
        if updated_member["phone"] != update_data["phone"]:
            self.log("Member update data mismatch", "ERROR")
            return False
        
        # Test 5: Test duplicate email validation
        self.log("Testing duplicate email validation...")
        duplicate_member = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "sarah.johnson@email.com",  # Same email
            "phone": "+1-555-5555",
            "membership_type": "basic"
        }
        
        result = self.test_api_endpoint("POST", "/members", duplicate_member, 400)
        if result["success"]:
            self.log("Duplicate email validation test passed")
        else:
            self.log("Duplicate email validation failed - should have returned 400", "ERROR")
            return False
        
        self.log("Member Management APIs: PASSED")
        return True
    
    def test_payment_management(self):
        """Test payment recording and history APIs"""
        self.log("=== Testing Payment Management APIs ===")
        
        if not self.test_member_id:
            self.log("No test member available for payment testing", "ERROR")
            return False
        
        # Test 1: Record a payment
        self.log("Testing payment recording...")
        payment_data = {
            "member_id": self.test_member_id,
            "amount": 49.99,
            "payment_method": "credit_card",
            "membership_type": "premium",
            "notes": "Monthly membership payment"
        }
        
        result = self.test_api_endpoint("POST", "/payments", payment_data)
        if not result["success"]:
            self.log("Payment recording failed", "ERROR")
            return False
            
        payment = result["data"]
        self.test_payment_id = payment["id"]
        self.log(f"Recorded payment with ID: {self.test_payment_id}")
        
        # Verify payment data
        if payment["amount"] != payment_data["amount"]:
            self.log("Payment amount mismatch", "ERROR")
            return False
            
        if payment["status"] != "paid":
            self.log("Payment status should be 'paid'", "ERROR")
            return False
        
        # Test 2: Get all payments
        self.log("Testing get all payments...")
        result = self.test_api_endpoint("GET", "/payments")
        if not result["success"]:
            self.log("Get all payments failed", "ERROR")
            return False
            
        payments = result["data"]
        self.log(f"Retrieved {len(payments)} payments")
        
        # Test 3: Get member's payment history
        self.log("Testing member payment history...")
        result = self.test_api_endpoint("GET", f"/payments/member/{self.test_member_id}")
        if not result["success"]:
            self.log("Get member payments failed", "ERROR")
            return False
            
        member_payments = result["data"]
        if len(member_payments) == 0:
            self.log("No payments found for member", "ERROR")
            return False
        
        # Test 4: Verify membership extension after payment
        self.log("Verifying membership extension after payment...")
        result = self.test_api_endpoint("GET", f"/members/{self.test_member_id}")
        if not result["success"]:
            self.log("Failed to get member after payment", "ERROR")
            return False
            
        member = result["data"]
        if member["status"] != "active":
            self.log("Member status should be active after payment", "ERROR")
            return False
        
        # Test 5: Test payment for non-existent member
        self.log("Testing payment for non-existent member...")
        invalid_payment = {
            "member_id": str(uuid.uuid4()),
            "amount": 29.99,
            "payment_method": "cash",
            "membership_type": "basic"
        }
        
        result = self.test_api_endpoint("POST", "/payments", invalid_payment, 404)
        if result["success"]:
            self.log("Invalid member payment validation test passed")
        else:
            self.log("Invalid member payment validation failed", "ERROR")
            return False
        
        self.log("Payment Management APIs: PASSED")
        return True
    
    def test_attendance_tracking(self):
        """Test attendance check-in/check-out functionality"""
        self.log("=== Testing Attendance Tracking APIs ===")
        
        if not self.test_member_id:
            self.log("No test member available for attendance testing", "ERROR")
            return False
        
        # Test 1: Check in member
        self.log("Testing member check-in...")
        checkin_data = {
            "member_id": self.test_member_id
        }
        
        result = self.test_api_endpoint("POST", "/attendance/checkin", checkin_data)
        if not result["success"]:
            self.log("Member check-in failed", "ERROR")
            return False
            
        attendance = result["data"]
        self.test_attendance_id = attendance["id"]
        self.log(f"Member checked in with attendance ID: {self.test_attendance_id}")
        
        # Verify attendance data
        if attendance["member_id"] != self.test_member_id:
            self.log("Attendance member ID mismatch", "ERROR")
            return False
            
        if attendance["check_out_time"] is not None:
            self.log("Check-out time should be None for new check-in", "ERROR")
            return False
        
        # Test 2: Test duplicate check-in prevention
        self.log("Testing duplicate check-in prevention...")
        result = self.test_api_endpoint("POST", "/attendance/checkin", checkin_data, 400)
        if not result["success"]:
            self.log("Duplicate check-in prevention test passed")
        else:
            self.log("Duplicate check-in prevention failed", "ERROR")
            return False
        
        # Test 3: Check out member
        self.log("Testing member check-out...")
        result = self.test_api_endpoint("POST", f"/attendance/checkout/{self.test_member_id}")
        if not result["success"]:
            self.log("Member check-out failed", "ERROR")
            return False
        
        self.log("Member checked out successfully")
        
        # Test 4: Get attendance records
        self.log("Testing get attendance records...")
        result = self.test_api_endpoint("GET", "/attendance")
        if not result["success"]:
            self.log("Get attendance records failed", "ERROR")
            return False
            
        attendance_records = result["data"]
        self.log(f"Retrieved {len(attendance_records)} attendance records")
        
        # Test 5: Test check-out without check-in
        self.log("Testing check-out without active check-in...")
        result = self.test_api_endpoint("POST", f"/attendance/checkout/{self.test_member_id}", expected_status=404)
        if not result["success"]:
            self.log("Check-out without check-in validation test passed")
        else:
            self.log("Check-out without check-in validation failed", "ERROR")
            return False
        
        # Test 6: Test check-in for non-existent member
        self.log("Testing check-in for non-existent member...")
        invalid_checkin = {
            "member_id": str(uuid.uuid4())
        }
        
        result = self.test_api_endpoint("POST", "/attendance/checkin", invalid_checkin, 404)
        if not result["success"]:
            self.log("Invalid member check-in validation test passed")
        else:
            self.log("Invalid member check-in validation failed", "ERROR")
            return False
        
        self.log("Attendance Tracking APIs: PASSED")
        return True
    
    def test_dashboard_apis(self):
        """Test dashboard statistics and membership pricing APIs"""
        self.log("=== Testing Dashboard APIs ===")
        
        # Test 1: Get dashboard statistics
        self.log("Testing dashboard statistics...")
        result = self.test_api_endpoint("GET", "/dashboard/stats")
        if not result["success"]:
            self.log("Dashboard statistics failed", "ERROR")
            return False
            
        stats = result["data"]
        required_fields = ["total_members", "active_members", "monthly_revenue", "pending_payments", "todays_checkins"]
        
        for field in required_fields:
            if field not in stats:
                self.log(f"Missing field in dashboard stats: {field}", "ERROR")
                return False
            
            if not isinstance(stats[field], (int, float)):
                self.log(f"Invalid data type for {field}: {type(stats[field])}", "ERROR")
                return False
        
        self.log(f"Dashboard stats: {stats}")
        
        # Verify stats make sense
        if stats["active_members"] > stats["total_members"]:
            self.log("Active members cannot exceed total members", "ERROR")
            return False
        
        # Test 2: Get membership pricing
        self.log("Testing membership pricing...")
        result = self.test_api_endpoint("GET", "/membership-pricing")
        if not result["success"]:
            self.log("Membership pricing failed", "ERROR")
            return False
            
        pricing = result["data"]
        expected_types = ["basic", "premium", "vip"]
        
        for membership_type in expected_types:
            if membership_type not in pricing:
                self.log(f"Missing membership type in pricing: {membership_type}", "ERROR")
                return False
                
            if not isinstance(pricing[membership_type], (int, float)):
                self.log(f"Invalid price type for {membership_type}", "ERROR")
                return False
                
            if pricing[membership_type] <= 0:
                self.log(f"Invalid price for {membership_type}: {pricing[membership_type]}", "ERROR")
                return False
        
        self.log(f"Membership pricing: {pricing}")
        
        self.log("Dashboard APIs: PASSED")
        return True
    
    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        self.log("=== Cleaning up test data ===")
        
        if self.test_member_id:
            self.log("Deleting test member...")
            result = self.test_api_endpoint("DELETE", f"/members/{self.test_member_id}")
            if result["success"]:
                self.log("Test member deleted successfully")
            else:
                self.log("Failed to delete test member", "ERROR")
    
    def run_all_tests(self):
        """Run all backend API tests"""
        self.log("Starting comprehensive backend API testing...")
        self.log(f"Backend URL: {self.base_url}")
        
        test_results = {
            "member_management": False,
            "payment_management": False,
            "attendance_tracking": False,
            "dashboard_apis": False
        }
        
        try:
            # Test member management
            test_results["member_management"] = self.test_member_management()
            
            # Test payment management (requires member)
            if test_results["member_management"]:
                test_results["payment_management"] = self.test_payment_management()
            
            # Test attendance tracking (requires member)
            if test_results["member_management"]:
                test_results["attendance_tracking"] = self.test_attendance_tracking()
            
            # Test dashboard APIs
            test_results["dashboard_apis"] = self.test_dashboard_apis()
            
        except Exception as e:
            self.log(f"Unexpected error during testing: {str(e)}", "ERROR")
        
        finally:
            # Clean up test data
            self.cleanup_test_data()
        
        # Print final results
        self.log("=== FINAL TEST RESULTS ===")
        all_passed = True
        for test_name, passed in test_results.items():
            status = "PASSED" if passed else "FAILED"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
            if not passed:
                all_passed = False
        
        overall_status = "ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"
        self.log(f"Overall Result: {overall_status}")
        
        return test_results

if __name__ == "__main__":
    tester = GymAPITester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)