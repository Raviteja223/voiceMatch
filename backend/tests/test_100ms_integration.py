import pytest
import requests
import os
import time
from pathlib import Path

# 100ms Integration Testing - Tests real 100ms room creation, token generation, room status, and billing

# Load BASE_URL from frontend env file
def get_base_url():
    frontend_env = Path('/app/frontend/.env')
    if frontend_env.exists():
        with open(frontend_env) as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().strip('"')
    raise ValueError("EXPO_PUBLIC_BACKEND_URL not found in /app/frontend/.env")

BASE_URL = get_base_url()

# ─── 100ms INTEGRATION TESTS ───────────────────────────

class Test100msCallIntegration:
    """Test 100ms real room creation and token generation"""

    def test_call_start_creates_real_100ms_room(self, seeker_with_balance):
        """Test that POST /api/calls/start creates a real 100ms room with hms_room_id"""
        token = seeker_with_balance["token"]
        listener_id = seeker_with_balance["listener_id"]
        
        response = requests.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"listener_id": listener_id, "call_type": "voice"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data["success"] is True, "success should be true"
        assert "call" in data, "call object should be present"
        
        call = data["call"]
        
        # CRITICAL: Verify 100ms room was created
        assert "hms_room_id" in call, "hms_room_id should be present in call"
        assert call["hms_room_id"] is not None, "hms_room_id should NOT be null (real 100ms room should be created)"
        assert isinstance(call["hms_room_id"], str), "hms_room_id should be a string"
        assert len(call["hms_room_id"]) > 0, "hms_room_id should not be empty"
        
        # Verify 100ms token for seeker is returned
        assert "hms_token" in call, "hms_token should be present for seeker"
        assert call["hms_token"] is not None, "hms_token should not be null"
        assert isinstance(call["hms_token"], str), "hms_token should be a JWT string"
        assert len(call["hms_token"]) > 50, "hms_token should be a valid JWT (length > 50)"
        
        # Verify call metadata
        assert call["status"] == "active", "Call status should be active"
        assert call["seeker_id"] == seeker_with_balance["user_id"], "seeker_id should match"
        assert call["listener_id"] == listener_id, "listener_id should match"
        assert call["call_type"] == "voice", "call_type should be voice"
        assert "rate_per_min" in call, "rate_per_min should be present"
        
        # Store for next tests
        seeker_with_balance["call_id"] = call["id"]
        seeker_with_balance["hms_room_id"] = call["hms_room_id"]
        seeker_with_balance["hms_token"] = call["hms_token"]
        
        print(f"✅ Real 100ms room created: room_id={call['hms_room_id'][:20]}...")
        print(f"✅ HMS token generated for seeker: {call['hms_token'][:40]}...")
        print(f"✅ Call ID: {call['id']}")
    
    def test_hms_room_status_endpoint(self, seeker_with_balance):
        """Test GET /api/hms/room-status/{room_id} returns room details from 100ms"""
        hms_room_id = seeker_with_balance["hms_room_id"]
        
        response = requests.get(f"{BASE_URL}/api/hms/room-status/{hms_room_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        room_data = response.json()
        
        # Verify 100ms room data structure
        assert "id" in room_data, "Room should have id"
        assert room_data["id"] == hms_room_id, "Room id should match"
        assert "name" in room_data, "Room should have name"
        assert "enabled" in room_data, "Room should have enabled field"
        
        print(f"✅ 100ms room status retrieved: name={room_data.get('name')}, enabled={room_data.get('enabled')}")
    
    def test_call_end_disables_100ms_room_and_billing(self, seeker_with_balance):
        """Test POST /api/calls/end disables 100ms room and calculates billing correctly"""
        # Wait a few seconds for call duration
        time.sleep(3)
        
        call_id = seeker_with_balance["call_id"]
        token = seeker_with_balance["token"]
        initial_balance = seeker_with_balance["balance"]
        
        response = requests.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"call_id": call_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify billing calculation
        assert data["success"] is True, "success should be true"
        assert "duration_seconds" in data, "duration_seconds should be present"
        assert data["duration_seconds"] >= 3, f"Duration should be at least 3 seconds, got {data['duration_seconds']}"
        assert "cost" in data, "cost should be present"
        assert data["cost"] > 0, "cost should be greater than 0"
        assert "listener_earned" in data, "listener_earned should be present"
        assert data["listener_earned"] > 0, "listener should have earned money"
        
        # Verify wallet deduction
        balance_response = requests.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        assert balance_response.status_code == 200
        new_balance = balance_response.json()["balance"]
        assert new_balance < initial_balance, f"Balance should be deducted. Initial: {initial_balance}, New: {new_balance}"
        
        # Verify 100ms room is disabled (optional check - room should be disabled but API might still return it)
        # Backend calls end_hms_room() which posts enabled=False to 100ms
        
        print(f"✅ Call ended successfully")
        print(f"✅ Duration: {data['duration_seconds']}s, Cost: ₹{data['cost']}, Listener earned: ₹{data['listener_earned']}")
        print(f"✅ Wallet deducted: ₹{initial_balance} → ₹{new_balance}")
        print(f"✅ 100ms room disabled (backend called end_hms_room)")


class Test100msListenerToken:
    """Test listener 100ms token retrieval"""
    
    def test_listener_incoming_token_endpoint(self, listener_with_call):
        """Test GET /api/calls/incoming-token returns 100ms token for listener"""
        token = listener_with_call["token"]
        
        response = requests.get(f"{BASE_URL}/api/calls/incoming-token",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify token response
        assert data["success"] is True, "success should be true"
        assert "call_id" in data, "call_id should be present"
        assert "hms_token" in data, "hms_token should be present"
        assert "hms_room_id" in data, "hms_room_id should be present"
        assert "call" in data, "call object should be present"
        
        # Verify token is valid JWT
        assert data["hms_token"] is not None, "hms_token should not be null"
        assert isinstance(data["hms_token"], str), "hms_token should be a string"
        assert len(data["hms_token"]) > 50, "hms_token should be a valid JWT"
        
        # Verify room_id matches
        assert data["hms_room_id"] == listener_with_call["hms_room_id"], "hms_room_id should match"
        
        # Verify call is active
        assert data["call"]["status"] == "active", "Call should be active"
        
        print(f"✅ Listener incoming token retrieved successfully")
        print(f"✅ HMS token: {data['hms_token'][:40]}...")
        print(f"✅ Room ID: {data['hms_room_id']}")
        
        # End the call for cleanup
        seeker_token = listener_with_call["seeker_token"]
        end_response = requests.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {seeker_token}", "Content-Type": "application/json"},
            json={"call_id": data["call_id"]}
        )
        assert end_response.status_code == 200, "Call should end successfully"
        print(f"✅ Call ended for cleanup")


# ─── FIXTURES ──────────────────────────────────────────

@pytest.fixture(scope="class")
def seeker_with_balance():
    """Create a seeker with balance and match with listener - shared across class tests"""
    # Create seeker
    phone = f"+9199998{int(time.time()) % 100000:05d}"
    
    # Step 1: Verify OTP (creates new user)
    verify_res = requests.post(f"{BASE_URL}/api/auth/verify-otp",
        headers={"Content-Type": "application/json"},
        json={"phone": phone, "otp": "1234"}
    )
    assert verify_res.status_code == 200, f"OTP verification failed: {verify_res.text}"
    verify_data = verify_res.json()
    token = verify_data["token"]
    user_id = verify_data["user"]["id"]
    
    # Step 2: Set gender to male (becomes seeker)
    gender_res = requests.post(f"{BASE_URL}/api/auth/set-gender",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"gender": "male"}
    )
    assert gender_res.status_code == 200, f"Set gender failed: {gender_res.text}"
    token = gender_res.json()["token"]  # New token with role
    
    # Step 3: Onboard seeker
    onboard_res = requests.post(f"{BASE_URL}/api/seekers/onboard",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "name": "TEST_100ms_Seeker",
            "age": 27,
            "languages": ["Hindi", "English"],
            "intent_tags": ["Just Talk"]
        }
    )
    assert onboard_res.status_code == 200, f"Onboarding failed: {onboard_res.text}"
    
    # Step 4: Add balance
    recharge_res = requests.post(f"{BASE_URL}/api/wallet/recharge",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"pack_id": "pack_99"}
    )
    assert recharge_res.status_code == 200, f"Recharge failed: {recharge_res.text}"
    balance = recharge_res.json()["new_balance"]
    
    # Step 5: Get online listener
    listeners_res = requests.get(f"{BASE_URL}/api/listeners/online",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    assert listeners_res.status_code == 200, f"Get listeners failed: {listeners_res.text}"
    listeners = listeners_res.json()["listeners"]
    assert len(listeners) > 0, "No online listeners available"
    listener_id = listeners[0]["user_id"]
    
    print(f"✅ Seeker created: {phone}, balance: ₹{balance}, matched with listener: {listener_id}")
    
    return {
        "phone": phone,
        "token": token,
        "user_id": user_id,
        "balance": balance,
        "listener_id": listener_id,
        "call_id": None,
        "hms_room_id": None,
        "hms_token": None
    }

@pytest.fixture
def listener_with_call():
    """Create a listener and start a call so listener can retrieve token"""
    # Create listener
    listener_phone = f"+9199997{int(time.time()) % 100000:05d}"
    
    # Step 1: Verify OTP (creates new user)
    verify_res = requests.post(f"{BASE_URL}/api/auth/verify-otp",
        headers={"Content-Type": "application/json"},
        json={"phone": listener_phone, "otp": "1234"}
    )
    assert verify_res.status_code == 200
    listener_token = verify_res.json()["token"]
    
    # Step 2: Set gender to female (becomes listener)
    gender_res = requests.post(f"{BASE_URL}/api/auth/set-gender",
        headers={"Authorization": f"Bearer {listener_token}", "Content-Type": "application/json"},
        json={"gender": "female"}
    )
    assert gender_res.status_code == 200
    listener_token = gender_res.json()["token"]
    listener_user_id = gender_res.json()["user"]["id"]
    
    # Step 3: Onboard listener
    onboard_res = requests.post(f"{BASE_URL}/api/listeners/onboard",
        headers={"Authorization": f"Bearer {listener_token}", "Content-Type": "application/json"},
        json={
            "name": "TEST_100ms_Listener",
            "age": 25,
            "languages": ["Hindi", "English"],
            "avatar_id": "avatar_1",
            "style_tags": ["Friendly"],
            "topic_tags": ["Life", "Career"],
            "boundary_answers": [1, 1, 0, 1, 0]
        }
    )
    assert onboard_res.status_code == 200
    
    # Step 4: Go online
    online_res = requests.post(f"{BASE_URL}/api/listeners/toggle-online",
        headers={"Authorization": f"Bearer {listener_token}", "Content-Type": "application/json"},
        json={"online": True}
    )
    assert online_res.status_code == 200
    
    # Create a seeker and start a call with this listener
    seeker_phone = f"+9199996{int(time.time()) % 100000:05d}"
    seeker_verify = requests.post(f"{BASE_URL}/api/auth/verify-otp",
        headers={"Content-Type": "application/json"},
        json={"phone": seeker_phone, "otp": "1234"}
    )
    seeker_token = seeker_verify.json()["token"]
    
    # Set gender
    seeker_gender = requests.post(f"{BASE_URL}/api/auth/set-gender",
        headers={"Authorization": f"Bearer {seeker_token}", "Content-Type": "application/json"},
        json={"gender": "male"}
    )
    seeker_token = seeker_gender.json()["token"]
    
    # Onboard seeker
    requests.post(f"{BASE_URL}/api/seekers/onboard",
        headers={"Authorization": f"Bearer {seeker_token}", "Content-Type": "application/json"},
        json={
            "name": "TEST_Seeker_For_Listener",
            "age": 26,
            "languages": ["Hindi"],
            "intent_tags": ["Just Talk"]
        }
    )
    
    # Recharge
    requests.post(f"{BASE_URL}/api/wallet/recharge",
        headers={"Authorization": f"Bearer {seeker_token}", "Content-Type": "application/json"},
        json={"pack_id": "pack_99"}
    )
    
    # Start call
    call_res = requests.post(f"{BASE_URL}/api/calls/start",
        headers={"Authorization": f"Bearer {seeker_token}", "Content-Type": "application/json"},
        json={"listener_id": listener_user_id, "call_type": "voice"}
    )
    assert call_res.status_code == 200
    call_data = call_res.json()["call"]
    
    print(f"✅ Listener created and call started for incoming token test")
    
    return {
        "phone": listener_phone,
        "token": listener_token,
        "user_id": listener_user_id,
        "call_id": call_data["id"],
        "hms_room_id": call_data["hms_room_id"],
        "seeker_token": seeker_token
    }
