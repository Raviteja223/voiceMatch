# VoiceMatch Setup Guide

This repository contains:
- **Backend**: FastAPI service (`/backend`)
- **Frontend**: React Native Expo app (`/frontend`)

---

## Prerequisites

- Python 3.10+
- Node.js + npm
- MongoDB instance (local or cloud)

---

## 1) Backend Setup (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=voicematch

# 100ms configuration
HMS_TEMPLATE_ID=your_100ms_template_id

# Either set a management token directly:
# HMS_MANAGEMENT_TOKEN=your_100ms_management_token

# OR set Access/Secret so server generates management token:
HMS_ACCESS_KEY=your_100ms_access_key
HMS_SECRET_KEY=your_100ms_secret_key

# Optional
HMS_API_BASE=https://api.100ms.live/v2
HMS_TOKEN_ROLE=host
```

Start backend:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2) Frontend Setup (Expo)

In a new terminal:

```bash
cd frontend
npm install
```

Set backend URL and run app:

```bash
export EXPO_PUBLIC_BACKEND_URL=http://localhost:8000
npx expo start
```

You can then open on Android/iOS/web from Expo CLI.

---

## 3) Authentication and OTP

- OTP is currently **mocked**.
- Use `1234` as the OTP code in the app.

---

## 4) 100ms Integration Behavior

When `/api/calls/start` is called:
- Backend attempts to create a 100ms room/session.
- If successful, it stores and returns `call.hms` in response.
- If 100ms config/API fails, app continues with existing simulated call flow.

---

## 5) Notes on MSG91

- MSG91 is **not yet integrated** in current backend OTP flow.
- Current OTP verification remains mocked (`1234`) until SMS provider integration is implemented.
