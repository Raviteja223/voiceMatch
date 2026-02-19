from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import jwt
import random
import httpx
from datetime import datetime, timezone, timedelta
import asyncio
import json
import firebase_admin
from firebase_admin import credentials as fb_credentials, auth as fb_auth

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# ─── FIREBASE ADMIN INIT ─────────────────────────────
_firebase_cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', '')
if _firebase_cred_path and os.path.exists(_firebase_cred_path):
    _fb_cred = fb_credentials.Certificate(_firebase_cred_path)
    firebase_admin.initialize_app(_fb_cred)
elif os.environ.get('FIREBASE_PROJECT_ID'):
    # Initialize without credentials (uses Application Default Credentials)
    firebase_admin.initialize_app(options={'projectId': os.environ['FIREBASE_PROJECT_ID']})
else:
    # Fallback: init with no project — firebase-verify will return 503
    try:
        firebase_admin.initialize_app()
    except Exception:
        pass

JWT_SECRET = "konnectra-secret-key-2024"
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

# 100ms Configuration
HMS_APP_ACCESS_KEY = os.environ.get('HMS_APP_ACCESS_KEY', '')
HMS_APP_SECRET = os.environ.get('HMS_APP_SECRET', '')
HMS_API_BASE = "https://api.100ms.live/v2"

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── MODELS ────────────────────────────────────────────
class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp: str
    role: Optional[str] = None  # optional - determined by gender for new users
    device_id: Optional[str] = None  # Expo device ID for fingerprinting

class SetGenderRequest(BaseModel):
    gender: str  # male or female

class SeekerOnboard(BaseModel):
    name: str
    age: int
    languages: List[str]
    intent_tags: List[str]

class ListenerOnboard(BaseModel):
    name: str
    age: int
    languages: List[str]
    avatar_id: str
    style_tags: List[str]
    topic_tags: List[str]
    boundary_answers: List[int]
    referral_code: Optional[str] = None  # code used to join

class RechargeRequest(BaseModel):
    pack_id: str

class CallStartRequest(BaseModel):
    listener_id: str
    call_type: str = "voice"

class CallAcceptRequest(BaseModel):
    call_id: str

class CallRejectRequest(BaseModel):
    call_id: str

class CallEndRequest(BaseModel):
    call_id: str

class RatingRequest(BaseModel):
    call_id: str
    rating: str  # great, good, okay, bad
    feedback: Optional[str] = None

class ReportRequest(BaseModel):
    reported_user_id: str
    call_id: Optional[str] = None
    reason: str
    details: Optional[str] = None

class WithdrawRequest(BaseModel):
    amount: float
    upi_id: str

class ToggleOnlineRequest(BaseModel):
    online: bool

class ApplyReferralRequest(BaseModel):
    referral_code: str

class SeekerApplyReferralRequest(BaseModel):
    referral_code: str

class KYCSubmitRequest(BaseModel):
    full_name: str
    aadhaar_last4: str  # last 4 digits only
    pan_number: Optional[str] = None
    dob: str  # YYYY-MM-DD

class KYCUploadIDRequest(BaseModel):
    id_type: str  # aadhaar, pan, driving_license
    id_image_base64: str  # base64 encoded image

class KYCSelfieVideoRequest(BaseModel):
    video_base64: str  # base64 encoded video or image frames

class FirebaseAuthRequest(BaseModel):
    firebase_token: str
    phone: str
    device_id: Optional[str] = None

class PushTokenRequest(BaseModel):
    token: str
    platform: str = "expo"

class FavoriteToggleRequest(BaseModel):
    listener_id: str

class TipRequest(BaseModel):
    amount: float

class RematchRequest(BaseModel):
    call_id: str

# ─── HELPERS ───────────────────────────────────────────
def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid.uuid4())

# ─── 100ms HELPERS ─────────────────────────────────────
def generate_hms_management_token():
    """Generate a management token for 100ms REST API calls"""
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    token_id = str(uuid.uuid4())
    payload = {
        "access_key": HMS_APP_ACCESS_KEY,
        "type": "management",
        "version": 2,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": now_ts + 86400,
        "jti": token_id,
    }
    return jwt.encode(payload, HMS_APP_SECRET, algorithm="HS256")

def generate_hms_app_token(room_id: str, user_id: str, role: str = "guest"):
    """Generate an app token for a user to join a 100ms room"""
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    token_id = str(uuid.uuid4())
    payload = {
        "access_key": HMS_APP_ACCESS_KEY,
        "room_id": room_id,
        "user_id": user_id,
        "role": role,
        "type": "app",
        "version": 2,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": now_ts + 3600,
        "jti": token_id,
    }
    return jwt.encode(payload, HMS_APP_SECRET, algorithm="HS256")

