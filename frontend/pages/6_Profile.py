import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import get,  is_logged_in, do_logout
from frontend.theme import inject_css
from frontend.sidebar import render_sidebar

st.set_page_config(page_title="Profile – CarpoolSafe", page_icon="👤", layout="centered")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>👤 My <span class='gradient-text'>Profile</span></h1>", unsafe_allow_html=True)

profile = get("/auth/me")
if not profile:
    st.error("Could not load profile.")
    st.stop()

sc = profile.get("safety_score", 5.0)
sc_color = "#00e676" if sc >= 4 else "#ffc107" if sc >= 3 else "#ff416c"
gender = (profile.get("gender") or "").lower()
avatar = "👩" if gender == "female" else "🧑"

st.markdown(f"""
<div class='gcard-glow' style='text-align:center;padding:28px;margin-bottom:20px;'>
  <div style='font-size:60px;'>{avatar}</div>
  <div style='font-size:22px;font-weight:800;font-family:Syne,sans-serif;margin:8px 0 4px;'>
    {profile.get('name','User')}
  </div>
  <div style='color:#4a7a98;margin-bottom:10px;'>
    {profile.get('email','')}
    {f" · 📱 {profile.get('phone','')}" if profile.get('phone') else ''}
  </div>
  <div style='display:flex;gap:8px;justify-content:center;flex-wrap:wrap;'>
    <span class='badge badge-cyan'>{profile.get('role','rider').upper()}</span>
    <span style='background:{sc_color}22;color:{sc_color};border:1px solid {sc_color}55;
                 border-radius:999px;padding:3px 12px;font-size:12px;font-weight:600;'>
      ⭐ {sc:.1f} Safety Score
    </span>
    {"<span class='badge badge-pink'>👩 Female</span>" if gender == "female" else ""}
  </div>
</div>""", unsafe_allow_html=True)

rides = get("/ride/my-rides") or []
bookings = get("/booking/my-bookings") or []
c1, c2, c3, c4 = st.columns(4)
c1.metric("🚗 Rides Created", len(rides))
c2.metric("🎟️ Rides Booked", len(bookings))
c3.metric("⭐ Safety Score", f"{sc:.1f}")
c4.metric("📅 Member Since", profile.get("created_at", "")[:10] if profile.get("created_at") else "N/A")

st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)
st.markdown("### ✏️ Edit Profile")

with st.form("edit_form"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Full Name", value=profile.get("name", ""))
        phone = st.text_input("Phone", value=profile.get("phone", "") or "")
        gender_opts = ["", "Female", "Male", "Non-binary", "Prefer not to say"]
        cur_g = profile.get("gender", "") or ""
        gender_sel = st.selectbox("Gender", gender_opts,
            index=gender_opts.index(cur_g) if cur_g in gender_opts else 0)
    with c2:
        vtype = st.text_input("Vehicle Type", value=profile.get("vehicle_type", "") or "")
        vnum = st.text_input("Vehicle Number", value=profile.get("vehicle_number", "") or "")
    if st.form_submit_button("💾 Save Changes", use_container_width=True):
        payload = {}
        if name: payload["name"] = name
        if phone: payload["phone"] = phone
        if gender_sel: payload["gender"] = gender_sel
        if vtype: payload["vehicle_type"] = vtype
        if vnum: payload["vehicle_number"] = vnum
        if payload:
            result = ("/auth/profile", payload)
            if result:
                st.success("✅ Profile updated!")
                st.session_state.user_name = result.get("name", st.session_state.user_name)
                st.session_state.user_gender = result.get("gender", "")
                st.rerun()

st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)
st.markdown("### 🚪 Account")
if st.button("Sign Out", use_container_width=True, key="profile_signout"):
    do_logout()
    st.rerun()
