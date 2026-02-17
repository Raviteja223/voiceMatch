import pytest
import requests
import os
import time
from pathlib import Path

# Backend API testing: Zero balance onboarding, new billing logic (≤5s free), referral system

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

# ─── ZERO BALANCE WALLET TESTS ────────────────────────

class TestZeroBalanceOnboarding:
    """Test seeker onboarding creates wallet with ₹0 balance (no welcome bonus)"""

    def test_seeker_onboard_zero_balance(self, api_client):
        """Test seeker onboarding creates wallet with ₹0 balance"""
        # Create new seeker
        phone = "+919111111111"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        assert auth_res.status_code == 200
        auth_data = auth_res.json()
        
        # Set gender to male (becomes seeker)
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_data['token']}"},
            json={"gender": "male"}
        )
        assert gender_res.status_code == 200
        token = gender_res.json()["token"]
        
        # Onboard seeker
        onboard_res = api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_ZeroBalance_Seeker",
                "age": 25,
                "languages": ["Hindi", "English"],
                "intent_tags": ["Just Talk"]
            }
        )
        assert onboard_res.status_code == 200
        onboard_data = onboard_res.json()
        assert onboard_data["success"] is True
        
        # Check wallet balance - should be ₹0 (no welcome bonus)
        balance_res = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert balance_res.status_code == 200
        balance = balance_res.json()["balance"]
        assert balance == 0, f"Expected ₹0 balance, got ₹{balance}"
        print(f"✓ Seeker onboarded with ₹0 balance (no welcome bonus)")

    def test_wallet_transactions_no_welcome_credit(self, api_client):
        """Test wallet transactions show no welcome credit"""
        # Create and onboard seeker
        phone = "+919111111112"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_res.json()['token']}"},
            json={"gender": "male"}
        )
        token = gender_res.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_TxnCheck_Seeker",
                "age": 26,
                "languages": ["Hindi"],
                "intent_tags": ["Career"]
            }
        )
        
        # Check transactions - should be empty or no welcome credit
        txn_res = api_client.get(f"{BASE_URL}/api/wallet/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert txn_res.status_code == 200
        txns = txn_res.json()["transactions"]
        
        # Should have no welcome credit transaction
        welcome_txns = [t for t in txns if "welcome" in t.get("description", "").lower()]
        assert len(welcome_txns) == 0, f"Found unexpected welcome credit transaction"
        print(f"✓ No welcome credit transaction found (expected)")


# ─── NEW BILLING LOGIC TESTS (≤5s free, >5s full minute) ──────────────────

class TestNewBillingLogic:
    """Test new billing: FREE if ≤5 seconds, full first minute + per-second after 60s"""

    def test_call_under_5_seconds_free(self, api_client):
        """Test calls ≤5 seconds are FREE (cost = 0)"""
        # Create seeker with balance
        phone = "+919222222221"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_res.json()['token']}"},
            json={"gender": "male"}
        )
        token = gender_res.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_5SecCall_Seeker",
                "age": 27,
                "languages": ["Hindi"],
                "intent_tags": ["Fun"]
            }
        )
        
        # Recharge wallet
        api_client.post(f"{BASE_URL}/api/wallet/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={"pack_id": "pack_99"}
        )
        
        balance_before = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        # Get online listener
        listeners_res = api_client.get(f"{BASE_URL}/api/listeners/online",
            headers={"Authorization": f"Bearer {token}"}
        )
        listeners = listeners_res.json()["listeners"]
        assert len(listeners) > 0, "No online listeners available"
        listener_id = listeners[0]["user_id"]
        
        # Start call
        call_res = api_client.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"listener_id": listener_id, "call_type": "voice"}
        )
        assert call_res.status_code == 200
        call_id = call_res.json()["call"]["id"]
        
        # Wait 3 seconds (under 5 seconds threshold)
        time.sleep(3)
        
        # End call
        end_res = api_client.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {token}"},
            json={"call_id": call_id}
        )
        assert end_res.status_code == 200
        end_data = end_res.json()
        
        # Cost should be ₹0 for calls under 5 seconds
        assert end_data["cost"] == 0, f"Expected cost=0 for {end_data['duration_seconds']}s call, got ₹{end_data['cost']}"
        
        # Balance should remain unchanged
        balance_after = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        assert balance_after == balance_before, f"Balance changed from ₹{balance_before} to ₹{balance_after} for free call"
        print(f"✓ Call under 5 seconds (3s) = FREE (cost=0, balance unchanged)")

    def test_call_6_seconds_charges_full_minute(self, api_client):
        """Test calls >5 seconds charge full first minute (not pro-rated)"""
        # Create seeker with balance
        phone = "+919222222222"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_res.json()['token']}"},
            json={"gender": "male"}
        )
        token = gender_res.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_6SecCall_Seeker",
                "age": 28,
                "languages": ["Hindi"],
                "intent_tags": ["Chat"]
            }
        )
        
        # Recharge wallet
        api_client.post(f"{BASE_URL}/api/wallet/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={"pack_id": "pack_99"}
        )
        
        balance_before = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        # Get online listener
        listeners_res = api_client.get(f"{BASE_URL}/api/listeners/online",
            headers={"Authorization": f"Bearer {token}"}
        )
        listeners = listeners_res.json()["listeners"]
        listener_id = listeners[0]["user_id"]
        
        # Start call
        call_res = api_client.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"listener_id": listener_id, "call_type": "voice"}
        )
        call_id = call_res.json()["call"]["id"]
        rate = call_res.json()["call"]["rate_per_min"]
        is_first_call = call_res.json()["call"].get("is_first_call", False)
        
        # Wait 6 seconds (over 5 seconds, but under 60)
        time.sleep(6)
        
        # End call
        end_res = api_client.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {token}"},
            json={"call_id": call_id}
        )
        end_data = end_res.json()
        
        # For calls >5s but <60s: should charge full first minute
        expected_cost = 1.0 if is_first_call else rate  # First call discount or normal rate
        assert end_data["cost"] == expected_cost, f"Expected cost=₹{expected_cost} for 6s call, got ₹{end_data['cost']}"
        
        # Balance should be deducted
        balance_after = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        assert balance_after == balance_before - expected_cost, f"Balance deduction mismatch"
        print(f"✓ Call 6 seconds charged full first minute: ₹{expected_cost} (rate={rate}/min, first_call={is_first_call})")

    def test_call_over_60_seconds_per_second_billing(self, api_client):
        """Test calls >60 seconds charge first minute + per-second after"""
        # Create seeker with balance
        phone = "+919222222223"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_res.json()['token']}"},
            json={"gender": "male"}
        )
        token = gender_res.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_90SecCall_Seeker",
                "age": 29,
                "languages": ["Hindi"],
                "intent_tags": ["Life"]
            }
        )
        
        # Recharge wallet
        api_client.post(f"{BASE_URL}/api/wallet/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={"pack_id": "pack_299"}
        )
        
        balance_before = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        # Get online listener
        listeners_res = api_client.get(f"{BASE_URL}/api/listeners/online",
            headers={"Authorization": f"Bearer {token}"}
        )
        listeners = listeners_res.json()["listeners"]
        listener_id = listeners[0]["user_id"]
        
        # Start call
        call_res = api_client.post(f"{BASE_URL}/api/calls/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"listener_id": listener_id, "call_type": "voice"}
        )
        call_id = call_res.json()["call"]["id"]
        rate = call_res.json()["call"]["rate_per_min"]
        is_first_call = call_res.json()["call"].get("is_first_call", False)
        
        # Wait 65 seconds (over 60 seconds)
        time.sleep(65)
        
        # End call
        end_res = api_client.post(f"{BASE_URL}/api/calls/end",
            headers={"Authorization": f"Bearer {token}"},
            json={"call_id": call_id}
        )
        end_data = end_res.json()
        duration = end_data["duration_seconds"]
        
        # Calculate expected cost: full first minute + per-second after 60s
        if is_first_call:
            # First call: ₹1 for first minute + ((duration - 60) / 60) * 1
            expected_cost = 1.0 + ((duration - 60) / 60) * 1.0
        else:
            # Normal: rate for first minute + ((duration - 60) / 60) * rate
            expected_cost = rate + ((duration - 60) / 60) * rate
        expected_cost = round(expected_cost, 2)
        
        assert end_data["cost"] == expected_cost, f"Expected cost=₹{expected_cost} for {duration}s call, got ₹{end_data['cost']}"
        
        # Balance should be deducted
        balance_after = api_client.get(f"{BASE_URL}/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        ).json()["balance"]
        
        assert abs((balance_before - balance_after) - expected_cost) < 0.01, f"Balance deduction mismatch"
        print(f"✓ Call {duration}s charged: ₹{end_data['cost']} (first minute + per-second, rate={rate}/min)")


# ─── REFERRAL SYSTEM TESTS ─────────────────────────────

class TestReferralSystem:
    """Test listener referral system with tiers and commission"""

    def test_referral_my_code_generation(self, api_client):
        """Test GET /api/referral/my-code generates unique code for listener"""
        # Create listener
        phone = "+919333333331"
        auth_res = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender_res = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth_res.json()['token']}"},
            json={"gender": "female"}
        )
        token = gender_res.json()["token"]
        
        # Onboard listener
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_RefCode_Listener",
                "age": 24,
                "languages": ["Hindi"],
                "avatar_id": "avatar_1",
                "style_tags": ["Friendly"],
                "topic_tags": ["Life"],
                "boundary_answers": [1, 1, 0, 1, 0]
            }
        )
        
        # Get referral code
        ref_res = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ref_res.status_code == 200
        ref_data = ref_res.json()
        
        # Verify response structure
        assert "code" in ref_data
        assert len(ref_data["code"]) > 0
        assert "tier" in ref_data
        assert ref_data["tier"] == "bronze"  # New listener starts at bronze
        assert "bonus_per_referral" in ref_data
        assert ref_data["bonus_per_referral"] == 200  # Bronze tier bonus
        assert "commission_rate" in ref_data
        assert ref_data["commission_rate"] == "5%"  # Bronze tier commission
        assert "total_referrals" in ref_data
        assert "active_referrals" in ref_data
        assert "pending_referrals" in ref_data
        
        print(f"✓ Referral code generated: {ref_data['code']} (tier={ref_data['tier']}, bonus=₹{ref_data['bonus_per_referral']}, commission={ref_data['commission_rate']})")
        
        return token, ref_data["code"]

    def test_referral_apply_code_success(self, api_client):
        """Test POST /api/referral/apply allows listener to apply another's code"""
        # Create referrer listener
        phone1 = "+919333333332"
        auth1 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone1,
            "otp": "1234"
        })
        gender1 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth1.json()['token']}"},
            json={"gender": "female"}
        )
        token1 = gender1.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "name": "TEST_Referrer",
                "age": 25,
                "languages": ["Hindi"],
                "avatar_id": "avatar_2",
                "style_tags": ["Calm"],
                "topic_tags": ["Career"],
                "boundary_answers": [1, 0, 1, 0, 1]
            }
        )
        
        # Get referral code
        ref1 = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token1}"}
        ).json()
        referral_code = ref1["code"]
        
        # Create referred listener
        phone2 = "+919333333333"
        auth2 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone2,
            "otp": "1234"
        })
        gender2 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth2.json()['token']}"},
            json={"gender": "female"}
        )
        token2 = gender2.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "name": "TEST_Referred",
                "age": 23,
                "languages": ["English"],
                "avatar_id": "avatar_3",
                "style_tags": ["Funny"],
                "topic_tags": ["Fun"],
                "boundary_answers": [1, 1, 1, 0, 0]
            }
        )
        
        # Apply referral code
        apply_res = api_client.post(f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {token2}"},
            json={"referral_code": referral_code}
        )
        assert apply_res.status_code == 200
        apply_data = apply_res.json()
        assert apply_data["success"] is True
        assert "message" in apply_data
        assert "30 minutes" in apply_data["message"].lower()
        
        print(f"✓ Referral code {referral_code} applied successfully")

    def test_referral_self_referral_prevention(self, api_client):
        """Test POST /api/referral/apply prevents self-referral"""
        # Create listener
        phone = "+919333333334"
        auth = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth.json()['token']}"},
            json={"gender": "female"}
        )
        token = gender.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_SelfRef",
                "age": 26,
                "languages": ["Hindi"],
                "avatar_id": "avatar_4",
                "style_tags": ["Caring"],
                "topic_tags": ["Health"],
                "boundary_answers": [1, 0, 0, 1, 1]
            }
        )
        
        # Get own referral code
        ref = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        own_code = ref["code"]
        
        # Try to apply own code
        apply_res = api_client.post(f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {token}"},
            json={"referral_code": own_code}
        )
        assert apply_res.status_code == 400
        assert "own" in apply_res.json()["detail"].lower()
        
        print(f"✓ Self-referral prevented (cannot use own code)")

    def test_referral_duplicate_application_prevention(self, api_client):
        """Test POST /api/referral/apply prevents duplicate applications"""
        # Create referrer
        phone1 = "+919333333335"
        auth1 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone1,
            "otp": "1234"
        })
        gender1 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth1.json()['token']}"},
            json={"gender": "female"}
        )
        token1 = gender1.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "name": "TEST_RefDup1",
                "age": 27,
                "languages": ["Tamil"],
                "avatar_id": "avatar_5",
                "style_tags": ["Motivating"],
                "topic_tags": ["Study"],
                "boundary_answers": [0, 1, 1, 0, 1]
            }
        )
        
        code1 = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token1}"}
        ).json()["code"]
        
        # Create second referrer
        phone2 = "+919333333336"
        auth2 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone2,
            "otp": "1234"
        })
        gender2 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth2.json()['token']}"},
            json={"gender": "female"}
        )
        token2 = gender2.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "name": "TEST_RefDup2",
                "age": 22,
                "languages": ["Bengali"],
                "avatar_id": "avatar_6",
                "style_tags": ["Spiritual"],
                "topic_tags": ["Life"],
                "boundary_answers": [1, 1, 0, 0, 1]
            }
        )
        
        code2 = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token2}"}
        ).json()["code"]
        
        # Create referred listener
        phone3 = "+919333333337"
        auth3 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone3,
            "otp": "1234"
        })
        gender3 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth3.json()['token']}"},
            json={"gender": "female"}
        )
        token3 = gender3.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token3}"},
            json={
                "name": "TEST_RefDupUser",
                "age": 24,
                "languages": ["Marathi"],
                "avatar_id": "avatar_7",
                "style_tags": ["Friendly"],
                "topic_tags": ["Movies"],
                "boundary_answers": [0, 0, 1, 1, 0]
            }
        )
        
        # Apply first referral code
        apply1 = api_client.post(f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {token3}"},
            json={"referral_code": code1}
        )
        assert apply1.status_code == 200
        
        # Try to apply second referral code (should fail - duplicate)
        apply2 = api_client.post(f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {token3}"},
            json={"referral_code": code2}
        )
        assert apply2.status_code == 400
        assert "already" in apply2.json()["detail"].lower()
        
        print(f"✓ Duplicate referral application prevented")

    def test_referral_my_referrals_list(self, api_client):
        """Test GET /api/referral/my-referrals returns list of referred listeners"""
        # Create referrer
        phone1 = "+919333333338"
        auth1 = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone1,
            "otp": "1234"
        })
        gender1 = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth1.json()['token']}"},
            json={"gender": "female"}
        )
        token1 = gender1.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "name": "TEST_RefList",
                "age": 28,
                "languages": ["Hindi"],
                "avatar_id": "avatar_8",
                "style_tags": ["Calm"],
                "topic_tags": ["Travel"],
                "boundary_answers": [1, 0, 1, 1, 0]
            }
        )
        
        code = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token1}"}
        ).json()["code"]
        
        # Create 2 referred listeners
        for i in range(2):
            phone = f"+91933333339{i}"
            auth = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
                "phone": phone,
                "otp": "1234"
            })
            gender = api_client.post(f"{BASE_URL}/api/auth/set-gender",
                headers={"Authorization": f"Bearer {auth.json()['token']}"},
                json={"gender": "female"}
            )
            token = gender.json()["token"]
            
            api_client.post(f"{BASE_URL}/api/listeners/onboard",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"TEST_RefUser{i}",
                    "age": 23 + i,
                    "languages": ["English"],
                    "avatar_id": "avatar_1",
                    "style_tags": ["Funny"],
                    "topic_tags": ["Music"],
                    "boundary_answers": [1, 1, 1, 1, 1]
                }
            )
            
            api_client.post(f"{BASE_URL}/api/referral/apply",
                headers={"Authorization": f"Bearer {token}"},
                json={"referral_code": code}
            )
        
        # Get my referrals list
        refs_res = api_client.get(f"{BASE_URL}/api/referral/my-referrals",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert refs_res.status_code == 200
        refs_data = refs_res.json()
        assert "referrals" in refs_data
        assert len(refs_data["referrals"]) == 2
        
        # Check referral structure
        referral = refs_data["referrals"][0]
        assert "id" in referral
        assert "referred_id" in referral
        assert "referred_name" in referral
        assert "status" in referral
        assert referral["status"] == "pending"  # Not activated yet (need 30 min talk time)
        assert "code_used" in referral
        assert referral["code_used"] == code
        
        print(f"✓ Referrals list retrieved: {len(refs_data['referrals'])} referrals (status={referral['status']})")

    def test_referral_invalid_code(self, api_client):
        """Test applying invalid referral code returns 404"""
        # Create listener
        phone = "+919333333340"
        auth = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth.json()['token']}"},
            json={"gender": "female"}
        )
        token = gender.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/listeners/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_InvalidCode",
                "age": 25,
                "languages": ["Hindi"],
                "avatar_id": "avatar_1",
                "style_tags": ["Friendly"],
                "topic_tags": ["Life"],
                "boundary_answers": [1, 1, 0, 1, 0]
            }
        )
        
        # Apply invalid code
        apply_res = api_client.post(f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {token}"},
            json={"referral_code": "INVALID9999"}
        )
        assert apply_res.status_code == 404
        assert "invalid" in apply_res.json()["detail"].lower()
        
        print(f"✓ Invalid referral code properly rejected")

    def test_referral_requires_listener_role(self, api_client):
        """Test referral endpoints require listener role (not seeker)"""
        # Create seeker
        phone = "+919333333341"
        auth = api_client.post(f"{BASE_URL}/api/auth/verify-otp", json={
            "phone": phone,
            "otp": "1234"
        })
        gender = api_client.post(f"{BASE_URL}/api/auth/set-gender",
            headers={"Authorization": f"Bearer {auth.json()['token']}"},
            json={"gender": "male"}
        )
        token = gender.json()["token"]
        
        api_client.post(f"{BASE_URL}/api/seekers/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TEST_SeekerRef",
                "age": 30,
                "languages": ["Hindi"],
                "intent_tags": ["Fun"]
            }
        )
        
        # Try to get referral code as seeker
        ref_res = api_client.get(f"{BASE_URL}/api/referral/my-code",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ref_res.status_code == 403
        assert "listeners only" in ref_res.json()["detail"].lower()
        
        print(f"✓ Referral endpoints properly restricted to listeners only")


# ─── FIXTURES ──────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