async def create_hms_room(room_name: str):
    """Create a new 100ms room via REST API"""
    try:
        mgmt_token = generate_hms_management_token()
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.post(
                f"{HMS_API_BASE}/rooms",
                json={"name": room_name, "description": f"VoiceMatch call room", "region": "in"},
                headers={"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
            )
            if response.status_code in (200, 201):
                data = response.json()
                logger.info(f"100ms room created: {data.get('id')}")
                return data
            else:
                logger.error(f"100ms room creation failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"100ms room creation error: {e}")
        return None

async def end_hms_room(room_id: str):
    """Disable/end a 100ms room"""
    try:
        mgmt_token = generate_hms_management_token()
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.post(
                f"{HMS_API_BASE}/rooms/{room_id}",
                json={"enabled": False},
                headers={"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
            )
            logger.info(f"100ms room ended: {room_id} - status {response.status_code}")
    except Exception as e:
        logger.error(f"100ms room end error: {e}")

# ─── ANTI-COLLUSION ENGINE ─────────────────────────────
async def run_anti_collusion_checks(seeker_id: str, listener_id: str, call_id: str, duration: int):
    """Run anti-collusion checks after each call"""
    flags = []
    now_dt = datetime.now(timezone.utc)
    today_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Short call spam: 3 calls < 60 sec in 15 min
    fifteen_min_ago = now_dt - timedelta(minutes=15)
    recent_short = await db.calls.count_documents({
        "seeker_id": seeker_id, "duration_seconds": {"$lt": 60, "$gt": 0},
        "created_at": {"$gte": fifteen_min_ago.isoformat()}
    })
    if recent_short >= 3:
        flags.append({"type": "short_call_spam", "desc": f"{recent_short} short calls in 15min"})

    # 2. Same pair abuse: >3 calls/day or >60 min/day
    pair_calls_today = await db.calls.find(
        {"seeker_id": seeker_id, "listener_id": listener_id, "created_at": {"$gte": today_start.isoformat()}},
        {"_id": 0}
    ).to_list(100)
    if len(pair_calls_today) > 3:
        flags.append({"type": "pair_overcall", "desc": f"{len(pair_calls_today)} calls today with same pair"})
    pair_minutes = sum(c.get("duration_seconds", 0) for c in pair_calls_today) / 60
    if pair_minutes > 60:
        flags.append({"type": "pair_overminutes", "desc": f"{pair_minutes:.0f} min today with same pair"})

    # 3. Silence farming: call < 30 seconds but not a quick disconnect
    if 5 < duration < 30:
        silence_count = await db.risk_flags.count_documents({
            "user_id": seeker_id, "flag_type": "silence_farming",
            "created_at": {"$gte": today_start.isoformat()}
        })
        if silence_count >= 2:
            flags.append({"type": "silence_farming", "desc": "Multiple very short calls"})

    # Store flags
    for f in flags:
        await db.risk_flags.insert_one({
            "id": uid(), "user_id": seeker_id, "listener_id": listener_id,
            "call_id": call_id, "flag_type": f["type"],
            "description": f["desc"], "status": "active",
            "created_at": now()
        })
        logger.warning(f"Anti-collusion flag: {f['type']} - {f['desc']} (seeker={seeker_id[:8]})")

    # Auto-actions
    active_flags = await db.risk_flags.count_documents({"user_id": seeker_id, "status": "active"})
    if active_flags >= 5:
        await db.users.update_one({"id": seeker_id}, {"$set": {"shadow_limited": True}})
        logger.warning(f"Shadow-limited seeker {seeker_id[:8]} with {active_flags} flags")

# ─── RATE LIMITING ─────────────────────────────────────
async def check_rate_limit_db(limit_type: str, key: str, max_calls: int, window_minutes: int) -> bool:
    """Returns True if rate limit exceeded. MongoDB-backed for cross-process safety."""
    window_start = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    count = await db.rate_limits.count_documents({
        "type": limit_type, "key": key, "created_at": {"$gte": window_start}
    })
    if count >= max_calls:
        return True
    await db.rate_limits.insert_one({
        "id": uid(), "type": limit_type, "key": key, "created_at": now()
    })
    return False

# ─── DEVICE FINGERPRINTING ─────────────────────────────
async def record_device_fingerprint(device_id: str, user_id: str):
    """Track device↔user association; soft-flag multi-account devices."""
    if not device_id:
        return
    already_this_user = await db.device_fingerprints.find_one(
        {"device_id": device_id, "user_id": user_id}
    )
    if not already_this_user:
        other_user = await db.device_fingerprints.find_one(
            {"device_id": device_id, "user_id": {"$ne": user_id}}
        )
        if other_user:
            flag_desc = f"Device shared between accounts {other_user['user_id'][:8]} and {user_id[:8]}"
            for flag_uid in [user_id, other_user["user_id"]]:
                existing_flag = await db.risk_flags.find_one(
                    {"user_id": flag_uid, "flag_type": "device_shared", "status": "active"}
                )
                if not existing_flag:
                    await db.risk_flags.insert_one({
                        "id": uid(), "user_id": flag_uid, "flag_type": "device_shared",
                        "description": flag_desc, "status": "active", "created_at": now()
                    })
            logger.warning(f"Multi-account device: device={device_id[:12]}, users={other_user['user_id'][:8]},{user_id[:8]}")
        await db.device_fingerprints.update_one(
            {"device_id": device_id, "user_id": user_id},
            {"$set": {"device_id": device_id, "user_id": user_id, "updated_at": now()},
             "$setOnInsert": {"created_at": now()}},
            upsert=True
        )

async def is_same_device(user_a: str, user_b: str) -> bool:
    """Return True if two users share a known device fingerprint."""
    a_devices = await db.device_fingerprints.find(
        {"user_id": user_a}, {"device_id": 1, "_id": 0}
    ).to_list(20)
    a_ids = {d["device_id"] for d in a_devices}
    if not a_ids:
        return False
    match = await db.device_fingerprints.find_one(
        {"user_id": user_b, "device_id": {"$in": list(a_ids)}}
    )
    return match is not None

# ─── PUSH NOTIFICATIONS ─────────────────────────────────
async def send_expo_push(push_token: str, title: str, body: str, data: dict = {}):
    """Send a push notification via Expo Push API."""
    if not push_token or not push_token.startswith("ExponentPushToken"):
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            await http_client.post(
                "https://exp.host/--/api/v2/push/send",
                json={"to": push_token, "sound": "default",
                      "title": title, "body": body, "data": data},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
    except Exception as e:
        logger.warning(f"Push notification error: {e}")

async def notify_favorites_of_listener_online(listener_id: str, listener_name: str):
    """Notify seekers who favorited this listener that they're now online."""
    favorites = await db.favorites.find(
        {"listener_id": listener_id}, {"seeker_id": 1, "_id": 0}
    ).to_list(200)
    if not favorites:
        return
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    for fav in favorites:
        seeker_id = fav["seeker_id"]
        # Throttle: one notification per seeker-listener pair per hour
        recent = await db.push_notifications_sent.find_one({
            "seeker_id": seeker_id, "listener_id": listener_id,
            "sent_at": {"$gte": one_hour_ago}
        })
        if recent:
            continue
        token_doc = await db.push_tokens.find_one({"user_id": seeker_id}, {"token": 1})
        if not token_doc:
            continue
        await send_expo_push(
            token_doc["token"],
            title=f"{listener_name} is available!",
            body="Your favorite listener is online now. Tap to start a call.",
            data={"listener_id": listener_id, "screen": "seeker/home"},
        )
        await db.push_notifications_sent.insert_one({
            "seeker_id": seeker_id, "listener_id": listener_id, "sent_at": now()
        })

# ─── CALL RECORDING METADATA ──────────────────────────
async def create_call_recording_metadata(call_id: str, seeker_id: str, listener_id: str, hms_room_id: str):
    """Store encrypted call recording metadata (actual recording via 100ms)"""
    await db.call_recordings.insert_one({
        "id": uid(), "call_id": call_id,
        "seeker_id": seeker_id, "listener_id": listener_id,
        "hms_room_id": hms_room_id,
        "status": "recorded",
        "encrypted": True,
        "retention_days": 15,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
        "created_at": now()
    })

async def cleanup_expired_recordings():
    """Delete recordings older than 15 days"""
    cutoff = datetime.now(timezone.utc).isoformat()
    result = await db.call_recordings.delete_many({"expires_at": {"$lt": cutoff}})
    if result.deleted_count:
        logger.info(f"Cleaned up {result.deleted_count} expired recordings")

# ─── SUBSCRIPTION & PROMO CONSTANTS ────────────────────
SUBSCRIPTION_PLANS = {
    "basic_monthly": {
        "price": 199, "credits": 50,
        "discount_pct": 10,  # 10% off per-minute call rate
        "name": "Basic Monthly", "duration_days": 30,
    },
    "premium_monthly": {
        "price": 499, "credits": 150,
        "discount_pct": 20,  # 20% off per-minute call rate
        "name": "Premium Monthly", "duration_days": 30,
    },
}

# IST = UTC + 5:30.  Happy hour 14:00–16:00 IST = 08:30–10:30 UTC
HAPPY_HOUR_UTC_START = 8   # 08:30 UTC ≈ 14:00 IST (approximate to whole hour)
HAPPY_HOUR_UTC_END   = 10  # 10:30 UTC ≈ 16:00 IST
HAPPY_HOUR_BONUS_PCT = 20  # 20 % bonus credits during happy hour

STREAK_BUNDLE = {
    "pack_299": {"bonus_pct": 10, "label": "+10% bonus credits"},
    "pack_699": {"bonus_pct": 15, "label": "+15% bonus credits"},
}

# ─── WEBSOCKET MANAGER ─────────────────────────────────
# In-memory map: user_id → active WebSocket (listeners AND seekers share this)
_active_ws: dict = {}

async def _ws_push(user_id: str, payload: dict):
    """Push a JSON event to a connected WebSocket client, if any."""
    ws = _active_ws.get(user_id)
    if ws:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception as e:
            logger.warning(f"WS push failed for {user_id[:8]}: {e}")
            _active_ws.pop(user_id, None)

async def _update_listener_answer_rate(listener_id: str):
    """Recalculate and store answer_rate for a listener."""
    profile = await db.listener_profiles.find_one({"user_id": listener_id}, {"_id": 0})
    if not profile:
        return
    answered = profile.get("calls_answered", 0)
    rejected = profile.get("calls_rejected", 0)
    total = answered + rejected
    if total > 0:
        rate = round(answered / total, 3)
        await db.listener_profiles.update_one(
            {"user_id": listener_id}, {"$set": {"answer_rate": rate}}
        )

# ─── AUTH ──────────────────────────────────────────────
@api_router.post("/auth/send-otp")
async def send_otp(req: OTPRequest):
    # Rate limit: 3 OTP sends per phone per 10 minutes
    if await check_rate_limit_db("otp_send", req.phone, 3, 10):
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait 10 minutes before retrying.")
    # Mocked OTP - always sends 1234
    return {"success": True, "message": "OTP sent (mocked: use 1234)"}

@api_router.post("/auth/verify-otp")
async def verify_otp(req: OTPVerify):
    if req.otp != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check if user already exists by phone number (any role)
    user = await db.users.find_one({"phone": req.phone}, {"_id": 0})
    if user:
        # Existing user - return with their role
        if req.device_id:
            await record_device_fingerprint(req.device_id, user["id"])
        token = create_token(user["id"], user.get("role", ""))
        return {"success": True, "token": token, "user": user, "needs_gender": False}
    else:
        # New user - create without role, needs gender selection
        user_id = uid()
        user = {
            "id": user_id,
            "phone": req.phone,
            "role": "",
            "gender": "",
            "onboarded": False,
            "created_at": now()
        }
        await db.users.insert_one(user)
        user.pop("_id", None)
        if req.device_id:
            await record_device_fingerprint(req.device_id, user_id)
        token = create_token(user_id, "")
        return {"success": True, "token": token, "user": user, "needs_gender": True}

@api_router.post("/auth/firebase-verify")
async def firebase_verify(req: FirebaseAuthRequest):
    """Verify a Firebase ID token from phone OTP auth and return an app JWT."""
    try:
        decoded = fb_auth.verify_id_token(req.firebase_token)
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token")

    # Extract the phone number verified by Firebase
    firebase_phone = decoded.get("phone_number", "")
    if not firebase_phone:
        raise HTTPException(status_code=400, detail="Firebase token does not contain a phone number")

    # Use the Firebase-verified phone; fall back to the client-supplied one only
    # if they match (prevents spoofing).
    phone = firebase_phone
    if req.phone and req.phone != firebase_phone:
        raise HTTPException(status_code=400, detail="Phone number mismatch")

    # Check if user already exists by phone number
    user = await db.users.find_one({"phone": phone}, {"_id": 0})
    if user:
        if req.device_id:
            await record_device_fingerprint(req.device_id, user["id"])
        token = create_token(user["id"], user.get("role", ""))
        return {"success": True, "token": token, "user": user, "needs_gender": False}
    else:
        # New user
        user_id = uid()
        user = {
            "id": user_id,
            "phone": phone,
            "role": "",
            "gender": "",
            "onboarded": False,
            "firebase_uid": decoded.get("uid", ""),
            "created_at": now()
        }
        await db.users.insert_one(user)
        user.pop("_id", None)
        if req.device_id:
            await record_device_fingerprint(req.device_id, user_id)
        token = create_token(user_id, "")
        return {"success": True, "token": token, "user": user, "needs_gender": True}

@api_router.post("/auth/set-gender")
async def set_gender(req: SetGenderRequest, user=Depends(get_current_user)):
    if req.gender not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be male or female")
    role = "seeker" if req.gender == "male" else "listener"
    await db.users.update_one(
        {"id": user["user_id"]},
        {"$set": {"gender": req.gender, "role": role}}
    )
    updated_user = await db.users.find_one({"id": user["user_id"]}, {"_id": 0})
    # Generate new token with role
    token = create_token(user["user_id"], role)
    return {"success": True, "token": token, "user": updated_user}

# ─── SEEKER ────────────────────────────────────────────
@api_router.post("/seekers/onboard")
async def seeker_onboard(req: SeekerOnboard, user=Depends(get_current_user)):
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Not a seeker")
    profile = {
        "user_id": user["user_id"],
        "name": req.name,
        "age": req.age,
        "languages": req.languages,
        "intent_tags": req.intent_tags,
        "created_at": now()
    }
    await db.seeker_profiles.update_one(
        {"user_id": user["user_id"]}, {"$set": profile}, upsert=True
    )
    # Create wallet with zero balance
    existing_wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]})
    if not existing_wallet:
        await db.wallet_accounts.insert_one({
            "user_id": user["user_id"],
            "balance": 0,
            "created_at": now()
        })
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"onboarded": True, "name": req.name}})
    return {"success": True, "message": "Onboarding complete"}

@api_router.get("/seekers/profile")
async def get_seeker_profile(user=Depends(get_current_user)):
    profile = await db.seeker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

# ─── LISTENER ──────────────────────────────────────────
@api_router.post("/listeners/onboard")
async def listener_onboard(req: ListenerOnboard, user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Not a listener")
    profile = {
        "user_id": user["user_id"],
        "name": req.name,
        "age": req.age,
        "languages": req.languages,
        "avatar_id": req.avatar_id,
        "style_tags": req.style_tags,
        "topic_tags": req.topic_tags,
        "boundary_answers": req.boundary_answers,
        "is_online": True,  # Auto-online when they open app
        "kyc_status": "pending",  # pending, submitted, verified, rejected
        "tier": "new",
        "total_calls": 0,
        "total_minutes": 0,
        "avg_rating": 0,
        "last_matched_at": None,
        "created_at": now()
    }
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]}, {"$set": profile}, upsert=True
    )
    # Create earnings account
    existing = await db.listener_earnings.find_one({"user_id": user["user_id"]})
    if not existing:
        await db.listener_earnings.insert_one({
            "user_id": user["user_id"],
            "total_earned": 0,
            "pending_balance": 0,
            "withdrawn": 0,
            "created_at": now()
        })
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"onboarded": True, "name": req.name}})
    return {"success": True, "message": "Listener onboarding complete"}

@api_router.get("/listeners/profile")
async def get_listener_profile(user=Depends(get_current_user)):
    profile = await db.listener_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@api_router.post("/listeners/toggle-online")
async def toggle_online(req: ToggleOnlineRequest, user=Depends(get_current_user)):
    # Now used as heartbeat - listener auto-goes online when app opens
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"is_online": True, "last_online": now()}}
    )
    return {"success": True, "online": True}

# Auto-online heartbeat endpoint - called when listener opens dashboard
@api_router.post("/listeners/heartbeat")
async def listener_heartbeat(user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    profile = await db.listener_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    # Detect coming-online event: was offline or last heartbeat > 2 minutes ago
    was_offline = True
    if profile and profile.get("is_online") and profile.get("last_online"):
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(profile["last_online"])).total_seconds()
            was_offline = elapsed > 120
        except Exception:
            pass
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"is_online": True, "last_online": now()}}
    )
    # Notify favoriting seekers only on fresh online event
    if was_offline:
        listener_name = profile.get("name", "Your listener") if profile else "Your listener"
        await notify_favorites_of_listener_online(user["user_id"], listener_name)
    return {"success": True, "online": True}

# Go offline when listener leaves the app
@api_router.post("/listeners/go-offline")
async def go_offline(user=Depends(get_current_user)):
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"is_online": False, "last_online": now()}}
    )
    return {"success": True, "online": False}

