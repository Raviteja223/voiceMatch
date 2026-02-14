import pytest
import requests
import os
import time
from pathlib import Path

# Load BASE_URL from frontend env file
def get_base_url():
    frontend_env = Path('/app/frontend/.env')
    if frontend_env.exists():
        with open(frontend_env) as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().strip('"')
    return 'https://voicematch-21.preview.emergentagent.com'

BASE_URL = get_base_url()

# ─── AUTH & ONBOARDING TESTS ───────────────────────────

class TestAuthFlow:
    """Test authentication and user creation"""

    def test_send_otp(self, api_client):
        """Test OTP sending (mocked)"""
        response = api_client.post(f"{BASE_URL}/api/auth/send-otp", json={
            "phone": "+919876543210"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "mocked" in data["message"].lower()
        print("✓ OTP send API working")

    def test_verify_otp_invalid(self, api_client):
        """Test invalid OTP rejection"""
        response = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": "+919876543210",
            "otp": "9999",
            "role": "seeker"
        })
        assert response.status_code == 400
        print("✓ Invalid OTP properly rejected")

    def test_verify_otp_seeker_new_user(self, api_client, seeker_test_data):
        """Test OTP verification for new seeker user"""
        response = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": seeker_test_data["phone"],
            "otp": "1234",
            "role": "seeker"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["user"]["role"] == "seeker"
        assert data["user"]["onboarded"] is False
        seeker_test_data["token"] = data["token"]
        seeker_test_data["user_id"] = data["user"]["id"]
        print(f"✓ Seeker user created with ID: {data['user']['id']}")

    def test_verify_otp_listener_new_user(self, api_client, listener_test_data):
        """Test OTP verification for new listener user"""
        response = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": listener_test_data["phone"],
            "otp": "1234",
            "role": "listener"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["user"]["role"] == "listener"
        listener_test_data["token"] = data["token"]
        listener_test_data["user_id"] = data["user"]["id"]
        print(f"✓ Listener user created with ID: {data['user']['id']}")


