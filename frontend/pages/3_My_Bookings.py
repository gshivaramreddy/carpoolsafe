import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import post, get,  is_logged_in
from frontend.theme import inject_css, HYD_LOCATIONS
from frontend.sidebar import render_sidebar

st.set_page_config(page_title="My Bookings – CarpoolSafe", page_icon="📋", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>📋 My <span class='gradient-text'>Bookings</span></h1>", unsafe_allow_html=True)

# ── Quick Book (from Search) ───────────────────────────────────────────────────
ride_to_book = st.session_state.get("booking_ride")
match_info   = st.session_state.get("booking_match")

if ride_to_book:
    st.markdown("## 🎟️ Complete Your Booking")
    st.markdown(f"""
    <div class='gcard-glow'>
      <div style='font-weight:700;font-size:15px;margin-bottom:8px;'>
        {ride_to_book['source_address']} → {ride_to_book['destination_address']}
      </div>
      <div style='display:flex;gap:7px;flex-wrap:wrap;'>
        <span class='badge badge-cyan'>🧑 {ride_to_book['driver_name']}</span>
        <span class='badge badge-green'>⭐ {ride_to_book['driver_safety_score']:.1f}</span>
        <span class='badge badge-blue'>🕐 {ride_to_book['departure_time'][:16].replace('T',' ')}</span>
        <span class='badge badge-purple'>💺 {ride_to_book['available_seats']} seats</span>
        <span class='badge badge-amber'>₹{ride_to_book['price_per_km']}/km</span>
        {"<span class='badge badge-pink'>👩 Women Only</span>" if ride_to_book.get('is_women_only') else ""}
      </div>
    </div>""", unsafe_allow_html=True)

    with st.form("book_form"):
        c1, c2 = st.columns(2)
        with c1:
            pickup_addr = st.text_input("📍 Your Pickup Address *",
                value=st.session_state.get("search_pickup", {}).get("address", ""))
            pu_lat = st.number_input("Pickup Lat",
                value=st.session_state.get("search_pickup", {}).get("lat", 17.4435), format="%.6f")
            pu_lng = st.number_input("Pickup Lng",
                value=st.session_state.get("search_pickup", {}).get("lng", 78.3772), format="%.6f")
        with c2:
            drop_addr = st.text_input("🏁 Your Drop Address *",
                value=st.session_state.get("search_drop", {}).get("address", ""))
            dr_lat = st.number_input("Drop Lat",
                value=st.session_state.get("search_drop", {}).get("lat", 17.3616), format="%.6f")
            dr_lng = st.number_input("Drop Lng",
                value=st.session_state.get("search_drop", {}).get("lng", 78.4747), format="%.6f")
        seats = st.number_input("Seats to book", 1, ride_to_book.get("available_seats", 4), 1)
        if match_info:
            est = match_info.get("estimated_price", 0) * seats
            st.markdown(f"""
            <div style='background:rgba(0,230,118,0.07);border:1px solid rgba(0,230,118,0.2);
                        border-radius:12px;padding:12px;'>
              💰 Estimated fare: <b style='color:#00e676;font-size:18px;'>₹{est:.2f}</b> for {seats} seat(s)
            </div>""", unsafe_allow_html=True)
        col_yes, col_no = st.columns(2)
        with col_yes: confirmed = st.form_submit_button("✅ Confirm Booking", use_container_width=True)
        with col_no:  cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

    if confirmed:
        if not pickup_addr.strip() or not drop_addr.strip():
            st.error("⚠️ Enter your pickup and drop addresses.")
        else:
            result = post("/booking/book", {
                "ride_id": ride_to_book["id"],
                "pickup_address": pickup_addr.strip(), "pickup_lat": pu_lat, "pickup_lng": pu_lng,
                "drop_address": drop_addr.strip(), "drop_lat": dr_lat, "drop_lng": dr_lng,
                "seats_booked": int(seats),
            })
            if result:
                st.success(f"🎉 Booking confirmed! Fare: ₹{result.get('estimated_price', 0):.2f}")
                st.session_state.pop("booking_ride", None)
                st.session_state.pop("booking_match", None)
                st.rerun()
    if cancelled:
        st.session_state.pop("booking_ride", None)
        st.session_state.pop("booking_match", None)
        st.rerun()
    st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)

# ── Booking History ───────────────────────────────────────────────────────────
st.markdown("## 📜 My Booking History")
if st.button("🔄 Refresh"): st.rerun()
bookings = get("/booking/my-bookings") or []

STATUS = {
    "confirmed": ("badge-green", "✅ Confirmed"),
    "pending":   ("badge-amber", "⏳ Pending"),
    "cancelled": ("badge-red",   "❌ Cancelled"),
    "completed": ("badge-cyan",  "🏁 Completed"),
}

if not bookings:
    st.markdown("""
    <div style='text-align:center;padding:50px;color:#4a7a98;'>
      <div style='font-size:40px;'>📋</div>
      <div style='font-size:15px;margin-top:10px;color:#94a3b8;'>No bookings yet</div>
      <div style='font-size:12px;'>Search for rides and book your first seat!</div>
    </div>""", unsafe_allow_html=True)
else:
    for b in bookings:
        status = b.get("status", "confirmed")
        bc, bl = STATUS.get(status, ("badge-blue", status))
        st.markdown(f"""
        <div class='gcard'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
            <div>
              <div style='font-weight:700;font-size:14px;'>{b['pickup_address']} → {b['drop_address']}</div>
              <div style='color:#4a7a98;font-size:12px;margin-top:4px;'>
                💺 {b['seats_booked']} seat(s) · 💰 ₹{b.get('estimated_price', 0):.2f}
                · 🔖 {b['id'][:8]}…
              </div>
              <div style='color:#4a7a98;font-size:11px;margin-top:3px;'>
                {b.get('created_at','')[:16].replace('T',' ') if b.get('created_at') else ''}
              </div>
            </div>
            <span class='badge {bc}'>{bl}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        if status == "confirmed":
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📍 Track Ride", key=f"tr_{b['id']}"):
                    st.session_state["tracking_ride_id"] = b["ride_id"]
                    st.switch_page("pages/4_Live_Tracking.py")
            with c2:
                if st.button("💳 Pay", key=f"pay_{b['id']}"):
                    st.session_state["pay_booking_id"] = b["id"]
                    st.switch_page("pages/8_Payments.py")
            with c3:
                if st.button("❌ Cancel", key=f"can_{b['id']}"):
                    r = delete(f"/booking/cancel/{b['id']}")
                    if r:
                        st.success("Booking cancelled.")
                        st.rerun()