# ─── LEADERBOARD ────────────────────────────────────────
@api_router.get("/listeners/leaderboard")
async def get_leaderboard(period: str = "weekly", user=Depends(get_current_user)):
    """
    Get listener leaderboard rankings.
    Period can be: 'weekly', 'monthly', 'all_time'
    Returns top 50 listeners ranked by earnings.
    """
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    
    # Calculate date range for period
    now_dt = datetime.utcnow()
    if period == "weekly":
        start_date = now_dt - timedelta(days=7)
    elif period == "monthly":
        start_date = now_dt - timedelta(days=30)
    else:
        start_date = datetime(2020, 1, 1)  # All time
    
    # Get all listener profiles with stats
    profiles = await db.listener_profiles.find({}, {"_id": 0}).to_list(500)
    
    # Get earnings data from listener_stats
    stats_list = await db.listener_stats.find({}).to_list(500)
    stats_map = {s["user_id"]: s for s in stats_list}
    
    # Get call data for the period
    calls = await db.calls.find({
        "ended_at": {"$gte": start_date.isoformat()}
    }).to_list(10000)
    
    # Calculate period earnings and minutes per listener
    period_earnings = {}
    period_minutes = {}
    period_calls = {}
    
    for call in calls:
        listener_id = call.get("listener_id")
        if not listener_id:
            continue
        if listener_id not in period_earnings:
            period_earnings[listener_id] = 0
            period_minutes[listener_id] = 0
            period_calls[listener_id] = 0
        
        duration = call.get("duration_seconds", 0)
        # Calculate listener earnings (₹2.5/min voice, ₹5/min video)
        rate = 5 if call.get("call_type") == "video" else 2.5
        earnings = (duration / 60) * rate
        period_earnings[listener_id] += earnings
        period_minutes[listener_id] += duration / 60
        period_calls[listener_id] += 1
    
    # Build leaderboard entries
    leaderboard = []
    for profile in profiles:
        user_id = profile.get("user_id")
        stats = stats_map.get(user_id, {})
        
        entry = {
            "user_id": user_id,
            "name": profile.get("name", "Anonymous"),
            "avatar_id": profile.get("avatar_id", "avatar_1"),
            "is_online": profile.get("is_online", False),
            "period_earnings": round(period_earnings.get(user_id, 0), 2),
            "period_minutes": round(period_minutes.get(user_id, 0), 1),
            "period_calls": period_calls.get(user_id, 0),
            "total_earnings": stats.get("total_earnings", 0),
            "total_minutes": stats.get("total_minutes", 0),
            "total_calls": stats.get("total_calls", 0),
            "average_rating": stats.get("average_rating", 0),
            "tier": profile.get("tier", "new"),
        }
        leaderboard.append(entry)
    
    # Sort by period earnings (descending)
    leaderboard.sort(key=lambda x: x["period_earnings"], reverse=True)
    
    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    # Find current user's rank
    current_user_rank = None
    current_user_entry = None
    for entry in leaderboard:
        if entry["user_id"] == user["user_id"]:
            current_user_rank = entry["rank"]
            current_user_entry = entry
            break
    
    # Return top 50 and user's entry if not in top 50
    top_50 = leaderboard[:50]
    
    return {
        "period": period,
        "leaderboard": top_50,
        "total_listeners": len(leaderboard),
        "current_user": {
            "rank": current_user_rank,
            "entry": current_user_entry
        }
    }

@api_router.get("/listeners/online")
async def get_online_listeners(user=Depends(get_current_user)):
    # Only show listeners who sent a heartbeat in the last 90 seconds
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    listeners = await db.listener_profiles.find(
        {"is_online": True, "last_online": {"$gte": cutoff}}, {"_id": 0}
    ).to_list(50)
    return {"listeners": listeners}

@api_router.get("/listeners/all")
async def get_all_listeners():
    listeners = await db.listener_profiles.find({}, {"_id": 0}).to_list(100)
    return {"listeners": listeners}

# ─── MATCHING ──────────────────────────────────────────
@api_router.post("/match/talk-now")
async def talk_now(user=Depends(get_current_user)):
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Only seekers can use Talk Now")
    seeker = await db.seeker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not seeker:
        raise HTTPException(status_code=404, detail="Complete onboarding first")
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not wallet or wallet.get("balance", 0) < 5:
        raise HTTPException(status_code=400, detail="Insufficient balance. Minimum 5 credits required.")
    # Check shadow-limited
    seeker_user = await db.users.find_one({"id": user["user_id"]}, {"_id": 0})
    if seeker_user and seeker_user.get("shadow_limited"):
        raise HTTPException(status_code=404, detail="No listeners available right now. Try again shortly.")
    # Only match listeners who sent a heartbeat in the last 90 seconds
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    online = await db.listener_profiles.find(
        {"is_online": True, "in_call": {"$ne": True}, "last_online": {"$gte": cutoff}}, {"_id": 0}
    ).to_list(50)
    if not online:
        raise HTTPException(status_code=404, detail="No listeners available right now. Try again shortly.")

    # IMPROVED FAIRNESS ROTATION: Prioritize least-recently-matched listeners
    scored = []
    for l in online:
        score = 0
        # Language match (hard weight)
        lang_match = set(seeker.get("languages", [])) & set(l.get("languages", []))
        score += len(lang_match) * 10
        # Tag overlap
        tag_match = set(seeker.get("intent_tags", [])) & set(l.get("topic_tags", []))
        score += len(tag_match) * 3
        # Tier bonus
        if l.get("tier") == "trusted": score += 2
        elif l.get("tier") == "elite": score += 4
        # Answer-rate bonus: reward listeners who actually pick up (up to +20 pts)
        score += l.get("answer_rate", 0.5) * 20
        # FAIRNESS: Penalize recently matched listeners (spread calls across all)
        last_matched = l.get("last_matched_at")
        if last_matched:
            try:
                mins_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_matched)).total_seconds() / 60
                score += min(mins_since, 30)  # Up to 30 bonus pts for waiting long
            except Exception:
                score += 15  # Default bonus
        else:
            score += 30  # Never matched = highest priority
        # FAIRNESS: Penalize same-pair repeat matching
        pair_calls_today = await db.calls.count_documents({
            "seeker_id": user["user_id"], "listener_id": l["user_id"],
            "created_at": {"$gte": datetime.now(timezone.utc).replace(hour=0).isoformat()}
        })
        score -= pair_calls_today * 10  # Strong penalty for repeated pairing
        # Small random factor
        score += random.randint(0, 5)
        scored.append((score, l))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched = scored[0][1]
    # Update last_matched_at for the selected listener
    await db.listener_profiles.update_one(
        {"user_id": matched["user_id"]}, {"$set": {"last_matched_at": now()}}
    )
    return {"success": True, "listener": matched}

# ─── CALLS ─────────────────────────────────────────────
@api_router.post("/calls/start")
async def start_call(req: CallStartRequest, user=Depends(get_current_user)):
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not wallet or wallet.get("balance", 0) < 5:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    # Check first call discount
    prev_calls = await db.calls.count_documents({"seeker_id": user["user_id"]})
    is_first_call = prev_calls == 0
    rate = 1 if is_first_call else (5 if req.call_type == "voice" else 10)

    # Apply active subscription discount on non-first calls
    if not is_first_call:
        active_sub = await db.subscriptions.find_one(
            {"user_id": user["user_id"], "status": "active", "expires_at": {"$gt": now()}},
            {"_id": 0}
        )
        if active_sub:
            discount = active_sub.get("discount_pct", 0)
            rate = round(rate * (1 - discount / 100), 2)

    call_id = uid()

    # Create 100ms room for the call
    hms_room = await create_hms_room(f"vm-call-{call_id[:8]}")
    hms_room_id = hms_room.get("id") if hms_room else None

    # Generate 100ms tokens for both participants
    seeker_hms_token = None
    listener_hms_token = None
    if hms_room_id:
        seeker_hms_token = generate_hms_app_token(hms_room_id, user["user_id"], "host")
        listener_hms_token = generate_hms_app_token(hms_room_id, req.listener_id, "guest")
        # Store listener's token so they can retrieve it
        await db.hms_call_tokens.insert_one({
            "call_id": call_id,
            "listener_id": req.listener_id,
            "hms_token": listener_hms_token,
            "hms_room_id": hms_room_id,
            "created_at": now()
        })

    call = {
        "id": call_id,
        "seeker_id": user["user_id"],
        "listener_id": req.listener_id,
        "call_type": req.call_type,
        "rate_per_min": rate,
        "is_first_call": is_first_call,
        "status": "ringing",
        "hms_room_id": hms_room_id,
        "started_at": now(),
        "connected_at": None,
        "ended_at": None,
        "duration_seconds": 0,
        "cost": 0,
        "created_at": now()
    }
    await db.calls.insert_one(call)
    call.pop("_id", None)

    # Push real-time incoming-call notification to listener (if connected via WebSocket)
    seeker_profile_ws = await db.seeker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    caller_name = seeker_profile_ws.get("name", "Someone") if seeker_profile_ws else "Someone"
    await _ws_push(req.listener_id, {
        "event": "incoming_call",
        "call_id": call_id,
        "caller_name": caller_name,
        "call_type": req.call_type,
    })

    # Return call data with 100ms token for seeker
    call["hms_token"] = seeker_hms_token
    return {"success": True, "call": call}

@api_router.post("/calls/accept")
async def accept_call(req: CallAcceptRequest, user=Depends(get_current_user)):
    """Listener accepts an incoming call - transitions from ringing to active"""
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call["listener_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your call")
    if call["status"] != "ringing":
        raise HTTPException(status_code=400, detail=f"Call is not ringing (status: {call['status']})")
    connected_at = now()
    await db.calls.update_one(
        {"id": req.call_id},
        {"$set": {"status": "active", "connected_at": connected_at}}
    )
    # Mark listener as in_call now that they actually accepted
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"in_call": True}, "$inc": {"calls_answered": 1}}
    )
    await _update_listener_answer_rate(user["user_id"])

    # Notify seeker that their call was accepted
    await _ws_push(call["seeker_id"], {
        "event": "call_accepted",
        "call_id": req.call_id,
        "connected_at": connected_at,
    })
    # Get the listener's HMS token
    token_doc = await db.hms_call_tokens.find_one(
        {"call_id": req.call_id, "listener_id": user["user_id"]}, {"_id": 0}
    )
    return {
        "success": True,
        "call_id": req.call_id,
        "connected_at": connected_at,
        "hms_token": token_doc.get("hms_token") if token_doc else None,
        "hms_room_id": token_doc.get("hms_room_id") if token_doc else None,
    }

@api_router.post("/calls/reject")
async def reject_call(req: CallRejectRequest, user=Depends(get_current_user)):
    """Listener rejects an incoming call"""
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call["listener_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your call")
    if call["status"] != "ringing":
        raise HTTPException(status_code=400, detail=f"Call is not ringing (status: {call['status']})")
    await db.calls.update_one(
        {"id": req.call_id},
        {"$set": {"status": "rejected", "ended_at": now(), "duration_seconds": 0, "cost": 0}}
    )
    # Track rejection for answer-rate calculation
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]}, {"$inc": {"calls_rejected": 1}}
    )
    await _update_listener_answer_rate(user["user_id"])
    # Clean up HMS resources
    if call.get("hms_room_id"):
        await end_hms_room(call["hms_room_id"])
        await db.hms_call_tokens.delete_many({"call_id": req.call_id})
    # Notify seeker so they can rematch immediately
    await _ws_push(call["seeker_id"], {
        "event": "call_rejected",
        "call_id": req.call_id,
    })
    return {"success": True, "message": "Call rejected"}

@api_router.get("/calls/status/{call_id}")
async def get_call_status(call_id: str, user=Depends(get_current_user)):
    """Poll call status - used by seeker to check if listener accepted"""
    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "call_id": call_id,
        "status": call["status"],
        "connected_at": call.get("connected_at"),
        "duration_seconds": call.get("duration_seconds", 0),
        "cost": call.get("cost", 0),
    }