class TestSeekerOnboarding:
    """Test seeker onboarding flow"""

    def test_seeker_onboard_no_auth(self, api_client):
        """Test onboarding requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/seekers/onboard", json={
            "name": "Test Seeker",
            "age": 25,
            "languages": ["Hindi", "English"],
            "intent_tags": ["Just Talk", "Career Advice"]
        })
        assert response.status_code == 401
        print("✓ Seeker onboarding properly requires auth")

    def test_seeker_onboard_success(self, api_client, seeker_test_data):
        """Test successful seeker onboarding"""
        response = api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"},
            json={
                "name": "TEST_Seeker_User",
                "age": 25,
                "languages": ["Hindi", "English"],
                "intent_tags": ["Just Talk", "Career Advice"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["welcome_credits"] == 50
        print(f"✓ Seeker onboarded with {data['welcome_credits']} welcome credits")

    def test_seeker_profile_get(self, api_client, seeker_test_data):
        """Test fetching seeker profile after onboarding"""
        response = api_client.get(f"{BASE_URL}/api/seekers/profile",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        profile = response.json()
        assert profile["name"] == "TEST_Seeker_User"
        assert profile["age"] == 25
        assert "Hindi" in profile["languages"]
        assert "Just Talk" in profile["intent_tags"]
        print("✓ Seeker profile retrieved successfully")

    def test_wallet_balance_after_onboarding(self, api_client, seeker_test_data):
        """Test wallet has welcome bonus after onboarding"""
        response = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] >= 50
        seeker_test_data["balance"] = data["balance"]
        print(f"✓ Wallet balance: ₹{data['balance']}")


class TestListenerOnboarding:
    """Test listener onboarding flow"""

    def test_listener_onboard_success(self, api_client, listener_test_data):
        """Test successful listener onboarding"""
        response = api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {listener_test_data['token']}"},
            json={
                "name": "TEST_Listener_User",
                "age": 24,
                "languages": ["Hindi", "English"],
                "avatar_id": "avatar_1",
                "style_tags": ["Friendly", "Calm"],
                "topic_tags": ["Life", "Career", "Stress"],
                "boundary_answers": [1, 1, 0, 1, 0]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print("✓ Listener onboarded successfully")

    def test_listener_profile_get(self, api_client, listener_test_data):
        """Test fetching listener profile after onboarding"""
        response = api_client.get(f"{BASE_URL}/api/listeners/profile",
            headers={"Authorization": f"Bearer {listener_test_data['token']}"}
        )
        assert response.status_code == 200
        profile = response.json()
        assert profile["name"] == "TEST_Listener_User"
        assert profile["is_online"] is False
        assert profile["tier"] == "new"
        print("✓ Listener profile retrieved successfully")

    def test_listener_toggle_online(self, api_client, listener_test_data):
        """Test listener can go online"""
        response = api_client.post(f"{BASE_URL}/api/listeners/toggle-online",
            headers={"Authorization": f"Bearer {listener_test_data['token']}"},
            json={"online": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["online"] is True
        print("✓ Listener toggled online")


# ─── LISTENER DISCOVERY TESTS ──────────────────────────

class TestListenerDiscovery:
    """Test listener listing and matching"""

    def test_get_online_listeners(self, api_client, seeker_test_data):
        """Test fetching online listeners"""
        response = api_client.get(f"{BASE_URL}/api/listeners/online",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "listeners" in data
        assert len(data["listeners"]) > 0  # Should have seeded + test listener
        listener = data["listeners"][0]
        assert "name" in listener
        assert "avatar_id" in listener
        assert "languages" in listener
        assert "style_tags" in listener
        assert listener["is_online"] is True
        print(f"✓ Found {len(data['listeners'])} online listeners")

    def test_get_all_listeners(self, api_client):
        """Test fetching all listeners (no auth required for browsing)"""
        response = api_client.get(f"{BASE_URL}/api/listeners/all")
        assert response.status_code == 200
        data = response.json()
        assert "listeners" in data
        assert len(data["listeners"]) >= 8  # At least 8 seeded listeners
        print(f"✓ Total {len(data['listeners'])} listeners in system")

    def test_talk_now_matching(self, api_client, seeker_test_data):
        """Test Talk Now auto-matching"""
        response = api_client.post(f"{BASE_URL}/api/match/talk-now",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "listener" in data
        matched_listener = data["listener"]
        assert "user_id" in matched_listener
        assert "name" in matched_listener
        seeker_test_data["matched_listener_id"] = matched_listener["user_id"]
        print(f"✓ Matched with listener: {matched_listener['name']}")


# ─── WALLET & RECHARGE TESTS ───────────────────────────

class TestWalletAndRecharge:
    """Test wallet operations"""

    def test_wallet_recharge_pack_99(self, api_client, seeker_test_data):
        """Test recharge with pack_99"""
        response = api_client.post(f"{BASE_URL}/api/wallet/recharge",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"},
            json={"pack_id": "pack_99"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_balance"] > seeker_test_data["balance"]
        old_balance = seeker_test_data["balance"]
        seeker_test_data["balance"] = data["new_balance"]
        print(f"✓ Recharged ₹99: {old_balance} → {data['new_balance']}")

    def test_wallet_transactions_history(self, api_client, seeker_test_data):
        """Test fetching transaction history"""
        response = api_client.get(f"{BASE_URL}/api/wallet/transactions",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) >= 2  # Welcome + recharge
        txn = data["transactions"][0]
        assert "type" in txn
        assert "amount" in txn
        assert "description" in txn
        print(f"✓ Found {len(data['transactions'])} transactions")


# ─── CALL FLOW TESTS ───────────────────────────────────

class TestCallFlow:
    """Test voice call lifecycle"""

    def test_start_call_insufficient_balance(self, api_client):
        """Test call start fails with zero balance"""
        # Create a new user with no balance
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": "+919999999999",
            "otp": "1234",
            "role": "seeker"
        })
        token = auth_res.json()["token"]
        
        response = api_client.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"listener_id": "test_listener_id", "call_type": "voice"}
        )
        assert response.status_code == 400
        print("✓ Call start properly rejected for insufficient balance")

    def test_start_call_success(self, api_client, seeker_test_data):
        """Test starting a call"""
        listener_id = seeker_test_data.get("matched_listener_id", "test_listener")
        response = api_client.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"},
            json={"listener_id": listener_id, "call_type": "voice"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "call" in data
        call = data["call"]
        assert call["status"] == "active"
        assert "id" in call
        assert "rate_per_min" in call
        seeker_test_data["call_id"] = call["id"]
        seeker_test_data["call_rate"] = call["rate_per_min"]
        print(f"✓ Call started with ID: {call['id']}, Rate: ₹{call['rate_per_min']}/min")

    def test_end_call_success(self, api_client, seeker_test_data):
        """Test ending a call and cost calculation"""
        # Wait a few seconds to simulate call duration
        time.sleep(3)
        
        response = api_client.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"},
            json={"call_id": seeker_test_data["call_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "duration_seconds" in data
        assert data["duration_seconds"] >= 3
        assert "cost" in data
        assert data["cost"] > 0
        assert "listener_earned" in data
        seeker_test_data["call_duration"] = data["duration_seconds"]
        seeker_test_data["call_cost"] = data["cost"]
        print(f"✓ Call ended: {data['duration_seconds']}s, Cost: ₹{data['cost']}, Listener earned: ₹{data['listener_earned']}")

    def test_wallet_deducted_after_call(self, api_client, seeker_test_data):
        """Test wallet balance deducted after call"""
        response = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        new_balance = response.json()["balance"]
        assert new_balance < seeker_test_data["balance"]
        print(f"✓ Wallet deducted: {seeker_test_data['balance']} → {new_balance}")

    def test_call_history(self, api_client, seeker_test_data):
        """Test fetching call history"""
        response = api_client.get(f"{BASE_URL}/api/calls/history",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "calls" in data
        assert len(data["calls"]) > 0
        call = data["calls"][0]
        assert call["id"] == seeker_test_data["call_id"]
        assert call["status"] == "ended"
        print(f"✓ Call history retrieved: {len(data['calls'])} calls")


# ─── RATING TESTS ──────────────────────────────────────

class TestRatings:
    """Test call rating submission"""

    def test_submit_rating(self, api_client, seeker_test_data):
        """Test submitting a call rating"""
        response = api_client.post(f"{BASE_URL}/api/ratings/submit",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"},
            json={
                "call_id": seeker_test_data["call_id"],
                "rating": "great",
                "feedback": "Wonderful conversation!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print("✓ Rating submitted successfully")


# ─── LISTENER EARNINGS TESTS ───────────────────────────

class TestListenerEarnings:
    """Test listener earnings dashboard"""

    def test_earnings_dashboard(self, api_client, listener_test_data):
        """Test fetching listener earnings"""
        response = api_client.get(f"{BASE_URL}/api/earnings/dashboard",
            headers={"Authorization": f"Bearer {listener_test_data['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "earnings" in data
        earnings = data["earnings"]
        assert "total_earned" in earnings
        assert "pending_balance" in earnings
        assert "withdrawn" in earnings
        print(f"✓ Earnings: Total ₹{earnings['total_earned']}, Pending ₹{earnings['pending_balance']}")

    def test_withdraw_below_minimum(self, api_client, listener_test_data):
        """Test withdrawal fails below ₹1000 minimum"""
        response = api_client.post(f"{BASE_URL}/api/earnings/withdraw",
            headers={"Authorization": f"Bearer {listener_test_data['token']}"},
            json={"amount": 100, "upi_id": "test@upi"}
        )
        assert response.status_code == 400
        print("✓ Withdrawal properly rejected below ₹1000 minimum")


# ─── ADMIN PANEL TESTS ─────────────────────────────────

class TestAdminPanel:
    """Test admin dashboard endpoints"""

    def test_admin_dashboard(self, api_client):
        """Test admin dashboard stats (no auth required in MVP)"""
        response = api_client.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_seekers" in data
        assert "total_listeners" in data
        assert "online_listeners" in data
        assert "total_calls" in data
        assert "revenue" in data
        assert data["total_users"] > 0
        print(f"✓ Admin dashboard: {data['total_users']} users, {data['total_calls']} calls, ₹{data['revenue']} revenue")

    def test_moderation_queue(self, api_client):
        """Test moderation queue endpoint"""
        response = api_client.get(f"{BASE_URL}/api/admin/moderation-queue")
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        print(f"✓ Moderation queue: {len(data['reports'])} pending reports")


# ─── MISC API TESTS ────────────────────────────────────

class TestMiscAPIs:
    """Test miscellaneous endpoints"""

    def test_get_avatars(self, api_client):
        """Test fetching avatar list"""
        response = api_client.get(f"{BASE_URL}/api/avatars")
        assert response.status_code == 200
        data = response.json()
        assert "avatars" in data
        assert len(data["avatars"]) == 8
        avatar = data["avatars"][0]
        assert "id" in avatar
        assert "name" in avatar
        assert "image" in avatar
        print(f"✓ Found {len(data['avatars'])} avatars")

    def test_get_current_user(self, api_client, seeker_test_data):
        """Test /users/me endpoint"""
        response = api_client.get(f"{BASE_URL}/api/users/me",
            headers={"Authorization": f"Bearer {seeker_test_data['token']}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["id"] == seeker_test_data["user_id"]
        assert user["role"] == "seeker"
        print(f"✓ Current user endpoint working: {user['name']}")


# ─── FIXTURES ──────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def seeker_test_data():
    """Shared seeker test data across tests"""
    return {
        "phone": "+919876543210",
        "token": None,
        "user_id": None,
        "balance": 0,
        "matched_listener_id": None,
        "call_id": None,
        "call_rate": 0,
        "call_duration": 0,
        "call_cost": 0
    }

@pytest.fixture(scope="session")
def listener_test_data():
    """Shared listener test data across tests"""
    return {
        "phone": "+919876543211",
        "token": None,
        "user_id": None
    }
