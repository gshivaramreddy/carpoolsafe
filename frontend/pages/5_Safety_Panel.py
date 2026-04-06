import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import post, get,  is_logged_in
from frontend.theme import inject_css
from frontend.sidebar import render_sidebar

st.set_page_config(page_title="Safety Panel – CarpoolSafe", page_icon="🛡️", layout="wide")
inject_css()
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>🛡️ Safety <span class='gradient-text'>Panel</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4a7a98;margin-bottom:20px;'>Emergency tools, trusted contacts, and safety algorithms</p>", unsafe_allow_html=True)

profile = get("/auth/me") or {}
col_l, col_r = st.columns([1, 1.2], gap="large")

with col_l:
    st.markdown("### 🚨 Emergency SOS")
    st.markdown("""
    <div style='background:rgba(255,65,108,0.06);border:1px solid rgba(255,65,108,0.2);
                border-radius:16px;padding:14px;margin-bottom:14px;'>
      <div style='font-size:12px;color:#94a3b8;'>
        📲 Alerts all trusted contacts<br>
        📍 Shares your Google Maps location<br>
        🔔 Notifies all ride participants<br>
        💾 Logged in safety database
      </div>
    </div>""", unsafe_allow_html=True)

    ride_id_sos = st.text_input("Active Ride ID (optional)", placeholder="Paste ride ID if on a trip")
    sos_msg = st.text_input("SOS Message", value="EMERGENCY: I need help! Please contact me immediately.")

    st.markdown("<div class='sos-wrap'>", unsafe_allow_html=True)
    if st.button("🚨  SOS — SEND EMERGENCY ALERT", use_container_width=True, key="sos_btn"):
        result = post("/safety/sos", {"ride_id": ride_id_sos or None, "message": sos_msg,
                                       "lat": None, "lng": None})
        if result:
            st.error(f"🚨 SOS SENT! {result['message']}")
            if result.get("maps_link"):
                st.markdown(f"[📍 Your Location]({result['maps_link']})")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)
    st.markdown("### 🔗 Share Live Trip")
    share_id = st.text_input("Ride ID to share", key="share_rid")
    if st.button("Generate Link", use_container_width=True) and share_id:
        r = get(f"/safety/trip-share/{share_id}")
        if r:
            st.success("Share this link:")
            st.code(r["share_link"])

    if (profile.get("gender") or "").lower() == "female":
        st.markdown("""
        <div style='background:rgba(255,107,157,0.06);border:1px solid rgba(255,107,157,0.2);
                    border-radius:16px;padding:14px;margin-top:12px;'>
          <div style='font-weight:700;color:#ff6b9d;margin-bottom:6px;'>👩 Women Safety Active</div>
          <div style='font-size:12px;color:#94a3b8;'>
            ✅ Women-only ride filter<br>
            ✅ Route deviation monitoring (&gt;0.5km)<br>
            ✅ Stall detection (&gt;5 min)<br>
            ✅ SOS broadcasts to contacts<br>
            ✅ Live trip sharing
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)
    st.markdown("### ⚠️ Check Ride Alerts")
    alert_id = st.text_input("Ride ID", key="alert_rid")
    if alert_id:
        alerts = get(f"/safety/alerts/{alert_id}")
        if alerts:
            for a in alerts:
                st.markdown(f"""
                <div style='background:rgba(255,65,108,0.07);border:1px solid rgba(255,65,108,0.2);
                            border-radius:10px;padding:10px;margin-bottom:6px;'>
                  <div style='color:#ff416c;font-size:13px;'>{a.get('message','Alert')}</div>
                  <div style='color:#4a7a98;font-size:11px;margin-top:3px;'>
                    {a.get('created_at','')[:19].replace('T',' ') if a.get('created_at') else ''}
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("✅ No alerts for this ride.")

with col_r:
    st.markdown("### 👥 Trusted Contacts")
    contacts = profile.get("trusted_contacts", []) or []
    colors = ["#00d2ff", "#a78bfa", "#ff6b9d", "#00e676", "#ffc107"]
    for i, c in enumerate(contacts):
        color = colors[i % len(colors)]
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:10px;padding:10px;
                    background:#0d1f38;border:1px solid #1a3a5c;border-radius:12px;margin-bottom:7px;'>
          <div style='width:36px;height:36px;border-radius:50%;background:{color}22;
                      border:1px solid {color}55;display:flex;align-items:center;
                      justify-content:center;font-weight:700;font-size:12px;color:{color};flex-shrink:0;'>
            {c.get('name','?')[0].upper()}
          </div>
          <div>
            <div style='font-weight:600;font-size:13px;'>{c.get('name','Unknown')}</div>
            <div style='font-size:11px;color:#4a7a98;'>
              📞 {c.get('phone','N/A')}
              {f" · ✉️ {c.get('email','')}" if c.get('email') else ''}
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    if not contacts:
        st.info("No trusted contacts yet. Add them below.")

    with st.expander("➕ Add Trusted Contact"):
        with st.form("add_contact_form"):
            cn = st.text_input("Name *")
            cp = st.text_input("Phone *", placeholder="+91 9876543210")
            ce = st.text_input("Email (optional)")
            if st.form_submit_button("Add Contact", use_container_width=True):
                if cn and cp:
                    updated = contacts + [{"name": cn, "phone": cp, "email": ce or None}]
                    r = put("/auth/profile", {"trusted_contacts": updated})
                    if r:
                        st.success(f"Added {cn}!")
                        st.rerun()
                else:
                    st.error("Name and phone are required.")

    if contacts:
        if st.button("🗑️ Remove All Contacts"):
            put("/auth/profile", {"trusted_contacts": []})
            st.success("Removed.")
            st.rerun()

    st.markdown("<hr style='border-color:#0f2040;'>", unsafe_allow_html=True)
    st.markdown("### 🔬 Safety Algorithms")
    algos = [
        ("📐", "Haversine", "Great-circle distance", "#00d2ff"),
        ("🛤️", "Route Deviation", "Alert at >0.5km off-route", "#a78bfa"),
        ("⏸️", "Stall Detection", "Alert after 5min stop", "#ffc107"),
        ("⭐", "Safety Score", "Driver risk 0–5 rating", "#00e676"),
        ("📏", "Point-to-Route", "Segment distance calc", "#42a5f5"),
        ("🚨", "Anomaly Detect", "Real-time risk scoring", "#ff416c"),
    ]
    cols = st.columns(2)
    for i, (icon, name, desc, color) in enumerate(algos):
        with cols[i % 2]:
            st.markdown(f"""
            <div style='background:{color}0d;border:1px solid {color}33;
                        border-radius:12px;padding:10px;margin-bottom:8px;'>
              <div style='font-size:18px;'>{icon}</div>
              <div style='font-weight:600;font-size:12px;color:{color};margin-top:4px;'>{name}</div>
              <div style='font-size:11px;color:#4a7a98;margin-top:2px;'>{desc}</div>
            </div>""", unsafe_allow_html=True)
