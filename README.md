# 🚗 CarpoolSafe — Full Stack Carpooling Platform

## Quick Start

### 1. Install PostgreSQL & create database
```bash
psql -U postgres -c "CREATE DATABASE carpool_db;"
```

### 2. Add your Google Maps API Key
Edit `.env` — replace `your-google-maps-api-key-here` with your real key.
Also edit `frontend/.env` with the same key.

**Enable these APIs in Google Cloud Console:**
- Maps JavaScript API
- Directions API  
- Distance Matrix API
- Geocoding API

### 3. Run everything
```bash
# Linux / Mac
bash start.sh

# Windows
start.bat
```

### 4. Open browser
- Frontend: http://localhost:8501
- Backend API docs: http://localhost:8000/docs

---

## Manual Start (Two Terminals)

**Terminal 1 — Backend:**
```bash
pip install -r backend/requirements.txt
python run_backend.py
```

**Terminal 2 — Frontend:**
```bash
pip install -r frontend/requirements.txt
cd frontend
streamlit run app.py
```

---

## Project Structure

```
carpool/
├── backend/
│   ├── main.py              ← FastAPI app entry
│   ├── models/              ← Database models (SQLAlchemy)
│   ├── routes/              ← API endpoints
│   │   ├── auth.py          ← Login, Register, Profile
│   │   ├── rides.py         ← Create/Search rides
│   │   ├── bookings.py      ← Book/Cancel seats
│   │   ├── safety.py        ← SOS, alerts, trip sharing
│   │   ├── group_rides.py   ← Group coordination + chat
│   │   └── payments.py      ← Cost splitting + UPI
│   ├── services/
│   │   ├── matching.py      ← AI ride matching engine
│   │   └── ml_pricing.py    ← Smart fare suggestions
│   ├── utils/
│   │   ├── auth.py          ← JWT helpers
│   │   └── geo.py           ← Haversine, route deviation
│   └── websocket/
│       ├── manager.py       ← WebSocket connection manager
│       └── tracking.py      ← /ws/track/{ride_id} endpoint
│
├── frontend/
│   ├── app.py               ← Dashboard + Login/Register
│   ├── api_client.py        ← Backend HTTP client
│   ├── maps_component.py    ← Google Maps + Folium maps
│   ├── theme.py             ← Shared CSS theme
│   └── pages/
│       ├── 1_Create_Ride.py
│       ├── 2_Search_Rides.py
│       ├── 3_My_Bookings.py
│       ├── 4_Live_Tracking.py
│       ├── 5_Safety_Panel.py
│       ├── 6_Profile.py
│       ├── 7_Group_Rides.py
│       └── 8_Payments.py
│
├── .env                     ← Your config (edit this)
├── frontend/.env            ← Frontend config (edit this too)
├── start.sh                 ← One-command launcher (Linux/Mac)
└── start.bat                ← One-command launcher (Windows)
```

---

## All Features — Real-Time

| Feature | Status |
|---------|--------|
| Register / Login / Sign Out | ✅ JWT auth, bcrypt passwords |
| Create Ride + Google Maps route | ✅ Directions API polyline |
| AI Ride Matching | ✅ Haversine + weighted scoring |
| Book Seats | ✅ Atomic locking, no overbooking |
| Live GPS Tracking | ✅ WebSocket, updates every 3-5s |
| Route Deviation Alert | ✅ >0.5km triggers alert |
| Stall Detection | ✅ >5 min no movement = alert |
| SOS Emergency | ✅ Broadcasts to all contacts |
| Women-Only Rides | ✅ Gender-verified booking |
| Group Rides + Chat | ✅ Real-time group coordination |
| Schedule Voting | ✅ Propose + vote on times |
| Cost Splitting | ✅ Equal/distance/seats/custom |
| UPI Payments | ✅ Deep-link generation |
| Payment History | ✅ Full transaction tracking |