@api_router.get("/calls/check-incoming")
async def check_incoming_call(user=Depends(get_current_user)):
    """Listener polls this to check if there's an incoming call ringing"""
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    # Find any ringing call for this listener
    call = await db.calls.find_one(
        {"listener_id": user["user_id"], "status": "ringing"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    if not call:
        return {"has_incoming": False}
    # Get seeker name for display
    seeker_profile = await db.seeker_profiles.find_one(
        {"user_id": call["seeker_id"]}, {"_id": 0}
    )
    seeker_name = seeker_profile.get("name", "Someone") if seeker_profile else "Someone"
    return {
        "has_incoming": True,
        "call_id": call["id"],
        "caller_name": seeker_name,
        "call_type": call.get("call_type", "voice"),
        "started_at": call["started_at"],
    }

@api_router.post("/calls/end")
async def end_call(req: CallEndRequest, user=Depends(get_current_user)):
    call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    # Idempotent: if call is already ended, return existing data without re-processing
    if call["status"] in ("ended", "missed", "rejected"):
        return {
            "success": True,
            "duration_seconds": call.get("duration_seconds", 0),
            "cost": call.get("cost", 0),
            "listener_earned": 0
        }
    # If call was never accepted (still ringing), end it with no charge
    if call["status"] == "ringing":
        await db.calls.update_one({"id": req.call_id}, {"$set": {
            "status": "missed",
            "ended_at": now(),
            "duration_seconds": 0,
            "cost": 0
        }})
        # Clean up HMS resources
        if call.get("hms_room_id"):
            await end_hms_room(call["hms_room_id"])
            await db.hms_call_tokens.delete_many({"call_id": req.call_id})
        return {"success": True, "duration_seconds": 0, "cost": 0, "listener_earned": 0}

    # Use connected_at (when listener accepted) for billing, not started_at
    connected_at_str = call.get("connected_at")
    if connected_at_str:
        started = datetime.fromisoformat(connected_at_str)
    else:
        started = datetime.fromisoformat(call["started_at"])
    ended = datetime.now(timezone.utc)
    duration = int((ended - started).total_seconds())
    rate = call["rate_per_min"]

    # Billing: FREE if ≤5 seconds, full first minute + per-second after 60s
    if duration <= 5:
        cost = 0  # Free - no charge for calls under 5 seconds
    else:
        if call.get("is_first_call"):
            # First call discount: ₹1/min for first 5 mins
            if duration <= 300:
                # Full first minute at ₹1 + per-second for remaining
                cost = 1.0  # first minute flat
                if duration > 60:
                    cost += ((duration - 60) / 60) * 1.0
            else:
                # First 5 min at ₹1/min + rest at normal rate
                cost = 5.0  # 5 minutes at ₹1
                normal_rate = 5 if call["call_type"] == "voice" else 10
                cost += ((duration - 300) / 60) * normal_rate
        else:
            # Standard billing: full first minute charge + per-second after
            cost = rate  # first minute flat charge
            if duration > 60:
                cost += ((duration - 60) / 60) * rate
        cost = round(cost, 2)

    # ── Atomic status transition: prevents parallel/retry double-charge ─────────
    # Only transitions call if it is STILL "active". If another concurrent
    # request already closed it, modified_count == 0 and we return early.
    status_result = await db.calls.update_one(
        {"id": req.call_id, "status": "active"},
        {"$set": {
            "status": "ended",
            "ended_at": ended.isoformat(),
            "duration_seconds": duration,
            "cost": cost,
        }}
    )
    if status_result.modified_count == 0:
        call_final = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
        return {
            "success": True,
            "duration_seconds": call_final.get("duration_seconds", 0) if call_final else duration,
            "cost": call_final.get("cost", 0) if call_final else 0,
            "listener_earned": 0,
        }

    earnings = 0
    if cost > 0:
        # ── Atomic balance guard: prevents negative balance ───────────────────
        # Attempt full debit only when balance is sufficient.
        original_cost = cost
        debit_result = await db.wallet_accounts.update_one(
            {"user_id": call["seeker_id"], "balance": {"$gte": cost}},
            {"$inc": {"balance": -cost}}
        )
        if debit_result.modified_count == 0:
            # Insufficient balance — charge only what is available, floor at ₹0
            wallet_now = await db.wallet_accounts.find_one({"user_id": call["seeker_id"]})
            available = round(max(wallet_now.get("balance", 0), 0), 2) if wallet_now else 0
            if available > 0:
                await db.wallet_accounts.update_one(
                    {"user_id": call["seeker_id"]},
                    {"$set": {"balance": 0}}
                )
                cost = available
            else:
                cost = 0
            logger.warning(
                f"Balance shortfall: seeker {call['seeker_id'][:8]} "
                f"charged ₹{cost} (billed ₹{original_cost}) – partial debit"
            )
            # Correct the call record with the actual amount charged
            await db.calls.update_one({"id": req.call_id}, {"$set": {"cost": cost}})

        if cost > 0:
            await db.wallet_ledger.insert_one({
                "id": uid(), "user_id": call["seeker_id"],
                "type": "debit", "amount": cost,
                "description": f"Call ({call['call_type']}) - {duration}s",
                "call_id": req.call_id, "created_at": now()
            })
        # Credit listener earnings
        listener_rate = 2.5 if call["call_type"] == "voice" else 5
        earnings = round((duration / 60) * listener_rate, 2)
        await db.listener_earnings.update_one(
            {"user_id": call["listener_id"]},
            {"$inc": {"total_earned": earnings, "pending_balance": earnings}}
        )
        await db.listener_earnings_ledger.insert_one({
            "id": uid(), "user_id": call["listener_id"],
            "type": "earning", "amount": earnings,
            "description": f"Call earning - {duration}s",
            "call_id": req.call_id, "created_at": now()
        })
        # Check referral commission for the listener's referrer
        await process_referral_commission(call["listener_id"], earnings)

    # Update listener stats
    await db.listener_profiles.update_one(
        {"user_id": call["listener_id"]},
        {"$inc": {"total_calls": 1, "total_minutes": duration / 60}, "$set": {"in_call": False}}
    )
    # Check if this listener's referral should be activated
    await check_referral_activation(call["listener_id"])
    # Run anti-collusion checks
    await run_anti_collusion_checks(call["seeker_id"], call["listener_id"], req.call_id, duration)
    # Store call recording metadata
    if call.get("hms_room_id"):
        await create_call_recording_metadata(req.call_id, call["seeker_id"], call["listener_id"], call["hms_room_id"])
    # End 100ms room
    if call.get("hms_room_id"):
        await end_hms_room(call["hms_room_id"])
        # Clean up token
        await db.hms_call_tokens.delete_many({"call_id": req.call_id})
    return {
        "success": True,
        "duration_seconds": duration,
        "cost": cost,
        "listener_earned": earnings
    }

# Endpoint for listener to get their 100ms token for an incoming call
@api_router.get("/calls/incoming-token")
async def get_incoming_call_token(user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    token_doc = await db.hms_call_tokens.find_one(
        {"listener_id": user["user_id"]}, {"_id": 0},
        sort=[("created_at", -1)]
    )
    if not token_doc:
        raise HTTPException(status_code=404, detail="No incoming call")
    # Find the associated call
    call = await db.calls.find_one(
        {"id": token_doc["call_id"], "status": "active"}, {"_id": 0}
    )
    if not call:
        raise HTTPException(status_code=404, detail="No active incoming call")
    return {
        "success": True,
        "call_id": token_doc["call_id"],
        "hms_token": token_doc["hms_token"],
        "hms_room_id": token_doc["hms_room_id"],
        "call": call
    }

# 100ms room management endpoint
@api_router.get("/hms/room-status/{room_id}")
async def get_hms_room_status(room_id: str):
    """Check 100ms room status"""
    try:
        mgmt_token = generate_hms_management_token()
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                f"{HMS_API_BASE}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {mgmt_token}"}
            )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail="Room not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
async def call_history(user=Depends(get_current_user)):
    field = "seeker_id" if user["role"] == "seeker" else "listener_id"
    calls = await db.calls.find(
        {field: user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"calls": calls}

# ─── WALLET ────────────────────────────────────────────
@api_router.get("/wallet/balance")
async def get_balance(user=Depends(get_current_user)):
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not wallet:
        return {"balance": 0}
    return {"balance": wallet.get("balance", 0)}

@api_router.post("/wallet/recharge")
async def recharge(req: RechargeRequest, user=Depends(get_current_user)):
    # Rate limit: 10 recharges per user per 24 hours
    if await check_rate_limit_db("recharge", user["user_id"], 10, 1440):
        raise HTTPException(status_code=429, detail="Too many recharge attempts today. Please try again tomorrow.")
    packs = {"pack_99": 99, "pack_299": 299, "pack_699": 699}
    base_amount = packs.get(req.pack_id)
    if not base_amount:
        raise HTTPException(status_code=400, detail="Invalid pack")

    # Happy-hour bonus (14:00–16:00 IST ≈ 08:30–10:30 UTC)
    now_utc = datetime.now(timezone.utc)
    bonus_credits = 0
    bonus_reasons = []
    if HAPPY_HOUR_UTC_START <= now_utc.hour < HAPPY_HOUR_UTC_END:
        hh_bonus = round(base_amount * HAPPY_HOUR_BONUS_PCT / 100)
        bonus_credits += hh_bonus
        bonus_reasons.append(f"Happy-hour +{HAPPY_HOUR_BONUS_PCT}% ({hh_bonus} credits)")

    # Streak bundle bonus for pack_299 and pack_699
    bundle = STREAK_BUNDLE.get(req.pack_id)
    if bundle:
        bun_bonus = round(base_amount * bundle["bonus_pct"] / 100)
        bonus_credits += bun_bonus
        bonus_reasons.append(f"Bundle offer {bundle['label']} ({bun_bonus} credits)")

    total_credits = base_amount + bonus_credits
    description = f"Recharge ₹{base_amount}"
    if bonus_reasons:
        description += " + " + " + ".join(bonus_reasons)

    # Mocked payment - always success
    await db.wallet_accounts.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": total_credits}},
        upsert=True
    )
    await db.wallet_ledger.insert_one({
        "id": uid(), "user_id": user["user_id"],
        "type": "credit", "amount": total_credits,
        "description": description, "created_at": now()
    })
    # Trigger seeker referral credit on first recharge (anti-abuse: bonus only after real payment)
    await process_seeker_referral_on_recharge(user["user_id"])
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {
        "success": True,
        "base_credits": base_amount,
        "bonus_credits": bonus_credits,
        "total_credits": total_credits,
        "bonus_reasons": bonus_reasons,
        "new_balance": wallet.get("balance", 0),
    }

@api_router.get("/wallet/transactions")
async def get_transactions(user=Depends(get_current_user)):
    txns = await db.wallet_ledger.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"transactions": txns}

# ─── PUSH TOKENS ────────────────────────────────────────
@api_router.post("/push/register-token")
async def register_push_token(req: PushTokenRequest, user=Depends(get_current_user)):
    """Register an Expo push token for the authenticated user."""
    await db.push_tokens.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"user_id": user["user_id"], "token": req.token,
                  "platform": req.platform, "updated_at": now()},
         "$setOnInsert": {"created_at": now()}},
        upsert=True
    )
    return {"success": True}

# ─── FAVORITES ───────────────────────────────────────────
@api_router.post("/favorites/toggle")
async def toggle_favorite(req: FavoriteToggleRequest, user=Depends(get_current_user)):
    """Toggle a listener as a favorite. Returns new favorited state."""
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Seekers only")
    existing = await db.favorites.find_one(
        {"seeker_id": user["user_id"], "listener_id": req.listener_id}
    )
    if existing:
        await db.favorites.delete_one(
            {"seeker_id": user["user_id"], "listener_id": req.listener_id}
        )
        return {"success": True, "favorited": False}
    await db.favorites.insert_one({
        "id": uid(), "seeker_id": user["user_id"],
        "listener_id": req.listener_id, "created_at": now()
    })
    return {"success": True, "favorited": True}

@api_router.get("/favorites")
async def get_favorites(user=Depends(get_current_user)):
    """Get the current seeker's favorited listener IDs."""
    if user["role"] != "seeker":
        return {"listener_ids": []}
    favs = await db.favorites.find(
        {"seeker_id": user["user_id"]}, {"listener_id": 1, "_id": 0}
    ).to_list(200)
    return {"listener_ids": [f["listener_id"] for f in favs]}

