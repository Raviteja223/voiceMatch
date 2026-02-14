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
from datetime import datetime, timezone, timedelta
import requests
from uuid import uuid4

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = "voicematch-secret-key-2024"
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)
HMS_TEMPLATE_ID = os.getenv("HMS_TEMPLATE_ID", "")
HMS_MANAGEMENT_TOKEN = os.getenv("HMS_MANAGEMENT_TOKEN", "")
HMS_ACCESS_KEY = os.getenv("HMS_ACCESS_KEY", "")
HMS_SECRET_KEY = os.getenv("HMS_SECRET_KEY", "")
HMS_API_BASE = os.getenv("HMS_API_BASE", "https://api.100ms.live/v2")
HMS_TOKEN_ROLE = os.getenv("HMS_TOKEN_ROLE", "host")

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

class RechargeRequest(BaseModel):
    pack_id: str

class CallStartRequest(BaseModel):
    listener_id: str
    call_type: str = "voice"

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

def _build_hms_management_token() -> str:
    """Returns a usable 100ms management token from env configuration."""
    if HMS_MANAGEMENT_TOKEN:
        return HMS_MANAGEMENT_TOKEN

    if HMS_ACCESS_KEY and HMS_SECRET_KEY:
        issued_at = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "access_key": HMS_ACCESS_KEY,
            "type": "management",
            "version": 2,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": issued_at + 24 * 60 * 60,
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, HMS_SECRET_KEY, algorithm="HS256")

    return ""


def create_100ms_session(call_id: str, call_type: str):
    """Create a 100ms room + room code + room token for the call."""
    if not HMS_TEMPLATE_ID:
        logger.info("HMS_TEMPLATE_ID missing; continuing with simulated call flow")
        return None

    management_token = _build_hms_management_token()
    if not management_token:
        logger.info("100ms credentials missing; set HMS_MANAGEMENT_TOKEN or HMS_ACCESS_KEY/HMS_SECRET_KEY")
        return None

    headers = {
        "Authorization": f"Bearer {management_token}",
        "Content-Type": "application/json",
    }
    room_name = f"voicematch-{call_type}-{call_id[:8]}"

    try:
        room_res = requests.post(
            f"{HMS_API_BASE}/rooms",
            headers=headers,
            json={
                "name": room_name,
                "description": "VoiceMatch call room",
                "template_id": HMS_TEMPLATE_ID,
            },
            timeout=10,
        )
        room_res.raise_for_status()
        room_id = room_res.json().get("id")
        if not room_id:
            logger.warning("100ms room setup failed: room id missing in response")
            return None

        code_res = requests.post(
            f"{HMS_API_BASE}/room-codes/room/{room_id}",
            headers=headers,
            timeout=10,
        )
        code_res.raise_for_status()
        room_code = code_res.json().get("code")

        token_res = requests.post(
            f"{HMS_API_BASE}/room-tokens",
            headers=headers,
            json={
                "room_id": room_id,
                "role": HMS_TOKEN_ROLE,
                "user_id": f"vm-{call_id}",
            },
            timeout=10,
        )
        token_res.raise_for_status()
        auth_token = token_res.json().get("token")

        return {
            "room_id": room_id,
            "room_name": room_name,
            "room_code": room_code,
            "auth_token": auth_token,
            "enabled": True,
        }
    except requests.RequestException as exc:
        logger.warning("100ms room setup failed: %s", exc)
        return None

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
    # Create wallet
    existing_wallet = await db.wallet_accounts.find_one({"user_id": user["user_id"]})
    if not existing_wallet:
        await db.wallet_accounts.insert_one({
            "user_id": user["user_id"],
            "balance": 50,  # Welcome bonus
            "created_at": now()
        })
        await db.wallet_ledger.insert_one({
            "id": uid(), "user_id": user["user_id"],
            "type": "credit", "amount": 50,
            "description": "Welcome bonus", "created_at": now()
        })
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"onboarded": True, "name": req.name}})
    return {"success": True, "message": "Onboarding complete", "welcome_credits": 50}

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
        "is_online": False,
        "tier": "new",
        "total_calls": 0,
        "total_minutes": 0,
        "avg_rating": 0,
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
    await db.listener_profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"is_online": req.online, "last_online": now()}}
    )
    return {"success": True, "online": req.online}

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
    online = await db.listener_profiles.find(
        {"is_online": True, "in_call": {"$ne": True}}, {"_id": 0}
    ).to_list(50)
    if not online:
        raise HTTPException(status_code=404, detail="No listeners available right now. Try again shortly.")
    # Score and sort
    scored = []
    for l in online:
        score = 0
        lang_match = set(seeker.get("languages", [])) & set(l.get("languages", []))
        score += len(lang_match) * 5
        tag_match = set(seeker.get("intent_tags", [])) & set(l.get("topic_tags", []))
        score += len(tag_match) * 3
        if l.get("tier") == "trusted":
            score += 2
        elif l.get("tier") == "elite":
            score += 4
        score += random.randint(0, 3)  # Fairness rotation
        scored.append((score, l))
    scored.sort(key=lambda x: x[0], reverse=True)
    matched = scored[0][1]
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
    call = {
        "id": call_id,
        "seeker_id": user["user_id"],
        "listener_id": req.listener_id,
        "call_type": req.call_type,
        "rate_per_min": rate,
        "is_first_call": is_first_call,
        "status": "active",
        "started_at": now(),
        "ended_at": None,
        "duration_seconds": 0,
        "cost": 0,
        "created_at": now()
    }
    await db.calls.insert_one(call)
    call.pop("_id", None)
    hms_session = create_100ms_session(call_id=call_id, call_type=req.call_type)
    if hms_session:
        await db.calls.update_one({"id": call_id}, {"$set": {"hms": hms_session}})
        call["hms"] = hms_session
    await db.listener_profiles.update_one(
        {"user_id": req.listener_id}, {"$set": {"in_call": True}}
    )
    return {"success": True, "call": call}

@api_router.post("/calls/end")
async def end_call(req: CallEndRequest, user=Depends(get_current_user)):
    call = await db.calls.find_one({"id": req.call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    started = datetime.fromisoformat(call["started_at"])
    ended = datetime.now(timezone.utc)
    duration = int((ended - started).total_seconds())
    rate = call["rate_per_min"]
    # First call cap: ₹1/min for first 5 mins
    if call.get("is_first_call") and duration > 300:
        cost_first = (300 / 60) * 1
        cost_rest = ((duration - 300) / 60) * (5 if call["call_type"] == "voice" else 8)
        cost = round(cost_first + cost_rest, 2)
    else:
        cost = round((duration / 60) * rate, 2)

    await db.calls.update_one({"id": req.call_id}, {"$set": {
        "status": "ended",
        "ended_at": ended.isoformat(),
        "duration_seconds": duration,
        "cost": cost
    }})
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
    # Update listener stats
    await db.listener_profiles.update_one(
        {"user_id": call["listener_id"]},
        {"$inc": {"total_calls": 1, "total_minutes": duration / 60}, "$set": {"in_call": False}}
    )
    return {
        "success": True,
        "duration_seconds": duration,
        "cost": cost,
        "listener_earned": earnings
    }

@api_router.get("/calls/history")
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
        "status": "processing", "created_at": now()
    })
    return {"success": True, "message": f"₹{req.amount} withdrawal initiated to {req.upi_id}"}

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
    logger.info("Voice Companionship Platform API started")
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
