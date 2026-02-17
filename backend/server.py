from fastapi import FastAPI, APIRouter, HTTPException, Depends
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# ─── AUTH ──────────────────────────────────────────────
@api_router.post("/auth/send-otp")
async def send_otp(req: OTPRequest):
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
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"is_online": True, "last_online": now()}}
    )
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
        # Calculate listener earnings (₹3/min voice, ₹5/min video)
        rate = 5 if call.get("is_video") else 3
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
    listeners = await db.listener_profiles.find(
        {"is_online": True}, {"_id": 0}
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
    online = await db.listener_profiles.find(
        {"is_online": True, "in_call": {"$ne": True}}, {"_id": 0}
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
    rate = 1 if is_first_call else (5 if req.call_type == "voice" else 8)
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
        {"user_id": user["user_id"]}, {"$set": {"in_call": True}}
    )
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
    # Clean up HMS resources
    if call.get("hms_room_id"):
        await end_hms_room(call["hms_room_id"])
        await db.hms_call_tokens.delete_many({"call_id": req.call_id})
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
                normal_rate = 5 if call["call_type"] == "voice" else 8
                cost += ((duration - 300) / 60) * normal_rate
        else:
            # Standard billing: full first minute charge + per-second after
            cost = rate  # first minute flat charge
            if duration > 60:
                cost += ((duration - 60) / 60) * rate
        cost = round(cost, 2)

    await db.calls.update_one({"id": req.call_id}, {"$set": {
        "status": "ended",
        "ended_at": ended.isoformat(),
        "duration_seconds": duration,
        "cost": cost
    }})

    earnings = 0
    if cost > 0:
        # Deduct from seeker wallet
        await db.wallet_accounts.update_one(
            {"user_id": call["seeker_id"]},
            {"$inc": {"balance": -cost}}
        )
        await db.wallet_ledger.insert_one({
            "id": uid(), "user_id": call["seeker_id"],
            "type": "debit", "amount": cost,
            "description": f"Call ({call['call_type']}) - {duration}s",
            "call_id": req.call_id, "created_at": now()
        })
        # Credit listener earnings
        listener_rate = 3 if call["call_type"] == "voice" else 5
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
    packs = {"pack_99": 99, "pack_299": 299, "pack_699": 699}
    amount = packs.get(req.pack_id)
    if not amount:
        raise HTTPException(status_code=400, detail="Invalid pack")
    # Mocked payment - always success
    await db.wallet_accounts.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": amount}},
        upsert=True
    )
    await db.wallet_ledger.insert_one({
        "id": uid(), "user_id": user["user_id"],
        "type": "credit", "amount": amount,
        "description": f"Recharge ₹{amount}", "created_at": now()
    })
    wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"success": True, "new_balance": wallet.get("balance", 0)}

@api_router.get("/wallet/transactions")
async def get_transactions(user=Depends(get_current_user)):
    txns = await db.wallet_ledger.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"transactions": txns}

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
    return {"success": True}

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
    """Check if referred listener has hit 30 min talk time to activate referral"""
    referral = await db.referrals.find_one(
        {"referred_id": listener_id, "status": "pending"}, {"_id": 0}
    )
    if not referral:
        return
    profile = await db.listener_profiles.find_one({"user_id": listener_id}, {"_id": 0})
    if not profile:
        return
    if profile.get("total_minutes", 0) >= REFERRAL_ACTIVATION_MINUTES:
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
# Zero-cost KYC with simulated OCR, face detection, and liveness checks
# Can be upgraded to real APIs (AWS Rekognition, Google Vision) later

import base64
import re
from datetime import date