# ─── RATINGS ───────────────────────────────────────────
@api_router.post("/ratings/submit")
async def submit_rating(req: RatingRequest, user=Depends(get_current_user)):
    rating = {
        "id": uid(),
        "call_id": req.call_id,
        "from_user_id": user["user_id"],
        "rating": req.rating,
        "feedback": req.feedback,
        "created_at": now()
    }
    await db.call_ratings.insert_one(rating)
    # Update listener avg rating
    call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if call:
        listener_id = call["listener_id"]
        rating_map = {"great": 5, "good": 4, "okay": 3, "bad": 1}
        all_ratings = await db.call_ratings.find(
            {"call_id": {"$in": [c["id"] async for c in db.calls.find({"listener_id": listener_id}, {"id": 1, "_id": 0})]}},
            {"_id": 0}
        ).to_list(1000)
        if all_ratings:
            avg = sum(rating_map.get(r.get("rating", "okay"), 3) for r in all_ratings) / len(all_ratings)
            await db.listener_profiles.update_one(
                {"user_id": listener_id}, {"$set": {"avg_rating": round(avg, 1)}}
            )

    # ── VIDEO UNLOCK CHECK ─────────────────────────────────────────────────────
    # Unlock video for this seeker-listener pair when:
    #   1. The call was a voice call of at least 5 minutes (300 seconds)
    #   2. Both seeker AND listener give a positive rating (great or good)
    video_unlocked = False
    if call:
        seeker_id = call["seeker_id"]
        listener_id = call["listener_id"]
        positive = {"great", "good"}
        is_positive = req.rating in positive
        is_voice_and_long = (
            call.get("call_type") == "voice" and
            call.get("duration_seconds", 0) >= 300
        )

        if is_positive and is_voice_and_long:
            # Check if the other party has also submitted a positive rating
            other_party_id = listener_id if user["user_id"] == seeker_id else seeker_id
            other_rating = await db.call_ratings.find_one({
                "call_id": req.call_id,
                "from_user_id": other_party_id,
                "rating": {"$in": list(positive)}
            })
            if other_rating:
                # Both gave positive ratings — unlock video for this pair
                existing = await db.video_unlock_pairs.find_one({
                    "seeker_id": seeker_id, "listener_id": listener_id
                })
                if not existing:
                    await db.video_unlock_pairs.insert_one({
                        "id": uid(),
                        "seeker_id": seeker_id,
                        "listener_id": listener_id,
                        "unlocked_at": now(),
                        "unlocked_by_call_id": req.call_id
                    })
                    video_unlocked = True

    return {"success": True, "video_unlocked": video_unlocked}

@api_router.get("/listeners/video-unlock-status")
async def get_video_unlock_status(user=Depends(get_current_user)):
    """Returns listener IDs for which the current seeker has unlocked video calls."""
    if user["role"] != "seeker":
        return {"listener_ids": []}
    pairs = await db.video_unlock_pairs.find(
        {"seeker_id": user["user_id"]}, {"listener_id": 1, "_id": 0}
    ).to_list(200)
    return {"listener_ids": [p["listener_id"] for p in pairs]}

# ─── REPORTS ───────────────────────────────────────────
@api_router.post("/reports/submit")
async def submit_report(req: ReportRequest, user=Depends(get_current_user)):
    report = {
        "id": uid(),
        "reporter_id": user["user_id"],
        "reported_user_id": req.reported_user_id,
        "call_id": req.call_id,
        "reason": req.reason,
        "details": req.details,
        "status": "pending",
        "created_at": now()
    }
    await db.call_reports.insert_one(report)
    # Add risk flag
    await db.risk_flags.insert_one({
        "id": uid(),
        "user_id": req.reported_user_id,
        "flag_type": "user_report",
        "description": req.reason,
        "report_id": report["id"],
        "created_at": now()
    })
    return {"success": True, "message": "Report submitted"}

async def process_seeker_referral_on_recharge(referred_user_id: str):
    """Credit referrer ₹15 when the referred seeker completes their first recharge."""
    referral = await db.seeker_referrals.find_one(
        {"referred_id": referred_user_id, "status": "pending"}
    )
    if not referral:
        return
    # Count prior recharges (the current one is already in the ledger)
    prior_count = await db.wallet_ledger.count_documents({
        "user_id": referred_user_id, "type": "credit",
        "description": {"$regex": "^Recharge"}
    })
    if prior_count > 1:
        return  # Not the first recharge
    await db.wallet_accounts.update_one(
        {"user_id": referral["referrer_id"]}, {"$inc": {"balance": 15}}
    )
    await db.wallet_ledger.insert_one({
        "id": uid(), "user_id": referral["referrer_id"],
        "type": "credit", "amount": 15,
        "description": "Referral bonus - friend recharged for first time",
        "created_at": now()
    })
    await db.seeker_referrals.update_one(
        {"id": referral["id"]},
        {"$set": {"status": "credited", "credited_at": now()}}
    )
    logger.info(f"Seeker referral credited: referrer={referral['referrer_id'][:8]}")

# ─── REFERRAL HELPERS ──────────────────────────────────
# Referral only activates when referred listener completes 30 minutes of calls!
REFERRAL_TIERS = {
    "bronze": {"min_referrals": 0, "max_referrals": 5, "bonus": 50, "commission_rate": 0.05, "commission_days": 15},
    "silver": {"min_referrals": 6, "max_referrals": 15, "bonus": 75, "commission_rate": 0.075, "commission_days": 15},
    "gold": {"min_referrals": 16, "max_referrals": 25, "bonus": 100, "commission_rate": 0.10, "commission_days": 15},
}
REFERRAL_ACTIVATION_MINUTES = 30  # referred listener must complete 30 min talk time to activate
MAX_TOTAL_REFERRALS = 25  # Maximum referrals allowed per listener

def get_referral_tier(successful_referrals: int):
    if successful_referrals >= 16:
        return "gold", REFERRAL_TIERS["gold"]
    elif successful_referrals >= 6:
        return "silver", REFERRAL_TIERS["silver"]
    return "bronze", REFERRAL_TIERS["bronze"]

def generate_referral_code(name: str) -> str:
    return f"{name[:3].upper()}{random.randint(1000, 9999)}"

async def process_referral_commission(listener_id: str, call_earnings: float):
    """Process 5-10% ongoing commission from referred listener's earnings to referrer"""
    referral = await db.referrals.find_one(
        {"referred_id": listener_id, "status": "active"}, {"_id": 0}
    )
    if not referral:
        return
    # Check if commission period expired
    activated_at = datetime.fromisoformat(referral.get("activated_at", now()))
    days_since = (datetime.now(timezone.utc) - activated_at).days
    tier_name, tier = get_referral_tier(
        await db.referrals.count_documents({"referrer_id": referral["referrer_id"], "status": "active"})
    )
    if days_since > tier["commission_days"]:
        return  # Commission period expired
    commission = round(call_earnings * tier["commission_rate"], 2)
    if commission <= 0:
        return
    # Credit commission to referrer's earnings
    await db.listener_earnings.update_one(
        {"user_id": referral["referrer_id"]},
        {"$inc": {"total_earned": commission, "pending_balance": commission}}
    )
    await db.listener_earnings_ledger.insert_one({
        "id": uid(), "user_id": referral["referrer_id"],
        "type": "referral_commission", "amount": commission,
        "description": f"Referral commission ({int(tier['commission_rate']*100)}%) from {referral.get('referred_name', 'referral')}",
        "created_at": now()
    })
    # Track total commission
    await db.referrals.update_one(
        {"id": referral["id"]},
        {"$inc": {"total_commission": commission}}
    )

# ─── TIPS ──────────────────────────────────────────────
@api_router.post("/calls/{call_id}/tip")
async def tip_listener(call_id: str, req: TipRequest, user=Depends(get_current_user)):
    """Seeker sends a tip to the listener after a call ends."""
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Seekers only")
    if req.amount < 5:
        raise HTTPException(status_code=400, detail="Minimum tip is ₹5")
    if req.amount > 500:
        raise HTTPException(status_code=400, detail="Maximum tip is ₹500")

    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call["seeker_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your call")
    if call["status"] != "ended":
        raise HTTPException(status_code=400, detail="Can only tip after a call ends")

    # Idempotency: one tip per call
    existing_tip = await db.wallet_ledger.find_one(
        {"user_id": user["user_id"], "call_id": call_id, "type": "tip_sent"}
    )
    if existing_tip:
        raise HTTPException(status_code=409, detail="Already tipped this call")

    tip_amount = round(req.amount, 2)

    # Atomic debit from seeker wallet
    debit_result = await db.wallet_accounts.update_one(
        {"user_id": user["user_id"], "balance": {"$gte": tip_amount}},
        {"$inc": {"balance": -tip_amount}}
    )
    if debit_result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Insufficient balance for tip")

    # Credit listener earnings
    await db.listener_earnings.update_one(
        {"user_id": call["listener_id"]},
        {"$inc": {"total_earned": tip_amount, "pending_balance": tip_amount}}
    )
    # Ledger entries
    await db.wallet_ledger.insert_one({
        "id": uid(), "user_id": user["user_id"],
        "type": "tip_sent", "amount": tip_amount,
        "description": "Tip sent after call",
        "call_id": call_id, "created_at": now()
    })
    await db.listener_earnings_ledger.insert_one({
        "id": uid(), "user_id": call["listener_id"],
        "type": "tip", "amount": tip_amount,
        "description": "Tip received",
        "call_id": call_id, "created_at": now()
    })
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {
        "success": True,
        "tip_amount": tip_amount,
        "new_balance": wallet.get("balance", 0),
    }

# ─── MATCH REMATCH ─────────────────────────────────────
@api_router.post("/match/rematch")
async def rematch(req: RematchRequest, user=Depends(get_current_user)):
    """
    Find the next best available listener after a call was missed or rejected.
    Excludes the listener who missed/rejected to avoid routing back to them.
    Incorporates answer_rate bonus into scoring.
    """
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Seekers only")

    prev_call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if not prev_call:
        raise HTTPException(status_code=404, detail="Call not found")
    if prev_call["seeker_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your call")
    if prev_call["status"] not in ("missed", "rejected"):
        raise HTTPException(status_code=400, detail="Can only rematch after a missed or rejected call")

    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not wallet or wallet.get("balance", 0) < 5:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    seeker = await db.seeker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not seeker:
        raise HTTPException(status_code=404, detail="Complete onboarding first")

    excluded_listener = prev_call["listener_id"]
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    online = await db.listener_profiles.find(
        {
            "is_online": True,
            "in_call": {"$ne": True},
            "last_online": {"$gte": cutoff},
            "user_id": {"$ne": excluded_listener},
        },
        {"_id": 0}
    ).to_list(50)

    if not online:
        raise HTTPException(status_code=404, detail="No other listeners available right now. Try again shortly.")

    scored = []
    for l in online:
        score = 0
        lang_match = set(seeker.get("languages", [])) & set(l.get("languages", []))
        score += len(lang_match) * 10
        tag_match = set(seeker.get("intent_tags", [])) & set(l.get("topic_tags", []))
        score += len(tag_match) * 3
        if l.get("tier") == "trusted": score += 2
        elif l.get("tier") == "elite": score += 4
        # Answer-rate bonus: strongly prefer listeners who pick up
        score += l.get("answer_rate", 0.5) * 20
        last_matched = l.get("last_matched_at")
        if last_matched:
            try:
                mins_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_matched)).total_seconds() / 60
                score += min(mins_since, 30)
            except Exception:
                score += 15
        else:
            score += 30
        score += random.randint(0, 5)
        scored.append((score, l))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched = scored[0][1]
    await db.listener_profiles.update_one(
        {"user_id": matched["user_id"]}, {"$set": {"last_matched_at": now()}}
    )
    return {"success": True, "listener": matched}

# ─── EARNINGS ──────────────────────────────────────────
@api_router.get("/earnings/dashboard")
async def earnings_dashboard(user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    earnings = await db.listener_earnings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not earnings:
        earnings = {"total_earned": 0, "pending_balance": 0, "withdrawn": 0}
    ledger = await db.listener_earnings_ledger.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"earnings": earnings, "ledger": ledger}

