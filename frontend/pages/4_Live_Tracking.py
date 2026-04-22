import streamlit as st, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import get, is_logged_in
from frontend.theme import inject_css
from frontend.sidebar import render_sidebar
from frontend.maps_component import render_driver_tracking_sender, render_live_tracking_map

st.set_page_config(page_title="Live Tracking – CarpoolSafe", page_icon="📍", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.markdown("<h1 style='font-family:Syne,sans-serif;'>📍 Live <span class='gradient-text'>Tracking</span></h1>", unsafe_allow_html=True)
st.markdown("""<div class='live-pill' style='margin-bottom:16px;'>
  <div class='live-dot'></div> Real-time GPS · Route deviation detection · Stall monitoring
</div>""", unsafe_allow_html=True)

tab_driver, tab_rider = st.tabs(["🚗 Driver — Broadcast GPS", "🧑 Rider — Track My Ride"])

with tab_driver:
    rides = get("/ride/my-rides") or []
    active = [r for r in rides if r.get("status") in ("scheduled", "active")]
    if not active:
        st.info("No active rides. Create a ride first.")
    else:
        rm = {f"{r['source_address'][:22]}→{r['destination_address'][:22]} ({r['status']})": r for r in active}
        sel_label = st.selectbox("Select your ride to broadcast:", list(rm.keys()))
        sel_ride = rm[sel_label]
        c1, c2, c3 = st.columns(3)
        c1.metric("🛡️ Deviation Alert", "0.5 km")
        c2.metric("⏸️ Stall Alert", "5 min")
        c3.metric("👥 Riders", sel_ride["total_seats"] - sel_ride["available_seats"])
        st.markdown(f"""
        <div class='gcard-glow' style='margin:12px 0;'>
          <div style='display:flex;align-items:center;gap:10px;'>
            <div class='live-dot' style='width:12px;height:12px;'></div>
            <span style='font-weight:700;font-size:15px;color:#00d2ff;'>Broadcasting Location</span>
          </div>
          <div style='color:#4a7a98;font-size:12px;margin-top:6px;'>
            Ride: {sel_ride['id'][:12]}… · {sel_ride['departure_time'][:16].replace('T',' ')}
          </div>
          <div style='color:#94a3b8;font-size:11px;margin-top:4px;'>
            ⚠️ Allow browser location permission when prompted
          </div>
        </div>""", unsafe_allow_html=True)
        render_driver_tracking_sender(
            ride_id=sel_ride["id"],
            token=st.session_state.get("token", ""),
            backend_url=BACKEND_URL, height=480)

with tab_rider:
    default_id = st.session_state.get("tracking_ride_id", "")
    ride_id_inp = st.text_input("🔖 Ride ID to track", value=default_id, placeholder="Paste ride ID from your booking")
    if ride_id_inp:
        ride = get(f"/ride/{ride_id_inp}")
        if ride:
            st.markdown(f"""
            <div class='gcard-glow'>
              <div style='font-weight:700;font-size:15px;'>{ride['source_address']} → {ride['destination_address']}</div>
              <div style='margin-top:6px;display:flex;gap:7px;flex-wrap:wrap;'>
                <span class='badge badge-cyan'>🧑 {ride['driver_name']}</span>
                <span class='badge {"badge-green" if ride["status"]=="active" else "badge-amber"}'>{ride['status'].upper()}</span>
                <span class='badge badge-purple'>🕐 {ride['departure_time'][:16].replace('T',' ')}</span>
              </div>
            </div>""", unsafe_allow_html=True)

            col_map, col_info = st.columns([2, 1])
            with col_info:
                auto = st.checkbox("🔄 Auto-refresh (5s)")
                if st.button("Refresh Now"): st.rerun()
                cur_lat = ride.get("current_lat")
                cur_lng = ride.get("current_lng")
                if cur_lat and cur_lng:
                    st.markdown(f"""
                    <div class='gcard'>
                      <div class='stat-row'><span class='stat-label'>Latitude</span><span>{cur_lat:.4f}</span></div>
                      <div class='stat-row'><span class='stat-label'>Longitude</span><span>{cur_lng:.4f}</span></div>
                      <div class='stat-row'><span class='stat-label'>Last Update</span>
                        <span style='font-size:11px;'>{ride.get('last_location_update','')[:19].replace('T',' ') if ride.get('last_location_update') else 'N/A'}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"[📍 Open in Google Maps](https://maps.google.com/?q={cur_lat},{cur_lng})")
                else:
                    st.info("Driver hasn't started broadcasting yet.")
                share = get(f"/safety/trip-share/{ride_id_inp}", silent=True)
                if share:
                    st.markdown("<div class='section-label' style='margin-top:12px;'>🔗 Share Trip</div>", unsafe_allow_html=True)
                    st.code(share.get("share_link", ""), language=None)
                if auto:
                    time.sleep(5); st.rerun()

            with col_map:
                drv_lat = ride.get("current_lat") or ride["source_lat"]
                drv_lng = ride.get("current_lng") or ride["source_lng"]
                render_live_tracking_map(
                    route_points=ride.get("route_points") or [],
                    driver_lat=drv_lat, driver_lng=drv_lng,
                    source_lat=ride["source_lat"], source_lng=ride["source_lng"],
                    dest_lat=ride["destination_lat"], dest_lng=ride["destination_lng"], height=460)
        else:
            st.warning("Ride not found. Check the Ride ID.")
    else:
        st.markdown("""
        <div style='text-align:center;padding:50px;color:#4a7a98;'>
          <div style='font-size:48px;'>📡</div>
          <div style='font-size:14px;margin-top:10px;color:#94a3b8;'>Enter a Ride ID to start tracking</div>
        </div>""", unsafe_allow_html=True)
