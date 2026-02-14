import pytest
import requests
import os
from pathlib import Path

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

# ─── TESTS FOR NEW GENDER-BASED AUTH FLOW ───────────────────────────

class TestNewAuthFlow:
    """Test new login flow: phone → OTP → gender selection (new users) or auto-route (returning users)"""

    def test_verify_otp_new_user_needs_gender(self, api_client):
        """Test that new users get needs_gender=true after OTP verification"""
        # Use a unique phone number that doesn't exist yet
        test_phone = "+919999999991"
        
        response = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True, "success should be true"
        assert "token" in data, "token should be present"
        assert "user" in data, "user should be present"
        assert data["needs_gender"] is True, "needs_gender should be True for new users"
        assert data["user"]["role"] == "", "role should be empty for new users"
        assert data["user"]["onboarded"] is False, "onboarded should be False"
        
        print(f"✅ New user needs_gender=true, user_id={data['user']['id']}")
        return data
    
    def test_verify_otp_returning_listener_no_gender_needed(self, api_client):
        """Test that returning listener (+919876543200 Priya) auto-routes without gender selection"""
        # This is a seeded listener from backend startup
        response = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": "+919876543200",
            "otp": "1234"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["needs_gender"] is False, "Returning user should have needs_gender=False"
        assert data["user"]["role"] == "listener", "Returning user should have role=listener"
        assert data["user"]["name"] == "Priya", "User should be Priya"
        
        print(f"✅ Returning listener auto-routes, needs_gender=false, role=listener")
        return data


class TestSetGenderEndpoint:
    """Test /auth/set-gender endpoint that sets role based on gender"""
    
    def test_set_gender_male_becomes_seeker(self, api_client):
        """Test that selecting male sets role to seeker"""
        # Create new user
        test_phone = "+919999999992"
        verify_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        assert verify_res.status_code == 200
        token = verify_res.json()["token"]
        
        # Set gender to male
        response = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {token}"},
            json={"gender": "male"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data, "New token should be returned"
        assert data["user"]["gender"] == "male"
        assert data["user"]["role"] == "seeker", "Male should become seeker"
        
        print(f"✅ Male gender → seeker role assigned")
        return data
    
    def test_set_gender_female_becomes_listener(self, api_client):
        """Test that selecting female sets role to listener"""
        # Create new user
        test_phone = "+919999999993"
        verify_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        assert verify_res.status_code == 200
        token = verify_res.json()["token"]
        
        # Set gender to female
        response = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {token}"},
            json={"gender": "female"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["user"]["gender"] == "female"
        assert data["user"]["role"] == "listener", "Female should become listener"
        
        print(f"✅ Female gender → listener role assigned")
        return data
    
    def test_set_gender_invalid(self, api_client):
        """Test that invalid gender is rejected"""
        # Create new user
        test_phone = "+919999999994"
        verify_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        token = verify_res.json()["token"]
        
        # Try invalid gender
        response = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {token}"},
            json={"gender": "other"}
        )
        assert response.status_code == 400, "Invalid gender should return 400"
        print(f"✅ Invalid gender properly rejected")


class TestCompleteFlows:
    """Test complete user flows from login to onboarding"""
    
    def test_new_seeker_flow_male_gender(self, api_client):
        """Test complete flow: login → gender(male) → seeker onboarding"""
        # Step 1: New user login
        test_phone = "+919999999995"
        verify_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["needs_gender"] is True
        token = data["token"]
        
        # Step 2: Set gender to male (becomes seeker)
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {token}"},
            json={"gender": "male"}
        )
        assert gender_res.status_code == 200
        token = gender_res.json()["token"]  # Use new token with role
        assert gender_res.json()["user"]["role"] == "seeker"
        
        # Step 3: Complete seeker onboarding
        onboard_res = api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_Male_Seeker",
                "age": 26,
                "languages": ["Hindi", "English"],
                "intent_tags": ["Career", "Life"]
            }
        )
        assert onboard_res.status_code == 200
        assert onboard_res.json()["success"] is True
        
        print(f"✅ Complete seeker flow: login → male gender → seeker onboarding")
    
    def test_new_listener_flow_female_gender(self, api_client):
        """Test complete flow: login → gender(female) → listener onboarding"""
        # Step 1: New user login
        test_phone = "+919999999996"
        verify_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": test_phone,
            "otp": "1234"
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["needs_gender"] is True
        token = data["token"]
        
        # Step 2: Set gender to female (becomes listener)
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {token}"},
            json={"gender": "female"}
        )
        assert gender_res.status_code == 200
        token = gender_res.json()["token"]
        assert gender_res.json()["user"]["role"] == "listener"
        
        # Step 3: Get avatars for listener onboarding
        avatars_res = api_client.get(f"{BASE_URL}/api/avatars")
        assert avatars_res.status_code == 200
        avatars = avatars_res.json()["avatars"]
        avatar_id = avatars[0]["id"] if avatars else "avatar_1"
        
        # Step 4: Complete listener onboarding
        onboard_res = api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_Female_Listener",
                "age": 24,
                "languages": ["Hindi", "English"],
                "avatar_id": avatar_id,
                "style_tags": ["Friendly", "Calm"],
                "topic_tags": ["Life", "Career", "Relationships"],
                "boundary_answers": [1, 1, 0, 1, 0]
            }
        )
        assert onboard_res.status_code == 200
        assert onboard_res.json()["success"] is True
        
        print(f"✅ Complete listener flow: login → female gender → listener onboarding")


# ─── FIXTURES ───────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