@api_router.post("/earnings/withdraw")
async def withdraw(req: WithdrawRequest, user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    if req.amount < 1000:
        raise HTTPException(status_code=400, detail="Minimum withdrawal ₹1000")
    earnings = await db.listener_earnings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not earnings or earnings.get("pending_balance", 0) < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    await db.listener_earnings.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"pending_balance": -req.amount, "withdrawn": req.amount}}
    )
    await db.withdrawals.insert_one({
        "id": uid(), "user_id": user["user_id"],
        "amount": req.amount, "upi_id": req.upi_id,
        "status": "completed", "created_at": now()  # Instant withdrawal
    })
    return {"success": True, "message": f"₹{req.amount} withdrawn instantly to {req.upi_id}"}

# ─── REFERRAL SYSTEM ──────────────────────────────────
@api_router.get("/referral/my-code")
async def get_my_referral_code(user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    # Get or generate referral code
    ref = await db.referral_codes.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not ref:
        profile = await db.listener_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
        code = generate_referral_code(profile.get("name", "LST") if profile else "LST")
        # Ensure unique
        while await db.referral_codes.find_one({"code": code}):
            code = generate_referral_code(profile.get("name", "LST") if profile else "LST")
        ref = {"user_id": user["user_id"], "code": code, "created_at": now()}
        await db.referral_codes.insert_one(ref)
        ref.pop("_id", None)
    # Get referral stats
    total_referrals = await db.referrals.count_documents({"referrer_id": user["user_id"]})
    active_referrals = await db.referrals.count_documents({"referrer_id": user["user_id"], "status": "active"})
    pending_referrals = await db.referrals.count_documents({"referrer_id": user["user_id"], "status": "pending"})
    tier_name, tier = get_referral_tier(active_referrals)
    # Total commission earned
    pipeline = [
        {"$match": {"referrer_id": user["user_id"]}},
        {"$group": {"_id": None, "total": {"$sum": "$total_commission"}, "bonuses": {"$sum": "$bonus_paid"}}}
    ]
    stats = await db.referrals.aggregate(pipeline).to_list(1)
    total_commission = stats[0]["total"] if stats else 0
    total_bonuses = stats[0]["bonuses"] if stats else 0
    return {
        "code": ref["code"],
        "total_referrals": total_referrals,
        "active_referrals": active_referrals,
        "pending_referrals": pending_referrals,
        "tier": tier_name,
        "bonus_per_referral": tier["bonus"],
        "commission_rate": f"{int(tier['commission_rate']*100)}%",
        "commission_days": tier["commission_days"],
        "total_commission_earned": round(total_commission, 2),
        "total_bonuses_earned": round(total_bonuses, 2),
    }

@api_router.post("/referral/apply")
async def apply_referral_code(req: ApplyReferralRequest, user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    # Rate limit: 3 apply attempts per user per day
    if await check_rate_limit_db("listener_referral_apply", user["user_id"], 3, 1440):
        raise HTTPException(status_code=429, detail="Too many referral code attempts. Try again tomorrow.")
    # Check if already used a referral code
    existing = await db.referrals.find_one({"referred_id": user["user_id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You already used a referral code")
    # Find referrer's code
    ref_code = await db.referral_codes.find_one({"code": req.referral_code.upper()}, {"_id": 0})
    if not ref_code:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if ref_code["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")
    # Device abuse check: reject if referred and referrer share a device
    if await is_same_device(user["user_id"], ref_code["user_id"]):
        raise HTTPException(status_code=400, detail="Referral not allowed from the same device")
    # Check if referrer has hit max referrals (25)
    referrer_total = await db.referrals.count_documents({"referrer_id": ref_code["user_id"]})
    if referrer_total >= MAX_TOTAL_REFERRALS:
        raise HTTPException(status_code=400, detail="This referrer has reached the maximum referral limit")
    # Get names for display
    referrer_profile = await db.listener_profiles.find_one({"user_id": ref_code["user_id"]}, {"_id": 0})
    referred_profile = await db.listener_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    referral = {
        "id": uid(),
        "referrer_id": ref_code["user_id"],
        "referrer_name": referrer_profile.get("name", "Listener") if referrer_profile else "Listener",
        "referred_id": user["user_id"],
        "referred_name": referred_profile.get("name", "Listener") if referred_profile else "Listener",
        "code_used": req.referral_code.upper(),
        "status": "pending",  # pending → active after 30 min talk time
        "total_commission": 0,
        "bonus_paid": 0,
        "created_at": now(),
        "activated_at": None,
    }
    await db.referrals.insert_one(referral)
    return {
        "success": True,
        "message": f"Referral code applied! Your referrer will earn a bonus once you complete {REFERRAL_ACTIVATION_MINUTES} minutes of calls.",
        "referrer_name": referral["referrer_name"]
    }

@api_router.get("/referral/my-referrals")
async def get_my_referrals(user=Depends(get_current_user)):
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    referrals = await db.referrals.find(
        {"referrer_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"referrals": referrals}

# Check and activate pending referrals (called after each call ends)
async def check_referral_activation(listener_id: str):
    """Check if referred listener has hit 30 min talk time (verified from call records) to activate referral."""
    referral = await db.referrals.find_one(
        {"referred_id": listener_id, "status": "pending"}, {"_id": 0}
    )
    if not referral:
        return
    # Compute actual minutes from immutable call records (not the mutable profile stat)
    ended_calls = await db.calls.find(
        {"listener_id": listener_id, "status": "ended", "duration_seconds": {"$gt": 0}},
        {"duration_seconds": 1, "_id": 0}
    ).to_list(2000)
    actual_minutes = sum(c.get("duration_seconds", 0) for c in ended_calls) / 60
    if actual_minutes >= REFERRAL_ACTIVATION_MINUTES:
        # Activate referral!
        active_count = await db.referrals.count_documents({"referrer_id": referral["referrer_id"], "status": "active"})
        tier_name, tier = get_referral_tier(active_count)
        bonus = tier["bonus"]
        await db.referrals.update_one(
            {"id": referral["id"]},
            {"$set": {"status": "active", "activated_at": now(), "bonus_paid": bonus}}
        )
        # Pay referrer the activation bonus
        await db.listener_earnings.update_one(
            {"user_id": referral["referrer_id"]},
            {"$inc": {"total_earned": bonus, "pending_balance": bonus}}
        )
        await db.listener_earnings_ledger.insert_one({
            "id": uid(), "user_id": referral["referrer_id"],
            "type": "referral_bonus", "amount": bonus,
            "description": f"Referral bonus - {referral['referred_name']} activated ({tier_name} tier ₹{bonus})",
            "created_at": now()
        })
        logger.info(f"Referral activated: {referral['referred_name']} → bonus ₹{bonus} to {referral['referrer_name']}")

# ─── KYC VERIFICATION ─────────────────────────────────
# ─── ADVANCED KYC SYSTEM ───────────────────────────────
# Real KYC using Gemini Vision for OCR, document validation,
# face liveness detection, and face matching.

import base64
import re
from datetime import date
import google.generativeai as genai

_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-1.5-flash") if _GEMINI_API_KEY else None


def _image_part(base64_data: str, mime: str = "image/jpeg") -> dict:
    """Build an inline image part for the Gemini API."""
    return {"inline_data": {"mime_type": mime, "data": base64_data}}


async def gemini_ocr_extraction(id_type: str, image_data: str) -> dict:
    """
    Use Gemini Vision to extract name & DOB from an ID document image.
    Also validates that the image is actually a legitimate ID document.
    """
    if not _gemini_model:
        raise HTTPException(status_code=503, detail="KYC service unavailable — Gemini API key not configured")

    prompt = f"""You are a KYC document verification system. Analyze this image carefully.

The user claims this is a **{id_type}** identity document (one of: aadhaar, pan, driving_license, voter_id).

Respond ONLY with a JSON object (no markdown, no code fences) with these fields:
- "is_valid_document": boolean — true ONLY if this image clearly shows a real {id_type} document. false if it's a random photo, screenshot, meme, blank page, or anything that is NOT an actual government-issued ID document.
- "rejection_reason": string or null — if is_valid_document is false, explain why (e.g., "Image does not contain any identity document", "Image is blurry and unreadable", "Document type does not match claimed type").
- "extracted_name": string or null — the full name exactly as printed on the document. null if not readable.
- "extracted_dob": string or null — date of birth in YYYY-MM-DD format exactly as on the document. null if not present or not readable.
- "document_number_last4": string or null — last 4 digits/characters of the document number. null if not readable.
- "confidence": float 0.0 to 1.0 — your overall confidence in the extraction accuracy. Use 0.0 if the document is invalid.

Be strict: if the image is not clearly a {id_type} document, set is_valid_document to false and confidence to 0.0."""

    try:
        response = await asyncio.to_thread(
            _gemini_model.generate_content, [prompt, _image_part(image_data)]
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Gemini OCR parsing error: %s — raw: %s", exc, getattr(response, 'text', ''))
        return {
            "is_valid_document": False,
            "rejection_reason": "Failed to process document image. Please upload a clearer photo.",
            "extracted_name": None,
            "extracted_dob": None,
            "id_type": id_type,
            "confidence": 0.0,
            "ocr_status": "error",
        }

    is_valid = bool(result.get("is_valid_document"))
    confidence = float(result.get("confidence", 0.0))
    name = result.get("extracted_name")
    dob = result.get("extracted_dob")

    # Normalise DOB to YYYY-MM-DD if Gemini returned a slightly different format
    if dob:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                dob = datetime.strptime(dob, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    return {
        "is_valid_document": is_valid,
        "rejection_reason": result.get("rejection_reason"),
        "extracted_name": name,
        "extracted_dob": dob,
        "document_number_last4": result.get("document_number_last4"),
        "id_type": id_type,
        "confidence": round(confidence, 2),
        "ocr_status": "success" if is_valid and confidence >= 0.6 else "low_confidence" if is_valid else "invalid_document",
    }


def check_age_18_plus(dob_str: str) -> dict:
    """Check if person is 18+ based on DOB."""
    if not dob_str:
        return {"age": None, "is_18_plus": False, "verification_status": "dob_not_found"}
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return {
            "age": age,
            "is_18_plus": age >= 18,
            "verification_status": "passed" if age >= 18 else "failed_underage",
        }
    except Exception:
        return {"age": None, "is_18_plus": False, "verification_status": "invalid_dob"}


async def gemini_face_liveness(selfie_data: str) -> dict:
    """
    Use Gemini Vision to detect face presence and liveness from a selfie image.
    Checks for a real human face (not a photo-of-photo, screen, printout, mask, etc.).
    """
    if not _gemini_model:
        raise HTTPException(status_code=503, detail="KYC service unavailable — Gemini API key not configured")

    prompt = """You are a face liveness verification system. Analyze this selfie image carefully.

Respond ONLY with a JSON object (no markdown, no code fences) with these fields:
- "face_detected": boolean — true if a clear human face is visible in the image.
- "face_count": integer — number of faces detected.
- "is_live_person": boolean — true ONLY if this appears to be a real live person taking a selfie. false if it looks like a photo of a photo, a picture of a screen/monitor, a printed photo, a mask, a cartoon, or any non-live representation.
- "liveness_issues": list of strings — any concerns (e.g., "appears to be photo of a screen", "face partially obscured", "multiple faces detected", "image too dark"). Empty list if no issues.
- "face_confidence": float 0.0 to 1.0 — confidence that a real face is clearly visible.
- "liveness_score": float 0.0 to 1.0 — confidence that this is a live person (1.0 = definitely live, 0.0 = definitely fake/spoofed).

Be strict about liveness. Look for signs of spoofing: screen bezels, moiré patterns, reflections, paper edges, unnatural lighting, etc."""

    try:
        response = await asyncio.to_thread(
            _gemini_model.generate_content, [prompt, _image_part(selfie_data)]
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Gemini liveness parsing error: %s", exc)
        return {
            "face_detected": False,
            "face_confidence": 0.0,
            "blink_detected": False,
            "liveness_score": 0.0,
            "liveness_status": "error",
        }

    face_detected = bool(result.get("face_detected"))
    liveness_score = float(result.get("liveness_score", 0.0))

    return {
        "face_detected": face_detected,
        "face_count": result.get("face_count", 0),
        "face_confidence": round(float(result.get("face_confidence", 0.0)), 2),
        "is_live_person": bool(result.get("is_live_person")),
        "liveness_issues": result.get("liveness_issues", []),
        "liveness_score": round(liveness_score, 2),
        "liveness_status": "passed" if liveness_score >= 0.75 else "needs_review",
    }


async def gemini_face_match(id_image_data: str, selfie_data: str) -> dict:
    """
    Use Gemini Vision to compare the face on the ID document with the selfie.
    """
    if not _gemini_model:
        raise HTTPException(status_code=503, detail="KYC service unavailable — Gemini API key not configured")

    prompt = """You are a face matching verification system. You are given two images:
1. First image: An identity document (ID card) that contains a photo of a person.
2. Second image: A selfie taken by a person.

Compare the faces and determine if they are the same person.

Respond ONLY with a JSON object (no markdown, no code fences) with these fields:
- "face_found_in_id": boolean — true if you can see a face/photo on the ID document.
- "face_found_in_selfie": boolean — true if you can see a face in the selfie.
- "is_match": boolean — true if the faces appear to be the same person. Consider that the ID photo may be older, different angle, or different lighting.
- "match_score": float 0.0 to 1.0 — confidence that both images show the same person.
- "mismatch_reasons": list of strings — reasons for doubt (e.g., "different facial structure", "ID photo too small to compare", "very different apparent ages"). Empty list if confident match.

Be reasonably strict but account for normal differences between an ID photo and a live selfie (lighting, angle, aging)."""

    try:
        response = await asyncio.to_thread(
            _gemini_model.generate_content,
            [prompt, _image_part(id_image_data), _image_part(selfie_data)],
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Gemini face match parsing error: %s", exc)
        return {
            "match_score": 0.0,
            "is_match": False,
            "match_status": "error",
        }

    match_score = float(result.get("match_score", 0.0))
    is_match = bool(result.get("is_match", False))

    return {
        "face_found_in_id": bool(result.get("face_found_in_id")),
        "face_found_in_selfie": bool(result.get("face_found_in_selfie")),
        "match_score": round(match_score, 2),
        "is_match": is_match,
        "mismatch_reasons": result.get("mismatch_reasons", []),
        "match_status": "matched" if is_match else "needs_review",
    }


def determine_kyc_result(ocr_result: dict, age_check: dict, face_result: dict, match_result: dict) -> dict:
    """
    Determine final KYC result based on all checks.
    Auto-approve if all checks pass with high confidence.
    Flag for manual review otherwise.
    """
    issues = []

    # Check document validity
    if not ocr_result.get("is_valid_document"):
        issues.append("invalid_document")

    # Check OCR confidence
    if ocr_result.get("confidence", 0) < 0.6:
        issues.append("low_ocr_confidence")

    # Check age verification
    if not age_check.get("is_18_plus"):
        issues.append("underage_or_invalid_dob")

    # Check face detection
    if not face_result.get("face_detected"):
        issues.append("face_not_detected")

    # Check liveness
    if face_result.get("liveness_score", 0) < 0.75:
        issues.append("low_liveness_score")

    if not face_result.get("is_live_person"):
        issues.append("liveness_failed")

    # Check face match
    if not match_result.get("is_match"):
        issues.append("face_mismatch")

    # Determine final status
    if len(issues) == 0:
        return {
            "status": "verified",
            "auto_approved": True,
            "issues": [],
            "message": "KYC verified automatically",
        }
    elif "underage_or_invalid_dob" in issues:
        return {
            "status": "rejected",
            "auto_approved": False,
            "issues": issues,
            "message": "KYC rejected: Must be 18+ to use this platform",
        }
    elif "invalid_document" in issues:
        return {
            "status": "rejected",
            "auto_approved": False,
            "issues": issues,
            "message": "KYC rejected: Uploaded image is not a valid identity document",
        }
    else:
        return {
            "status": "pending_review",
            "auto_approved": False,
            "issues": issues,
            "message": "KYC flagged for manual review",
        }

@api_router.post("/kyc/upload-id")
async def upload_kyc_id(req: KYCUploadIDRequest, user=Depends(get_current_user)):
    """Step 1: Upload ID document and extract data via Gemini Vision OCR"""
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")

    # Check if already verified
    existing = await db.kyc_submissions.find_one({"user_id": user["user_id"]})
    if existing and existing.get("status") == "verified":
        raise HTTPException(status_code=400, detail="KYC already verified")

    # Validate ID type
    valid_types = ["aadhaar", "pan", "driving_license", "voter_id"]
    if req.id_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid ID type. Must be one of: {valid_types}")

    # Real OCR extraction via Gemini Vision
    ocr_result = await gemini_ocr_extraction(req.id_type, req.id_image_base64)

    # Reject immediately if the image is not a valid document
    if not ocr_result.get("is_valid_document"):
        reason = ocr_result.get("rejection_reason") or "Uploaded image is not a valid identity document."
        return {
            "success": False,
            "step": 0,
            "extracted_data": None,
            "age_verification": None,
            "next_step": None,
            "message": reason,
        }

    # Reject if name or DOB could not be extracted
    if not ocr_result.get("extracted_name") or not ocr_result.get("extracted_dob"):
        return {
            "success": False,
            "step": 0,
            "extracted_data": {
                "name": ocr_result.get("extracted_name"),
                "dob": ocr_result.get("extracted_dob"),
                "confidence": ocr_result.get("confidence", 0),
            },
            "age_verification": None,
            "next_step": None,
            "message": "Could not read name or date of birth from the document. Please upload a clearer photo.",
        }

    # Check age from extracted DOB
    age_check = check_age_18_plus(ocr_result["extracted_dob"])

    # Store KYC step 1 data — keep full image for face matching later
    kyc_data = {
        "user_id": user["user_id"],
        "step": 1,
        "id_type": req.id_type,
        "id_image": req.id_image_base64,
        "ocr_result": ocr_result,
        "age_check": age_check,
        "status": "id_uploaded",
        "updated_at": now(),
    }

    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]},
        {"$set": kyc_data},
        upsert=True,
    )

    # Update profile status
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"kyc_status": "in_progress"}},
    )

    return {
        "success": True,
        "step": 1,
        "extracted_data": {
            "name": ocr_result["extracted_name"],
            "dob": ocr_result["extracted_dob"],
            "confidence": ocr_result["confidence"],
        },
        "age_verification": age_check,
        "next_step": "upload_selfie" if age_check["is_18_plus"] else None,
        "message": "ID processed. Please verify extracted data." if age_check["is_18_plus"] else "Age verification failed. Must be 18+",
    }

@api_router.post("/kyc/confirm-id-data")
async def confirm_kyc_id_data(user=Depends(get_current_user)):
    """Step 2: User confirms extracted ID data before proceeding"""
    kyc = await db.kyc_submissions.find_one({"user_id": user["user_id"]})
    if not kyc or kyc.get("step") != 1:
        raise HTTPException(status_code=400, detail="Please upload ID first")
    
    if not kyc.get("age_check", {}).get("is_18_plus"):
        raise HTTPException(status_code=400, detail="Age verification failed")
    
    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"step": 2, "id_confirmed": True, "status": "id_confirmed", "updated_at": now()}}
    )
    
    return {
        "success": True,
        "step": 2,
        "message": "ID data confirmed. Please upload selfie video for liveness check.",
        "next_step": "upload_selfie"
    }

@api_router.post("/kyc/upload-selfie")
async def upload_kyc_selfie(req: KYCSelfieVideoRequest, user=Depends(get_current_user)):
    """Step 3: Upload selfie for face detection, liveness check, and face matching"""
    kyc = await db.kyc_submissions.find_one({"user_id": user["user_id"]})
    if not kyc:
        raise HTTPException(status_code=400, detail="Please upload ID first")

    if kyc.get("status") == "verified":
        raise HTTPException(status_code=400, detail="KYC already verified")

    # Run liveness detection and face matching in parallel via Gemini Vision
    id_image = kyc.get("id_image", "")
    face_result, match_result = await asyncio.gather(
        gemini_face_liveness(req.video_base64),
        gemini_face_match(id_image, req.video_base64),
    )

    # Determine final KYC result
    final_result = determine_kyc_result(
        kyc.get("ocr_result", {}),
        kyc.get("age_check", {}),
        face_result,
        match_result,
    )

    # Update KYC with all results (don't store full selfie image, just a truncated ref)
    update_data = {
        "step": 3,
        "selfie_data": req.video_base64[:100] + "...",
        "face_detection": face_result,
        "face_match": match_result,
        "final_result": final_result,
        "status": final_result["status"],
        "completed_at": now(),
        "updated_at": now(),
    }

    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]},
        {"$set": update_data},
    )

    # Update profile KYC status
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"kyc_status": final_result["status"]}},
    )

    return {
        "success": True,
        "step": 3,
        "face_detection": {
            "face_detected": face_result.get("face_detected", False),
            "liveness_passed": face_result.get("liveness_score", 0) >= 0.75,
            "is_live_person": face_result.get("is_live_person", False),
            "liveness_issues": face_result.get("liveness_issues", []),
        },
        "face_match": {
            "match_score": match_result.get("match_score", 0),
            "matched": match_result.get("is_match", False),
            "mismatch_reasons": match_result.get("mismatch_reasons", []),
        },
        "final_result": final_result,
        "message": final_result["message"],
    }

