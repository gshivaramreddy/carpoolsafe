import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.api_client import post, is_logged_in
from frontend.theme import inject_css, HYD_LOCATIONS
from frontend.maps_component import render_route_map
from frontend.sidebar import render_sidebar
from datetime import datetime, timedelta, date, time

st.set_page_config(page_title="Create Ride – CarpoolSafe", page_icon="🚗", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()

render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>🚗 Create a <span class='gradient-text'>Ride</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4a7a98;margin-bottom:20px;'>Offer your empty seats and earn while commuting</p>", unsafe_allow_html=True)

col_form, col_map = st.columns([1, 1], gap="large")

with col_form:
    with st.form("create_ride_form"):
        st.markdown("<div class='section-label'>📍 Source</div>", unsafe_allow_html=True)
        src_p = st.selectbox("Quick pick source", list(HYD_LOCATIONS.keys()), key="src_p")
        source_address = st.text_input("Source Address *", placeholder="e.g. HITEC City, Hyderabad")
        sc = HYD_LOCATIONS.get(src_p)
        c1, c2 = st.columns(2)
        with c1: src_lat = st.number_input("Latitude", value=sc[0] if sc else 17.4435, format="%.6f")
        with c2: src_lng = st.number_input("Longitude", value=sc[1] if sc else 78.3772, format="%.6f")

        st.markdown("<div class='section-label' style='margin-top:12px;'>🏁 Destination</div>", unsafe_allow_html=True)
        dst_p = st.selectbox("Quick pick destination", list(HYD_LOCATIONS.keys()), key="dst_p")
        dest_address = st.text_input("Destination Address *", placeholder="e.g. Charminar, Hyderabad")
        dc = HYD_LOCATIONS.get(dst_p)
        c3, c4 = st.columns(2)
        with c3: dst_lat = st.number_input("Latitude", value=dc[0] if dc else 17.3616, format="%.6f", key="dlat")
        with c4: dst_lng = st.number_input("Longitude", value=dc[1] if dc else 78.4747, format="%.6f", key="dlng")

        st.markdown("<div class='section-label' style='margin-top:12px;'>🗓️ Schedule & Options</div>", unsafe_allow_html=True)
        c5, c6, c7 = st.columns(3)
        with c5: dep_date = st.date_input("Date *", value=date.today() + timedelta(days=1), min_value=date.today())
        with c6: dep_time = st.time_input("Time *", value=time(8, 0))
        with c7: seats = st.number_input("Seats *", 1, 8, 3)
        c8, c9 = st.columns(2)
        with c8: price_km = st.number_input("₹ per km", 0.5, 20.0, 2.0, 0.5)
        with c9: women_only = st.checkbox("👩 Women-only ride")

        submitted = st.form_submit_button("🚀 Create Ride", use_container_width=True)

    if submitted:
        if not source_address.strip():
            st.error("⚠️ Source address is required.")
        elif not dest_address.strip():
            st.error("⚠️ Destination address is required.")
        elif src_lat == dst_lat and src_lng == dst_lng:
            st.error("⚠️ Source and destination cannot be the same.")
        else:
            payload = {
                "source_address": source_address.strip(),
                "source_lat": float(src_lat), "source_lng": float(src_lng),
                "destination_address": dest_address.strip(),
                "destination_lat": float(dst_lat), "destination_lng": float(dst_lng),
                "departure_time": datetime.combine(dep_date, dep_time).isoformat(),
                "total_seats": int(seats), "price_per_km": float(price_km),
                "is_women_only": women_only,
            }
            with st.spinner("Creating ride and fetching route..."):
                result = post("/ride/create", payload)
            if result:
                st.success("✅ Ride created!")
                st.session_state["new_ride"] = result
                c1, c2, c3 = st.columns(3)
                c1.metric("📏 Distance", f"{result.get('total_distance_km', 0):.1f} km")
                c2.metric("💰 Est. Price", f"₹{result.get('estimated_price', 0):.0f}")
                c3.metric("💺 Seats", result.get("available_seats", seats))

with col_map:
    st.markdown("<div class='section-label'>🗺️ Route Preview</div>", unsafe_allow_html=True)
    ride = st.session_state.get("new_ride")
    if ride:
        render_route_map(ride["source_lat"], ride["source_lng"],
            ride["destination_lat"], ride["destination_lng"],
            route_polyline=ride.get("route_polyline"),
            route_points=ride.get("route_points"), height=460)
        st.markdown(f"""
        <div class='gcard-glow'>
          <div style='font-weight:700;font-size:14px;'>{ride['source_address']} → {ride['destination_address']}</div>
          <div style='display:flex;gap:7px;flex-wrap:wrap;margin-top:8px;'>
            <span class='badge badge-cyan'>🕐 {ride['departure_time'][:16].replace('T',' ')}</span>
            <span class='badge badge-purple'>💺 {ride['available_seats']} seats</span>
            <span class='badge badge-green'>₹{ride['price_per_km']}/km</span>
            {"<span class='badge badge-pink'>👩 Women Only</span>" if ride.get('is_women_only') else ""}
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        render_route_map(17.4435, 78.3772, 17.3616, 78.4747, height=460)
        st.markdown("<p style='color:#4a7a98;text-align:center;font-size:12px;'>Fill the form to see your route</p>", unsafe_allow_html=True)
