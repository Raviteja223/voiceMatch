#!/usr/bin/env python3
"""
Backend API Testing for Voice Companionship Platform
Tests authentication, KYC, listener heartbeat, and referral systems
"""

import requests
import json
import time
from datetime import datetime

# Use the production URL from frontend/.env
BASE_URL = "https://talkbuddies-1.preview.emergentagent.com/api"

class VoiceCompanionshipTester:
    def __init__(self):
        self.seeker_token = None
        self.listener_token = None
        self.seeker_user_id = None
        self.listener_user_id = None
        self.seeker_referral_code = None
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def test_auth_flow(self):
        """Test complete authentication flow"""
        self.log("=== Testing Authentication Flow ===")
        
        # Test 1: Send OTP for seeker (male)
        self.log("1. Testing send-otp for seeker...")
        response = requests.post(f"{BASE_URL}/auth/send-otp", 
                               json={"phone": "9876543210"})
        
        if response.status_code != 200:
            self.log(f"❌ Send OTP failed: {response.status_code} - {response.text}")
            return False
            
        self.log("✅ Send OTP successful")
        
        # Test 2: Verify OTP for seeker
        self.log("2. Testing verify-otp for seeker...")
        response = requests.post(f"{BASE_URL}/auth/verify-otp",
                               json={"phone": "9876543210", "otp": "1234"})
        
        if response.status_code != 200:
            self.log(f"❌ Verify OTP failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if not data.get("needs_gender"):
            self.log(f"❌ Expected needs_gender=true for new user")
            return False
            
        temp_token = data.get("token")
        self.seeker_user_id = data.get("user", {}).get("id")
        self.log("✅ Verify OTP successful, needs gender selection")
        
        # Test 3: Set gender to male (becomes seeker)
        self.log("3. Testing set-gender to male...")
        response = requests.post(f"{BASE_URL}/auth/set-gender",
                               json={"gender": "male"},
                               headers={"Authorization": f"Bearer {temp_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Set gender failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        self.seeker_token = data.get("token")
        user = data.get("user", {})
        
        if user.get("role") != "seeker" or user.get("gender") != "male":
            self.log(f"❌ Expected role=seeker, gender=male, got role={user.get('role')}, gender={user.get('gender')}")
            return False
            
        self.log("✅ Set gender successful, user is now seeker")
        
        # Test 4: Register listener (female)
        self.log("4. Testing listener registration...")
        
        # Send OTP for listener
        response = requests.post(f"{BASE_URL}/auth/send-otp", 
                               json={"phone": "9876543211"})
        if response.status_code != 200:
            self.log(f"❌ Listener send OTP failed: {response.status_code}")
            return False
            
        # Verify OTP for listener
        response = requests.post(f"{BASE_URL}/auth/verify-otp",
                               json={"phone": "9876543211", "otp": "1234"})
        if response.status_code != 200:
            self.log(f"❌ Listener verify OTP failed: {response.status_code}")
            return False
            
        data = response.json()
        temp_listener_token = data.get("token")
        self.listener_user_id = data.get("user", {}).get("id")
        
        # Set gender to female (becomes listener)
        response = requests.post(f"{BASE_URL}/auth/set-gender",
                               json={"gender": "female"},
                               headers={"Authorization": f"Bearer {temp_listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Listener set gender failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        self.listener_token = data.get("token")
        user = data.get("user", {})
        
        if user.get("role") != "listener" or user.get("gender") != "female":
            self.log(f"❌ Expected listener role=listener, gender=female, got role={user.get('role')}, gender={user.get('gender')}")
            return False
            
        self.log("✅ Listener registration successful")
        return True
        
    def test_kyc_system(self):
        """Test KYC submission and status endpoints"""
        self.log("=== Testing KYC System ===")
        
        if not self.listener_token:
            self.log("❌ No listener token available for KYC testing")
            return False
            
        # Test 1: Get initial KYC status
        self.log("1. Testing initial KYC status...")
        response = requests.get(f"{BASE_URL}/kyc/status",
                              headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ KYC status failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if data.get("status") != "pending":
            self.log(f"❌ Expected initial status=pending, got {data.get('status')}")
            return False
            
        self.log("✅ Initial KYC status is pending")
        
        # Test 2: Submit KYC data
        self.log("2. Testing KYC submission...")
        kyc_data = {
            "full_name": "Priya Sharma",
            "aadhaar_last4": "1234",
            "dob": "1995-06-15",
            "pan_number": "ABCDE1234F"
        }
        
        response = requests.post(f"{BASE_URL}/kyc/submit",
                               json=kyc_data,
                               headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ KYC submission failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if data.get("status") != "submitted":
            self.log(f"❌ Expected status=submitted after submission, got {data.get('status')}")
            return False
            
        self.log("✅ KYC submission successful")
        
        # Test 3: Get updated KYC status
        self.log("3. Testing updated KYC status...")
        response = requests.get(f"{BASE_URL}/kyc/status",
                              headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Updated KYC status failed: {response.status_code}")
            return False
            
        data = response.json()
        if data.get("status") != "submitted":
            self.log(f"❌ Expected updated status=submitted, got {data.get('status')}")
            return False
            
        self.log("✅ Updated KYC status is submitted")
        return True
        
    def test_listener_heartbeat_system(self):
        """Test listener heartbeat, go-offline, and profile endpoints"""
        self.log("=== Testing Listener Heartbeat System ===")
        
        if not self.listener_token:
            self.log("❌ No listener token available for heartbeat testing")
            return False
            
        # Test 1: Listener heartbeat (auto-online)
        self.log("1. Testing listener heartbeat...")
        response = requests.post(f"{BASE_URL}/listeners/heartbeat",
                               headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Listener heartbeat failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if not data.get("online"):
            self.log(f"❌ Expected online=true after heartbeat, got {data.get('online')}")
            return False
            
        self.log("✅ Listener heartbeat successful, now online")
        
        # Test 2: Get listener profile (should include kyc_status)
        self.log("2. Testing listener profile...")
        response = requests.get(f"{BASE_URL}/listeners/profile",
                              headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Listener profile failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if "kyc_status" not in data:
            self.log(f"❌ Listener profile missing kyc_status field")
            return False
            
        if not data.get("is_online"):
            self.log(f"❌ Expected is_online=true after heartbeat, got {data.get('is_online')}")
            return False
            
        self.log(f"✅ Listener profile retrieved, kyc_status: {data.get('kyc_status')}, online: {data.get('is_online')}")
        
        # Test 3: Go offline
        self.log("3. Testing go offline...")
        response = requests.post(f"{BASE_URL}/listeners/go-offline",
                               headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Go offline failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if data.get("online"):
            self.log(f"❌ Expected online=false after go-offline, got {data.get('online')}")
            return False
            
        self.log("✅ Go offline successful")
        
        # Test 4: Verify profile shows offline
        self.log("4. Verifying profile shows offline...")
        response = requests.get(f"{BASE_URL}/listeners/profile",
                              headers={"Authorization": f"Bearer {self.listener_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Profile check failed: {response.status_code}")
            return False
            
        data = response.json()
        if data.get("is_online"):
            self.log(f"❌ Expected is_online=false after go-offline, got {data.get('is_online')}")
            return False
            
        self.log("✅ Profile correctly shows offline status")
        return True
        
    def test_seeker_referral_system(self):
        """Test seeker referral code generation and application"""
        self.log("=== Testing Seeker Referral System ===")
        
        if not self.seeker_token:
            self.log("❌ No seeker token available for referral testing")
            return False
            
        # Test 1: Get seeker's referral code
        self.log("1. Testing get seeker referral code...")
        response = requests.get(f"{BASE_URL}/seeker-referral/my-code",
                              headers={"Authorization": f"Bearer {self.seeker_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Get seeker referral code failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        self.seeker_referral_code = data.get("code")
        
        if not self.seeker_referral_code:
            self.log(f"❌ No referral code returned")
            return False
            
        self.log(f"✅ Seeker referral code generated: {self.seeker_referral_code}")
        
        # Test 2: Create another seeker to apply the referral code
        self.log("2. Creating second seeker to test referral application...")
        
        # Register second seeker
        response = requests.post(f"{BASE_URL}/auth/send-otp", 
                               json={"phone": "9876543212"})
        if response.status_code != 200:
            self.log(f"❌ Second seeker send OTP failed: {response.status_code}")
            return False
            
        response = requests.post(f"{BASE_URL}/auth/verify-otp",
                               json={"phone": "9876543212", "otp": "1234"})
        if response.status_code != 200:
            self.log(f"❌ Second seeker verify OTP failed: {response.status_code}")
            return False
            
        data = response.json()
        temp_token2 = data.get("token")
        
        response = requests.post(f"{BASE_URL}/auth/set-gender",
                               json={"gender": "male"},
                               headers={"Authorization": f"Bearer {temp_token2}"})
        if response.status_code != 200:
            self.log(f"❌ Second seeker set gender failed: {response.status_code}")
            return False
            
        data = response.json()
        seeker2_token = data.get("token")
        
        # Test 3: Apply referral code
        self.log("3. Testing referral code application...")
        response = requests.post(f"{BASE_URL}/seeker-referral/apply",
                               json={"referral_code": self.seeker_referral_code},
                               headers={"Authorization": f"Bearer {seeker2_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Referral code application failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if not data.get("success"):
            self.log(f"❌ Referral application not successful")
            return False
            
        self.log("✅ Referral code application successful")
        
        # Test 4: Verify original seeker got credits
        self.log("4. Verifying original seeker received referral credits...")
        response = requests.get(f"{BASE_URL}/seeker-referral/my-code",
                              headers={"Authorization": f"Bearer {self.seeker_token}"})
        
        if response.status_code != 200:
            self.log(f"❌ Check referral stats failed: {response.status_code}")
            return False
            
        data = response.json()
        if data.get("total_referrals") < 1:
            self.log(f"❌ Expected at least 1 referral, got {data.get('total_referrals')}")
            return False
            
        if data.get("credited_referrals") < 1:
            self.log(f"❌ Expected at least 1 credited referral, got {data.get('credited_referrals')}")
            return False
            
        self.log(f"✅ Referral stats updated: {data.get('total_referrals')} total, {data.get('credited_referrals')} credited")
        return True
        
    def test_invalid_scenarios(self):
        """Test error handling and invalid scenarios"""
        self.log("=== Testing Invalid Scenarios ===")
        
        # Test 1: Invalid OTP
        self.log("1. Testing invalid OTP...")
        response = requests.post(f"{BASE_URL}/auth/verify-otp",
                               json={"phone": "9876543213", "otp": "0000"})
        
        if response.status_code == 200:
            self.log(f"❌ Invalid OTP should fail but got success")
            return False
            
        self.log("✅ Invalid OTP correctly rejected")
        
        # Test 2: KYC without authentication
        self.log("2. Testing KYC without authentication...")
        response = requests.post(f"{BASE_URL}/kyc/submit",
                               json={"full_name": "Test", "aadhaar_last4": "1234", "dob": "1990-01-01"})
        
        if response.status_code == 200:
            self.log(f"❌ KYC without auth should fail but got success")
            return False
            
        self.log("✅ KYC without authentication correctly rejected")
        
        # Test 3: Seeker trying to access listener endpoints
        if self.seeker_token:
            self.log("3. Testing seeker accessing listener endpoints...")
            response = requests.post(f"{BASE_URL}/listeners/heartbeat",
                                   headers={"Authorization": f"Bearer {self.seeker_token}"})
            
            if response.status_code == 200:
                self.log(f"❌ Seeker accessing listener endpoint should fail")
                return False
                
            self.log("✅ Seeker correctly blocked from listener endpoints")
            
        # Test 4: Invalid referral code
        if self.seeker_token:
            self.log("4. Testing invalid referral code...")
            response = requests.post(f"{BASE_URL}/seeker-referral/apply",
                                   json={"referral_code": "INVALID123"},
                                   headers={"Authorization": f"Bearer {self.seeker_token}"})
            
            if response.status_code == 200:
                self.log(f"❌ Invalid referral code should fail")
                return False
                
            self.log("✅ Invalid referral code correctly rejected")
            
        return True
        
    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting Voice Companionship Platform Backend Tests")
        self.log(f"Testing against: {BASE_URL}")
        
        results = {
            "auth_flow": False,
            "kyc_system": False,
            "listener_heartbeat": False,
            "seeker_referral": False,
            "invalid_scenarios": False
        }
        
        try:
            results["auth_flow"] = self.test_auth_flow()
            results["kyc_system"] = self.test_kyc_system()
            results["listener_heartbeat"] = self.test_listener_heartbeat_system()
            results["seeker_referral"] = self.test_seeker_referral_system()
            results["invalid_scenarios"] = self.test_invalid_scenarios()
            
        except Exception as e:
            self.log(f"❌ Test execution error: {str(e)}")
            
        # Summary
        self.log("\n" + "="*50)
        self.log("TEST RESULTS SUMMARY")
        self.log("="*50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
                
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 All tests passed!")
            return True
        else:
            self.log("⚠️  Some tests failed - check logs above")
            return False

if __name__ == "__main__":
    tester = VoiceCompanionshipTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)