@api_router.get("/kyc/status")
async def get_kyc_status(user=Depends(get_current_user)):
    """Get detailed KYC status and progress"""
    kyc = await db.kyc_submissions.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not kyc:
        return {
            "status": "not_started",
            "step": 0,
            "message": "KYC not started. Please upload your ID to begin.",
            "steps_completed": []
        }
    
    steps_completed = []
    if kyc.get("step", 0) >= 1:
        steps_completed.append({"step": 1, "name": "ID Upload", "status": "completed"})
    if kyc.get("id_confirmed"):
        steps_completed.append({"step": 2, "name": "Data Confirmation", "status": "completed"})
    if kyc.get("step", 0) >= 3:
        steps_completed.append({"step": 3, "name": "Selfie Verification", "status": "completed"})
    
    return {
        "status": kyc.get("status", "pending"),
        "step": kyc.get("step", 0),
        "extracted_data": kyc.get("ocr_result"),
        "age_verification": kyc.get("age_check"),
        "face_detection": kyc.get("face_detection"),
        "face_match": kyc.get("face_match"),
        "final_result": kyc.get("final_result"),
        "steps_completed": steps_completed,
        "updated_at": kyc.get("updated_at"),
        "message": kyc.get("final_result", {}).get("message", "KYC in progress")
    }

# Legacy endpoint for backward compatibility
@api_router.post("/kyc/submit")
async def submit_kyc(req: KYCSubmitRequest, user=Depends(get_current_user)):
    """Legacy KYC submit - redirects to new flow"""
    if user["role"] != "listener":
        raise HTTPException(status_code=403, detail="Listeners only")
    existing = await db.kyc_submissions.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if existing and existing.get("status") == "verified":
        raise HTTPException(status_code=400, detail="KYC already verified")
    kyc = {
        "id": uid(), "user_id": user["user_id"],
        "full_name": req.full_name,
        "aadhaar_last4": req.aadhaar_last4,
        "pan_number": req.pan_number,
        "dob": req.dob,
        "status": "submitted",
        "submitted_at": now(),
        "verified_at": None,
    }
    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]}, {"$set": kyc}, upsert=True
    )
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]}, {"$set": {"kyc_status": "submitted"}}
    )
    return {"success": True, "message": "KYC submitted for verification", "status": "submitted"}