def simulate_ocr_extraction(id_type: str, image_data: str) -> dict:
    """
    Simulates OCR extraction from ID document.
    In production, replace with Google Vision API or AWS Textract.
    Returns extracted name, DOB, and confidence score.
    """
    # Simulate processing delay would happen in real OCR
    # For demo, generate realistic extracted data based on image size
    image_size = len(image_data)
    
    # Simulate different confidence levels based on image quality (size as proxy)
    if image_size > 50000:  # Good quality image
        confidence = random.uniform(0.85, 0.98)
    elif image_size > 20000:  # Medium quality
        confidence = random.uniform(0.70, 0.85)
    else:  # Low quality
        confidence = random.uniform(0.50, 0.70)
    
    # Simulated extracted data (in production, this comes from OCR)
    sample_names = ["Priya Sharma", "Ananya Gupta", "Riya Patel", "Meera Singh", "Kavya Reddy"]
    sample_dobs = ["1998-05-15", "1999-08-22", "2000-01-10", "1997-12-03", "2001-06-28"]
    
    idx = image_size % len(sample_names)
    
    return {
        "extracted_name": sample_names[idx],
        "extracted_dob": sample_dobs[idx],
        "id_type": id_type,
        "confidence": round(confidence, 2),
        "ocr_status": "success" if confidence > 0.6 else "low_confidence"
    }

def check_age_18_plus(dob_str: str) -> dict:
    """Check if person is 18+ based on DOB"""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return {
            "age": age,
            "is_18_plus": age >= 18,
            "verification_status": "passed" if age >= 18 else "failed_underage"
        }
    except:
        return {"age": None, "is_18_plus": False, "verification_status": "invalid_dob"}

def simulate_face_detection(video_data: str) -> dict:
    """
    Simulates face detection and liveness check from selfie video.
    In production, replace with AWS Rekognition or similar.
    """
    data_size = len(video_data)
    
    # Simulate face detection confidence
    face_confidence = random.uniform(0.75, 0.99)
    
    # Simulate blink detection (liveness)
    blink_detected = random.random() > 0.15  # 85% success rate
    
    # Simulate liveness score
    liveness_score = random.uniform(0.70, 0.98) if blink_detected else random.uniform(0.30, 0.60)
    
    return {
        "face_detected": face_confidence > 0.7,
        "face_confidence": round(face_confidence, 2),
        "blink_detected": blink_detected,
        "liveness_score": round(liveness_score, 2),
        "liveness_status": "passed" if liveness_score > 0.75 else "needs_review"
    }

def simulate_face_match(id_image_data: str, selfie_data: str) -> dict:
    """
    Simulates face matching between ID photo and selfie.
    In production, replace with AWS Rekognition CompareFaces.
    """
    # Simulate matching based on data characteristics
    combined_size = len(id_image_data) + len(selfie_data)
    
    # Simulate match score
    match_score = random.uniform(0.65, 0.99)
    
    # Higher threshold for auto-approval
    is_match = match_score > 0.80
    
    return {
        "match_score": round(match_score, 2),
        "is_match": is_match,
        "match_status": "matched" if is_match else "needs_review"
    }

def determine_kyc_result(ocr_result: dict, age_check: dict, face_result: dict, match_result: dict) -> dict:
    """
    Determine final KYC result based on all checks.
    Auto-approve if all checks pass with high confidence.
    Flag for manual review otherwise.
    """
    issues = []
    
    # Check OCR confidence
    if ocr_result["confidence"] < 0.75:
        issues.append("low_ocr_confidence")
    
    # Check age verification
    if not age_check["is_18_plus"]:
        issues.append("underage_or_invalid_dob")
    
    # Check face detection
    if not face_result["face_detected"]:
        issues.append("face_not_detected")
    
    # Check liveness
    if face_result["liveness_score"] < 0.75:
        issues.append("low_liveness_score")
    
    # Check face match
    if not match_result["is_match"]:
        issues.append("face_mismatch")
    
    # Determine final status
    if len(issues) == 0:
        return {
            "status": "verified",
            "auto_approved": True,
            "issues": [],
            "message": "KYC verified automatically"
        }
    elif "underage_or_invalid_dob" in issues:
        return {
            "status": "rejected",
            "auto_approved": False,
            "issues": issues,
            "message": "KYC rejected: Must be 18+ to use this platform"
        }
    else:
        return {
            "status": "pending_review",
            "auto_approved": False,
            "issues": issues,
            "message": "KYC flagged for manual review"
        }

