# VoiceMatch - Voice Companionship Platform MVP

## Overview
Voice-first paid companionship marketplace targeting Tier 2/3 India with male Seekers and female Listeners using AI avatars, credit-based billing, and hybrid listener earnings.

## Tech Stack
- **Frontend**: React Native Expo (Expo Router, file-based routing)
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT with mocked OTP (demo code: 1234)

## Features Implemented

### Seeker Flow
- OTP login with role selection
- 3-step onboarding (name/age → languages → intent tags)
- Browse online listeners with avatars, ratings, tier badges
- "Talk Now" auto-match (language + tag scoring + fairness rotation)
- Direct listener selection
- Voice call screen with real-time timer & per-second billing
- First call discount (₹1/min for first 5 minutes)
- Post-call rating (Great/Good/Okay/Bad)
- Credit wallet with recharge packs (₹99/₹299/₹699)
- Transaction history (append-only ledger)

### Listener Flow
- OTP login with listener role
- 4-step onboarding (name/avatar → languages → style/topics → boundary assessment)
- Earnings dashboard (total earned, pending, withdrawn)
- Online/offline toggle
- Call history with earnings breakdown
- UPI withdrawal (min ₹1000, mocked)
- Tier system (New → Trusted → Elite with earning boosts)

### Admin Panel
- Dashboard with key stats (users, calls, revenue, reports)
- Moderation queue with action buttons (Warn/Suspend/Dismiss)
- Key metrics targets display

### Backend APIs (20+ endpoints)
- Auth: send-otp, verify-otp
- Seekers: onboard, profile
- Listeners: onboard, profile, toggle-online, online, all
- Matching: talk-now
- Calls: start, end, history
- Wallet: balance, recharge, transactions
- Ratings: submit
- Reports: submit
- Earnings: dashboard, withdraw
- Admin: dashboard, moderation-queue, users
- Seed data: auto-seeds 8 listeners on startup

## Billing Model
- 1 credit = ₹1
- Voice: ₹5/min (seeker pays) → ₹3/min (listener earns)
- Video: ₹8/min (seeker pays) → ₹5/min (listener earns)
- First call discount: ₹1/min for first 5 minutes
- Per-second deduction
- Welcome bonus: 50 credits

## MOCKED Systems
- **OTP**: Always use code `1234`
- **Payments**: Recharge always succeeds
- **Voice/Video Calls**: Simulated with timer and billing logic (no actual RTC)
- **UPI Withdrawal**: Always processes (no actual transfer)

## Design
- Soft pastel theme: Coral (#FF8FA3), Mint (#A2E3C4), Cream (#FFFBF0), Marigold (#F6E05E)
- Safe, non-dating branding with shield/verified badges
- Mobile-first with 48px+ touch targets

## Next Steps
- Integrate real RTC (Agora/100ms) for voice/video
- Integrate Razorpay for payments
- Integrate SMS OTP provider (MSG91/Twilio)
- Anti-collusion detection engine
- Call recording & moderation tools
- Push notifications for incoming calls
- Multi-language UI translations (Hindi, Tamil, etc.)

## Business Enhancement
- **Referral Program**: Offer ₹20 credits per referral to drive viral growth in Tier 2/3 cities