# ─── SEEKER REFERRAL SYSTEM ───────────────────────────
@api_router.get("/seeker-referral/my-code")
async def get_seeker_referral_code(user=Depends(get_current_user)):
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Seekers only")
    ref = await db.seeker_referral_codes.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not ref:
        profile = await db.seeker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
        code = generate_referral_code(profile.get("name", "SKR") if profile else "SKR")
        while await db.seeker_referral_codes.find_one({"code": code}):
            code = generate_referral_code(profile.get("name", "SKR") if profile else "SKR")
        ref = {"user_id": user["user_id"], "code": code, "created_at": now()}
        await db.seeker_referral_codes.insert_one(ref)
        ref.pop("_id", None)
    total_refs = await db.seeker_referrals.count_documents({"referrer_id": user["user_id"]})
    total_credits = await db.seeker_referrals.count_documents({"referrer_id": user["user_id"], "status": "credited"})
    return {
        "code": ref["code"],
        "total_referrals": total_refs,
        "credited_referrals": total_credits,
        "credits_earned": total_credits * 15,
        "credits_per_referral": 15,
    }

@api_router.post("/seeker-referral/apply")
async def apply_seeker_referral(req: SeekerApplyReferralRequest, user=Depends(get_current_user)):
    if user["role"] != "seeker":
        raise HTTPException(status_code=403, detail="Seekers only")
    # Rate limit: 3 attempts per user per day
    if await check_rate_limit_db("seeker_referral_apply", user["user_id"], 3, 1440):
        raise HTTPException(status_code=429, detail="Too many referral code attempts. Try again tomorrow.")
    existing = await db.seeker_referrals.find_one({"referred_id": user["user_id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You already used a referral code")
    ref_code = await db.seeker_referral_codes.find_one({"code": req.referral_code.upper()}, {"_id": 0})
    if not ref_code:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if ref_code["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own code")
    # Device abuse check: same device as referrer = reject
    if await is_same_device(user["user_id"], ref_code["user_id"]):
        raise HTTPException(status_code=400, detail="Referral not allowed from the same device")
    # Anti-abuse: do NOT credit immediately. Credit fires on referred user's first recharge.
    await db.seeker_referrals.insert_one({
        "id": uid(), "referrer_id": ref_code["user_id"],
        "referred_id": user["user_id"], "code_used": req.referral_code.upper(),
        "status": "pending", "created_at": now()
    })
    return {
        "success": True,
        "message": "Referral code applied! Your friend will earn ₹15 credits when you complete your first recharge."
    }

# ─── CALL RECORDINGS ──────────────────────────────────
@api_router.get("/recordings/list")
async def list_recordings(user=Depends(get_current_user)):
    recordings = await db.call_recordings.find(
        {"$or": [{"seeker_id": user["user_id"]}, {"listener_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"recordings": recordings}

# ─── ADMIN ─────────────────────────────────────────────
@api_router.get("/admin/dashboard")
async def admin_dashboard():
    total_users = await db.users.count_documents({})
    total_seekers = await db.users.count_documents({"role": "seeker"})
    total_listeners = await db.users.count_documents({"role": "listener"})
    online_listeners = await db.listener_profiles.count_documents({"is_online": True})
    total_calls = await db.calls.count_documents({})
    active_calls = await db.calls.count_documents({"status": "active"})
    total_reports = await db.call_reports.count_documents({})
    pending_reports = await db.call_reports.count_documents({"status": "pending"})
    # Revenue calc
    pipeline = [{"$match": {"type": "debit"}}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    rev = await db.wallet_ledger.aggregate(pipeline).to_list(1)
    revenue = rev[0]["total"] if rev else 0
    return {
        "total_users": total_users,
        "total_seekers": total_seekers,
        "total_listeners": total_listeners,
        "online_listeners": online_listeners,
        "total_calls": total_calls,
        "active_calls": active_calls,
        "total_reports": total_reports,
        "pending_reports": pending_reports,
        "revenue": round(revenue, 2)
    }

@api_router.get("/admin/moderation-queue")
async def moderation_queue():
    reports = await db.call_reports.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"reports": reports}

@api_router.get("/admin/users")
async def admin_users():
    users = await db.users.find({}, {"_id": 0}).to_list(100)
    return {"users": users}

# ─── SEED DATA ─────────────────────────────────────────
@api_router.post("/seed")
async def seed_data():
    existing = await db.listener_profiles.count_documents({})
    if existing > 0:
        return {"message": "Data already seeded", "listeners": existing}

    avatars = [
        {"id": "avatar_1", "name": "Priya", "image": "priya"},
        {"id": "avatar_2", "name": "Ananya", "image": "ananya"},
        {"id": "avatar_3", "name": "Riya", "image": "riya"},
        {"id": "avatar_4", "name": "Meera", "image": "meera"},
        {"id": "avatar_5", "name": "Kavya", "image": "kavya"},
        {"id": "avatar_6", "name": "Neha", "image": "neha"},
        {"id": "avatar_7", "name": "Simran", "image": "simran"},
        {"id": "avatar_8", "name": "Diya", "image": "diya"},
    ]
    all_languages = ["Hindi", "English", "Tamil", "Telugu", "Bengali", "Marathi"]
    style_tags = ["Friendly", "Calm", "Funny", "Caring", "Motivating", "Spiritual"]
    topic_tags = ["Life", "Career", "Relationships", "Stress", "Fun Chat", "Movies", "Music", "Travel", "Health", "Study"]

    for i, av in enumerate(avatars):
        user_id = uid()
        langs = random.sample(all_languages, random.randint(1, 3))
        if "Hindi" not in langs:
            langs.append("Hindi")
        s_tags = random.sample(style_tags, random.randint(2, 3))
        t_tags = random.sample(topic_tags, random.randint(3, 5))
        user = {
            "id": user_id, "phone": f"+9198765432{i:02d}",
            "role": "listener", "onboarded": True,
            "name": av["name"], "created_at": now()
        }
        await db.users.insert_one(user)
        profile = {
            "user_id": user_id, "name": av["name"],
            "age": random.randint(20, 28),
            "languages": langs, "avatar_id": av["id"],
            "style_tags": s_tags, "topic_tags": t_tags,
            "boundary_answers": [1, 1, 0, 1, 0],
            "is_online": random.choice([True, True, True, False]),
            "last_online": now(),
            "in_call": False, "tier": random.choice(["new", "trusted", "trusted", "elite"]),
            "total_calls": random.randint(10, 200),
            "total_minutes": random.randint(100, 3000),
            "avg_rating": round(random.uniform(3.5, 4.9), 1),
            "created_at": now()
        }
        await db.listener_profiles.insert_one(profile)
        await db.listener_earnings.insert_one({
            "user_id": user_id, "total_earned": random.randint(500, 5000),
            "pending_balance": random.randint(100, 2000), "withdrawn": random.randint(0, 3000),
            "created_at": now()
        })
    # Seed avatars collection
    await db.avatars.delete_many({})
    for av in avatars:
        await db.avatars.insert_one(av)

    return {"message": "Seeded 8 listeners", "success": True}

@api_router.get("/avatars")
async def get_avatars():
    avatars = await db.avatars.find({}, {"_id": 0}).to_list(20)
    if not avatars:
        avatars = [
            {"id": "avatar_1", "name": "Priya", "image": "priya"},
            {"id": "avatar_2", "name": "Ananya", "image": "ananya"},
            {"id": "avatar_3", "name": "Riya", "image": "riya"},
            {"id": "avatar_4", "name": "Meera", "image": "meera"},
            {"id": "avatar_5", "name": "Kavya", "image": "kavya"},
            {"id": "avatar_6", "name": "Neha", "image": "neha"},
            {"id": "avatar_7", "name": "Simran", "image": "simran"},
            {"id": "avatar_8", "name": "Diya", "image": "diya"},
        ]
    return {"avatars": avatars}

@api_router.get("/users/me")
async def get_me(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["user_id"]}, {"_id": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

# ─── WEBSOCKET ─────────────────────────────────────────
@app.websocket("/ws/{user_id}")
async def user_ws_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None),
):
    """
    Persistent WebSocket for any authenticated user (listeners and seekers).
    Connect as: ws://<host>/ws/<user_id>?token=<jwt>

    Server events pushed to listeners:
      {"event": "incoming_call", "call_id": "...", "caller_name": "...", "call_type": "voice|video"}

    Server events pushed to seekers:
      {"event": "call_accepted", "call_id": "...", "connected_at": "..."}
      {"event": "call_rejected", "call_id": "..."}

    Client keeps connection alive by sending "ping"; server replies "pong".
    Server sends "keepalive" every 60 s of inactivity.
    """
    await websocket.accept()

    # Token validation
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("user_id") != user_id:
                await websocket.close(code=4003, reason="Forbidden")
                return
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return
    else:
        await websocket.close(code=4001, reason="Missing token")
        return

    _active_ws[user_id] = websocket
    logger.info(f"WS connected: {user_id[:8]}")
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("keepalive")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error {user_id[:8]}: {e}")
    finally:
        _active_ws.pop(user_id, None)
        logger.info(f"WS disconnected: {user_id[:8]}")

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("Konnectra API started")
    # Auto-seed on startup
    existing = await db.listener_profiles.count_documents({})
    if existing == 0:
        logger.info("Seeding initial data...")
        # Seed inline
        avatars_data = [
            {"id": "avatar_1", "name": "Priya", "image": "priya"},
            {"id": "avatar_2", "name": "Ananya", "image": "ananya"},
            {"id": "avatar_3", "name": "Riya", "image": "riya"},
            {"id": "avatar_4", "name": "Meera", "image": "meera"},
            {"id": "avatar_5", "name": "Kavya", "image": "kavya"},
            {"id": "avatar_6", "name": "Neha", "image": "neha"},
            {"id": "avatar_7", "name": "Simran", "image": "simran"},
            {"id": "avatar_8", "name": "Diya", "image": "diya"},
        ]
        all_langs = ["Hindi", "English", "Tamil", "Telugu", "Bengali", "Marathi"]
        s_tags = ["Friendly", "Calm", "Funny", "Caring", "Motivating", "Spiritual"]
        t_tags = ["Life", "Career", "Relationships", "Stress", "Fun Chat", "Movies", "Music", "Travel", "Health", "Study"]
        for i, av in enumerate(avatars_data):
            user_id = uid()
            langs = random.sample(all_langs, random.randint(1, 3))
            if "Hindi" not in langs:
                langs.append("Hindi")
            stags = random.sample(s_tags, random.randint(2, 3))
            ttags = random.sample(t_tags, random.randint(3, 5))
            await db.users.insert_one({
                "id": user_id, "phone": f"+9198765432{i:02d}",
                "role": "listener", "onboarded": True,
                "name": av["name"], "created_at": now()
            })
            await db.listener_profiles.insert_one({
                "user_id": user_id, "name": av["name"],
                "age": random.randint(20, 28),
                "languages": langs, "avatar_id": av["id"],
                "style_tags": stags, "topic_tags": ttags,
                "boundary_answers": [1, 1, 0, 1, 0],
                "is_online": random.choice([True, True, True, False]),
                "last_online": now(),
                "in_call": False, "tier": random.choice(["new", "trusted", "trusted", "elite"]),
                "total_calls": random.randint(10, 200),
                "total_minutes": random.randint(100, 3000),
                "avg_rating": round(random.uniform(3.5, 4.9), 1),
                "created_at": now()
            })
            await db.listener_earnings.insert_one({
                "user_id": user_id, "total_earned": random.randint(500, 5000),
                "pending_balance": random.randint(100, 2000), "withdrawn": random.randint(0, 3000),
                "created_at": now()
            })
        await db.avatars.delete_many({})
        for av in avatars_data:
            await db.avatars.insert_one(av)
        logger.info("Seeded 8 listeners successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
