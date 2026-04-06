"""
Shared sidebar — single source of truth for navigation.
All pages import and call render_sidebar() from here.
"""
import streamlit as st
from frontend.api_client import do_logout
import uuid


def render_sidebar():
    """Render the left navigation sidebar. Only call when user is logged in."""
    gender = (st.session_state.get("user_gender") or "").lower()
    role   = st.session_state.get("user_role") or "rider"
    name   = st.session_state.get("user_name") or "User"

    with st.sidebar:
        # Logo
        st.markdown("""
        <div style='padding:18px 10px 12px;'>
          <div style='font-size:22px;font-weight:800;font-family:Syne,sans-serif;
                      background:linear-gradient(135deg,#00d2ff,#7b2ff7,#ff6b9d);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
            🚗 CarpoolSafe
          </div>
          <div style='font-size:10px;color:#4a7a98;margin-top:2px;'>Intelligent carpooling</div>
        </div>
        """, unsafe_allow_html=True)

        # User card
        female_badge = ""
        if gender == "female":
            female_badge = "<span style='background:rgba(255,107,157,0.12);color:#ff6b9d;border:1px solid rgba(255,107,157,0.3);border-radius:999px;padding:2px 8px;font-size:10px;font-weight:600;margin-left:4px;'>👩 Female</span>"

        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#0d1f38,#0a172d);
                    border:1px solid rgba(0,210,255,0.3);border-radius:16px;
                    padding:14px;margin:0 4px 16px;'>
          <div style='font-size:15px;font-weight:600;color:#e8f4fd;'>{name}</div>
          <div style='font-size:11px;color:#4a7a98;margin-top:2px;'>{role}</div>
          <div style='margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;'>
            <span style='background:rgba(0,210,255,0.12);color:#00d2ff;
                         border:1px solid rgba(0,210,255,0.3);border-radius:999px;
                         padding:2px 8px;font-size:10px;font-weight:600;'>{role.upper()}</span>
            {female_badge}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation links — defined ONCE here only
        st.markdown("""
        <div style='font-size:10px;font-weight:600;color:#2a4a68;text-transform:uppercase;
                    letter-spacing:0.1em;padding:0 12px 6px;'>Navigation</div>
        """, unsafe_allow_html=True)

        nav_items = [
            ("🏠 Dashboard",     "app.py"),
            ("🚗 Create Ride",   "pages/1_Create_Ride.py"),
            ("🔍 Search Rides",  "pages/2_Search_Rides.py"),
            ("📋 My Bookings",   "pages/3_My_Bookings.py"),
            ("📍 Live Tracking", "pages/4_Live_Tracking.py"),
            ("🛡️ Safety Panel",  "pages/5_Safety_Panel.py"),
            ("👥 Group Rides",   "pages/7_Group_Rides.py"),
            ("💳 Payments",      "pages/8_Payments.py"),
            ("👤 Profile",       "pages/6_Profile.py"),
        ]
        for label, page in nav_items:
            st.page_link(page, label=label, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sign Out button — red
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] .stButton > button {
          background: linear-gradient(135deg,#ff416c,#ff4b2b) !important;
          box-shadow: 0 4px 20px rgba(255,65,108,0.3) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
            do_logout()
            st.rerun()
