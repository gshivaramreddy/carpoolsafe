import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.api_client import post, is_logged_in
from frontend.theme import inject_css, HYD_LOCATIONS
from frontend.maps_component import render_route_map
from frontend.sidebar import render_sidebar
from datetime import datetime, timedelta, date, time as dtime

st.set_page_config(page_title="Search Rides – CarpoolSafe", page_icon="🔍", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()

render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>🔍 Find a <span class='gradient-text'>Ride</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4a7a98;margin-bottom:20px;'>AI matching engine finds the best route-aligned rides</p>", unsafe_allow_html=True)

col_s, col_r = st.columns([1, 1.5], gap="large")

with col_s:
    with st.form("search_form"):
        st.markdown("<div class='section-label'>📍 Your Journey</div>", unsafe_allow_html=True)
        pu_p = st.selectbox("Pickup (quick pick)", list(HYD_LOCATIONS.keys()), key="pu_p")
        pickup_addr = st.text_input("Pickup Address *", placeholder="Where to pick you up?")
        pc = HYD_LOCATIONS.get(pu_p)
        c1, c2 = st.columns(2)
        with c1: pu_lat = st.number_input("Pickup Lat", value=pc[0] if pc else 17.4435, format="%.6f")
        with c2: pu_lng = st.number_input("Pickup Lng", value=pc[1] if pc else 78.3772, format="%.6f")

        dr_p = st.selectbox("Drop (quick pick)", list(HYD_LOCATIONS.keys()), key="dr_p")
        drop_addr = st.text_input("Drop Address *", placeholder="Your destination?")
        dc = HYD_LOCATIONS.get(dr_p)
        c3, c4 = st.columns(2)
        with c3: dr_lat = st.number_input("Drop Lat", value=dc[0] if dc else 17.3616, format="%.6f")
        with c4: dr_lng = st.number_input("Drop Lng", value=dc[1] if dc else 78.4747, format="%.6f")

        st.markdown("<div class='section-label' style='margin-top:10px;'>⚙️ Filters</div>", unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        with c5:
            dep_date = st.date_input("Date", value=date.today() + timedelta(days=1))
            seats_needed = st.number_input("Seats needed", 1, 6, 1)
        with c6:
            dep_time = st.time_input("Approx time", value=dtime(8, 0))
            max_km = st.number_input("Max pickup walk (km)", 0.5, 5.0, 2.0, 0.5)
        women_only = st.checkbox("👩 Women-only rides only")
        submitted = st.form_submit_button("🔍 Search Rides", use_container_width=True)

with col_r:
    st.markdown("<div class='section-label'>🎯 Matched Rides</div>", unsafe_allow_html=True)
    if submitted:
        if not pickup_addr.strip() or not drop_addr.strip():
            st.error("⚠️ Enter pickup and drop addresses.")
        else:
            payload = {
                "pickup_lat": pu_lat, "pickup_lng": pu_lng,
                "pickup_address": pickup_addr.strip(),
                "drop_lat": dr_lat, "drop_lng": dr_lng,
                "drop_address": drop_addr.strip(),
                "departure_time": datetime.combine(dep_date, dep_time).isoformat(),
                "seats_needed": int(seats_needed), "women_only": women_only,
                "max_pickup_distance_km": float(max_km),
                "max_drop_distance_km": float(max_km),
            }
            with st.spinner("AI matching engine running..."):
                results = post("/ride/search", payload)

            if results is None:
                st.info("🔌 Backend not reachable. Run: `python run_backend.py`")
            elif len(results) == 0:
                st.info("No matching rides found. Try wider filters.")
            else:
                st.success(f"Found **{len(results)}** ride(s) — sorted by best match")
                st.session_state["search_results"] = results
                st.session_state["search_pickup"] = {"lat": pu_lat, "lng": pu_lng, "address": pickup_addr}
                st.session_state["search_drop"] = {"lat": dr_lat, "lng": dr_lng, "address": drop_addr}

    results = st.session_state.get("search_results", [])
    if results:
        for idx, match in enumerate(results):
            ride = match["ride"]
            score_pct = max(0, int((1 - match["match_score"]) * 100))
            sc_color = "#00e676" if score_pct >= 80 else "#ffc107" if score_pct >= 60 else "#ff416c"
            wo = "<span class='badge badge-pink' style='font-size:10px;'>👩 Women Only</span>" if ride.get("is_women_only") else ""
            st.markdown(f"""
            <div class='gcard' style='border-left:3px solid {sc_color};'>
              <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;'>
                <div>
                  <div style='font-weight:700;font-size:14px;'>{ride['source_address'][:26]}… → {ride['destination_address'][:26]}…</div>
                  <div style='color:#4a7a98;font-size:12px;margin-top:2px;'>
                    🧑 {ride['driver_name']} · ⭐ {ride['driver_safety_score']:.1f} · 🚙 {ride.get('vehicle_type','N/A')}
                  </div>
                </div>
                <div style='text-align:right;'>
                  <div style='font-size:20px;font-weight:800;color:#00e676;'>₹{match['estimated_price']:.0f}</div>
                  <div style='font-size:10px;color:#4a7a98;'>est. fare</div>
                </div>
              </div>
              <div style='display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px;'>
                <span class='badge badge-blue'>🕐 {ride['departure_time'][:16].replace('T',' ')}</span>
                <span class='badge badge-purple'>💺 {ride['available_seats']} seats</span>
                <span class='badge badge-cyan'>📍 {match['pickup_distance_km']:.1f}km pickup</span>
                <span class='badge badge-amber'>⏱ {match['time_diff_minutes']:.0f}min diff</span>
                {wo}
              </div>
              <div style='display:flex;justify-content:space-between;font-size:10px;color:#4a7a98;margin-bottom:3px;'>
                <span>Match Score</span><span style='color:{sc_color};font-weight:700;'>{score_pct}%</span>
              </div>
              <div class='score-track'><div class='score-fill' style='width:{score_pct}%;background:{sc_color};'></div></div>
            </div>""", unsafe_allow_html=True)

            b1, b2 = st.columns([2, 1])
            with b1:
                if st.button(f"🎟️ Book This Ride", key=f"book_{idx}"):
                    st.session_state["booking_ride"] = ride
                    st.session_state["booking_match"] = match
                    st.switch_page("pages/3_My_Bookings.py")
            with b2:
                if st.button(f"🗺️ View Map", key=f"map_{idx}"):
                    st.session_state["viewing_ride"] = ride
            st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)

        view = st.session_state.get("viewing_ride", results[0]["ride"])
        pickup = st.session_state.get("search_pickup")
        drop_l = st.session_state.get("search_drop")
        render_route_map(
            view["source_lat"], view["source_lng"],
            view["destination_lat"], view["destination_lng"],
            route_polyline=view.get("route_polyline"),
            route_points=view.get("route_points"),
            pickup_lat=pickup["lat"] if pickup else None,
            pickup_lng=pickup["lng"] if pickup else None,
            drop_lat=drop_l["lat"] if drop_l else None,
            drop_lng=drop_l["lng"] if drop_l else None, height=340)
    elif not submitted:
        st.markdown("""
        <div style='text-align:center;padding:60px 0;color:#4a7a98;'>
          <div style='font-size:48px;margin-bottom:12px;'>🔍</div>
          <div style='font-size:15px;color:#94a3b8;'>Enter your journey details and hit Search</div>
        </div>""", unsafe_allow_html=True)