@api_router.post("/kyc/upload-id")
async def upload_kyc_id(req: KYCUploadIDRequest, user=Depends(get_current_user)):
    """Step 1: Upload ID document and extract data via OCR"""
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
    
    # Simulate OCR extraction
    ocr_result = simulate_ocr_extraction(req.id_type, req.id_image_base64)
    
    # Check age from extracted DOB
    age_check = check_age_18_plus(ocr_result["extracted_dob"])
    
    # Store KYC step 1 data
    kyc_data = {
        "user_id": user["user_id"],
        "step": 1,
        "id_type": req.id_type,
        "id_image": req.id_image_base64[:100] + "...",  # Store truncated for demo
        "ocr_result": ocr_result,
        "age_check": age_check,
        "status": "id_uploaded",
        "updated_at": now()
    }
    
    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]},
        {"$set": kyc_data},
        upsert=True
    )
    
    # Update profile status
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"kyc_status": "in_progress"}}
    )
    
    return {
        "success": True,
        "step": 1,
        "extracted_data": {
            "name": ocr_result["extracted_name"],
            "dob": ocr_result["extracted_dob"],
            "confidence": ocr_result["confidence"]
        },
        "age_verification": age_check,
        "next_step": "upload_selfie" if age_check["is_18_plus"] else None,
        "message": "ID processed. Please verify extracted data." if age_check["is_18_plus"] else "Age verification failed. Must be 18+"
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
    """Step 3: Upload selfie video for face detection and liveness check"""
    kyc = await db.kyc_submissions.find_one({"user_id": user["user_id"]})
    if not kyc:
        raise HTTPException(status_code=400, detail="Please upload ID first")
    
    if kyc.get("status") == "verified":
        raise HTTPException(status_code=400, detail="KYC already verified")
    
    # Simulate face detection and liveness
    face_result = simulate_face_detection(req.video_base64)
    
    # Simulate face matching with ID photo
    id_image = kyc.get("id_image", "")
    match_result = simulate_face_match(id_image, req.video_base64)
    
    # Determine final KYC result
    final_result = determine_kyc_result(
        kyc.get("ocr_result", {}),
        kyc.get("age_check", {}),
        face_result,
        match_result
    )
    
    # Update KYC with all results
    update_data = {
        "step": 3,
        "selfie_data": req.video_base64[:100] + "...",  # Store truncated
        "face_detection": face_result,
        "face_match": match_result,
        "final_result": final_result,
        "status": final_result["status"],
        "completed_at": now(),
        "updated_at": now()
    }
    
    await db.kyc_submissions.update_one(
        {"user_id": user["user_id"]},
        {"$set": update_data}
    )
    
    # Update profile KYC status
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"kyc_status": final_result["status"]}}
    )
    
    return {
        "success": True,
        "step": 3,
        "face_detection": {
            "face_detected": face_result["face_detected"],
            "liveness_passed": face_result["liveness_score"] > 0.75
        },
        "face_match": {
            "match_score": match_result["match_score"],
            "matched": match_result["is_match"]
        },
        "final_result": final_result,
        "message": final_result["message"]
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
    existing = await db.seeker_referrals.find_one({"referred_id": user["user_id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You already used a referral code")
    ref_code = await db.seeker_referral_codes.find_one({"code": req.referral_code.upper()}, {"_id": 0})
    if not ref_code:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if ref_code["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own code")
    # Credit ₹15 to the referrer immediately
    await db.wallet_accounts.update_one(
        {"user_id": ref_code["user_id"]},
        {"$inc": {"balance": 15}}
    )
    await db.wallet_ledger.insert_one({
        "id": uid(), "user_id": ref_code["user_id"],
        "type": "credit", "amount": 15,
        "description": "Referral bonus - friend joined", "created_at": now()
    })
    await db.seeker_referrals.insert_one({
        "id": uid(), "referrer_id": ref_code["user_id"],
        "referred_id": user["user_id"], "code_used": req.referral_code.upper(),
        "status": "credited", "created_at": now()
    })
    return {"success": True, "message": "Referral applied! Your friend earned ₹15 credits."}

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
