"""
CarpoolSafe — Main entry point.
Handles: Login, Register, Dashboard.
No sidebar shown before login.
"""
from api_client import do_signup
import streamlit as st
import sys, os


from api_client import post, get, is_logged_in, do_login, do_logout, backend_is_up
st.set_page_config(
    page_title="CarpoolSafe",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",   # ← collapsed until logged in
)
st.markdown("""
<style>
[data-testid="stSidebarNav"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

html,body,[data-testid="stApp"] {
  background:#050b18 !important; color:#e8f4fd !important;
  font-family:'Inter',sans-serif !important;
}
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#080f1f,#0a1628) !important;
  border-right:1px solid #0f2040 !important;
}
[data-testid="stSidebar"] * { color:#e8f4fd !important; }
h1,h2,h3,h4 { font-family:'Syne',sans-serif !important; }

/* Default button — gradient */
.stButton > button {
  background:linear-gradient(135deg,#00d2ff,#7b2ff7) !important;
  color:#fff !important; font-weight:700 !important;
  font-family:'Syne',sans-serif !important;
  border:none !important; border-radius:14px !important;
  padding:11px 24px !important; font-size:14px !important;
  box-shadow:0 4px 24px rgba(0,210,255,0.2) !important;
  transition:all 0.2s !important;
}
.stButton > button:hover {
  transform:translateY(-2px) !important;
  box-shadow:0 8px 32px rgba(123,47,247,0.4) !important;
}

/* Inputs */
.stTextInput>div>div>input,
.stTextArea>div>div>textarea,
.stSelectbox>div>div>div,
.stNumberInput>div>div>input,
.stDateInput>div>div>input,
.stTimeInput>div>div>input {
  background:#0d1f38 !important; color:#e8f4fd !important;
  border:1px solid #1a3a5c !important; border-radius:12px !important;
  font-family:'Inter',sans-serif !important;
}
.stTextInput>div>div>input:focus {
  border-color:#00d2ff !important;
  box-shadow:0 0 0 3px rgba(0,210,255,0.12) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background:#0d1f38 !important; border-radius:14px !important;
  padding:5px !important; gap:4px !important; border:1px solid #1a3a5c !important;
}
.stTabs [data-baseweb="tab"] {
  background:transparent !important; color:#6b8fa8 !important;
  border-radius:10px !important; font-weight:500 !important;
}
.stTabs [aria-selected="true"] {
  background:linear-gradient(135deg,#00d2ff22,#7b2ff722) !important;
  color:#00d2ff !important; border-bottom:2px solid #00d2ff !important;
}

/* Metrics */
[data-testid="metric-container"] {
  background:linear-gradient(135deg,#0d1f38,#0a172d) !important;
  border:1px solid #1a3a5c !important; border-radius:16px !important;
  padding:18px !important;
}
[data-testid="stMetricValue"] { color:#e8f4fd !important; }

/* Misc */
.stCheckbox label,.stRadio label { color:#b8d4e8 !important; }
.streamlit-expanderHeader {
  background:#0d1f38 !important; border-radius:12px !important;
  border:1px solid #1a3a5c !important; color:#e8f4fd !important;
}
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-track { background:#080f1f; }
::-webkit-scrollbar-thumb { background:#1a3a5c; border-radius:3px; }
[data-testid="stPageLink"] a { color:#6b8fa8 !important; border-radius:10px !important; }
[data-testid="stPageLink"] a:hover { background:#0d1f38 !important; color:#00d2ff !important; }

/* Component classes */
.gcard {
  background:linear-gradient(135deg,#0d1f38,#0a172d);
  border:1px solid #1a3a5c; border-radius:20px; padding:22px; margin-bottom:14px;
}
.gcard-glow {
  background:linear-gradient(135deg,#0d1f38,#0a172d);
  border:1px solid rgba(0,210,255,0.35); border-radius:20px; padding:22px;
  margin-bottom:14px; box-shadow:0 0 30px rgba(0,210,255,0.07);
}
.gradient-text {
  background:linear-gradient(135deg,#00d2ff,#7b2ff7,#ff6b9d);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.badge { display:inline-block; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:600; }
.badge-cyan   { background:rgba(0,210,255,0.12); color:#00d2ff; border:1px solid rgba(0,210,255,0.3); }
.badge-purple { background:rgba(123,47,247,0.12); color:#a78bfa; border:1px solid rgba(123,47,247,0.3); }
.badge-pink   { background:rgba(255,107,157,0.12); color:#ff6b9d; border:1px solid rgba(255,107,157,0.3); }
.badge-green  { background:rgba(0,230,118,0.12); color:#00e676; border:1px solid rgba(0,230,118,0.3); }
.badge-amber  { background:rgba(255,193,7,0.12); color:#ffc107; border:1px solid rgba(255,193,7,0.3); }
.badge-red    { background:rgba(255,65,108,0.12); color:#ff416c; border:1px solid rgba(255,65,108,0.3); }
.badge-blue   { background:rgba(33,150,243,0.12); color:#42a5f5; border:1px solid rgba(33,150,243,0.3); }
.section-label { font-size:11px; font-weight:600; color:#4a7a98; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px; }
.stat-row { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #0f2040; font-size:13px; }
.stat-row:last-child { border-bottom:none; }
.stat-label { color:#4a7a98; }
.live-pill { display:inline-flex; align-items:center; gap:6px; background:rgba(0,230,118,0.1); border:1px solid rgba(0,230,118,0.25); border-radius:999px; padding:4px 12px; font-size:12px; color:#00e676; }
.live-dot { width:7px; height:7px; background:#00e676; border-radius:50%; animation:blink 1.2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.score-track { height:6px; background:#0d1f38; border-radius:3px; }
.score-fill  { height:6px; border-radius:3px; }
.msg-me     { background:linear-gradient(135deg,#1a2f50,#142440); border:1px solid rgba(0,210,255,0.15); border-radius:14px 14px 2px 14px; padding:9px 14px; margin:4px 0; font-size:13px; }
.msg-other  { background:#0d1f38; border:1px solid #1a3a5c; border-radius:14px 14px 14px 2px; padding:9px 14px; margin:4px 0; font-size:13px; }
.msg-system { background:rgba(123,47,247,0.07); border:1px solid rgba(123,47,247,0.15); border-radius:8px; padding:5px 12px; text-align:center; font-size:11px; color:#6b8fa8; margin:4px 0; }
.invite-code { font-family:monospace; font-size:26px; font-weight:800; letter-spacing:8px; color:#00d2ff; text-align:center; padding:14px; background:#0d1f38; border:2px dashed #1a3a5c; border-radius:14px; margin:10px 0; }
.upi-box { background:rgba(0,230,118,0.06); border:2px dashed rgba(0,230,118,0.25); border-radius:14px; padding:16px; text-align:center; font-family:monospace; color:#00e676; word-break:break-all; margin:10px 0; }
.sos-wrap .stButton>button { background:linear-gradient(135deg,#ff416c,#ff0040) !important; font-size:18px !important; height:80px !important; border-radius:18px !important; box-shadow:0 0 50px rgba(255,65,108,0.4) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session init ───────────────────────────────────────────────────────────────
for k in ["token","user_id","user_name","user_role","user_gender"]:
    if k not in st.session_state:
        st.session_state[k] = None

# 🔥 FORCE RESET IF TOKEN INVALID
if st.session_state.get("token") == "":
    st.session_state.token = None
# ══════════════════════════════════════════════════════════════════════════════
# LOGIN / REGISTER  — no sidebar, completely clean page
# ══════════════════════════════════════════════════════════════════════════════
def render_auth():
    # Hide sidebar + its collapse arrow completely
    st.markdown("""
    <style>
    [data-testid="stSidebar"]        { display:none !important; }
    [data-testid="collapsedControl"] { display:none !important; }
    .block-container { max-width:680px !important; margin:auto !important; padding-top:1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Backend status banner ──────────────────────────────────────────────────
    if not backend_is_up():
        st.markdown("""
        <div style='background:rgba(255,65,108,0.1);border:1px solid rgba(255,65,108,0.35);
                    border-radius:12px;padding:12px 16px;margin-bottom:20px;
                    display:flex;align-items:center;gap:10px;'>
          <span style='font-size:20px;'>🔴</span>
          <div>
            <div style='font-weight:700;color:#ff416c;font-size:13px;'>Backend not running</div>
            <div style='font-size:12px;color:#94a3b8;margin-top:2px;'>
              Open a terminal and run: <code style='color:#00d2ff;background:#0d1f38;
              padding:2px 8px;border-radius:6px;'>python run_backend.py</code>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:rgba(0,230,118,0.07);border:1px solid rgba(0,230,118,0.25);
                    border-radius:12px;padding:10px 16px;margin-bottom:20px;
                    display:flex;align-items:center;gap:10px;'>
          <span style='font-size:16px;'>🟢</span>
          <span style='font-size:12px;color:#00e676;font-weight:600;'>Backend is running — ready to use</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center;padding:20px 0 28px;'>
      <div style='font-size:56px;margin-bottom:12px;'>🚗</div>
      <div style='font-size:2.6rem;font-weight:800;font-family:Syne,sans-serif;'
           class='gradient-text'>CarpoolSafe</div>
      <div style='color:#4a7a98;font-size:14px;margin-top:10px;line-height:1.6;'>
        AI ride matching &nbsp;·&nbsp; Real-time GPS tracking &nbsp;·&nbsp; Women safety &nbsp;·&nbsp; UPI payments
      </div>
      <div style='display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:14px;'>
        <span class='badge badge-cyan'>🤖 AI Matching</span>
        <span class='badge badge-green'>📍 Live GPS</span>
        <span class='badge badge-pink'>🛡️ Women Safety</span>
        <span class='badge badge-purple'>💳 UPI Pay</span>
        <span class='badge badge-amber'>👥 Group Rides</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_login, tab_reg = st.tabs(["🔑  Sign In", "✨  Create Account"])

    # ── SIGN IN TAB ───────────────────────────────────────────────────────────
    with tab_login:
        st.markdown("<br>", unsafe_allow_html=True)
        li_email = st.text_input("Email address", placeholder="you@example.com", key="li_email")
        li_pass  = st.text_input("Password", type="password", placeholder="Your password", key="li_pass")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Sign In  →", key="btn_login", use_container_width=True):
            if not li_email.strip():
                st.error("⚠️ Please enter your email address.")
            elif not li_pass:
                st.error("⚠️ Please enter your password.")
            else:
                with st.spinner("Signing in..."):
                    ok = do_login(li_email.strip().lower(), li_pass)
                if ok:
                    st.success(f"Welcome back, {st.session_state.user_name}! 👋")
                    st.rerun()

        st.markdown("""
        <div style='text-align:center;margin-top:14px;font-size:13px;color:#4a7a98;'>
          No account? Click the <b style='color:#00d2ff;'>Create Account</b> tab above ↑
        </div>""", unsafe_allow_html=True)

    # ── CREATE ACCOUNT TAB ────────────────────────────────────────────────────
    with tab_reg:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            rg_name  = st.text_input("Full Name *",  placeholder="Priya Sharma",      key="rg_name")
            rg_email = st.text_input("Email *",       placeholder="priya@email.com",   key="rg_email")
            rg_pass  = st.text_input("Password *",   type="password",
                                      placeholder="Minimum 6 characters",              key="rg_pass")
            rg_phone = st.text_input("Phone",         placeholder="+91 9876543210",    key="rg_phone")
        with c2:
            rg_gender = st.selectbox("Gender",
                ["", "Female", "Male", "Non-binary", "Prefer not to say"],             key="rg_gender")
            rg_role   = st.selectbox("I am a",  ["rider", "driver", "both"],           key="rg_role")
            rg_vtype  = st.text_input("Vehicle Type",    placeholder="Swift Dzire",    key="rg_vtype")
            rg_vnum   = st.text_input("Vehicle Number",  placeholder="TS 09 AB 1234", key="rg_vnum")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Create Account  →", key="btn_register", use_container_width=True):
            # Field validation
            err = None
            if not rg_name.strip():
                err = "Full name is required."
            elif not rg_email.strip() or "@" not in rg_email:
                err = "Enter a valid email address."
            elif not rg_pass or len(rg_pass) < 6:
                err = "Password must be at least 6 characters."

            if err:
                st.error(f"⚠️ {err}")
            else:
                payload = {
                    "name":           rg_name.strip(),
                    "email":          rg_email.strip().lower(),
                    "password":       rg_pass,
                    "phone_number":   rg_phone.strip(),
                    "gender":         rg_gender or None,
                    "role":           rg_role,
                    "vehicle_type":   rg_vtype.strip() or None,
                    "vehicle_number": rg_vnum.strip() or None,
                }
                with st.spinner("Creating your account..."):
                    
                    result = do_signup(payload)

                if result:
                    user = result.get("user", {})

                    st.session_state.token = result.get("access_token")
                    st.session_state.user_id = result.get("user_id")
                    st.session_state.user_name = result.get("name")
                    st.session_state.user_role = result.get("role")
                    st.session_state.user_gender = ""

                    st.success(f"🎉 Account created! Welcome, {user.get('name')}!")
                    st.balloons()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — shown after login, sidebar visible
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    st.write("✅ Dashboard loaded")
    try:
        import sidebar
        sidebar.render_sidebar()
    except Exception as e:
        st.error(f"Sidebar error: {e}")   # ✅ correctly indented

    import datetime
    hour = datetime.datetime.now().hour
    greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    st.markdown(f"""
    <h1 style='font-family:Syne,sans-serif;font-size:2.1rem;margin-bottom:4px;'>
      {greet}, <span class='gradient-text'>{st.session_state.get("user_name", "User")}</span> 👋
    </h1>
    <p style='color:#4a7a98;margin-bottom:26px;font-size:15px;'>
      Ready to carpool? Here's your dashboard.
    </p>
    """, unsafe_allow_html=True)

    # Quick action cards
    c1,c2,c3,c4 = st.columns(4)
    for col,(icon,title,sub,color,bg,page) in zip([c1,c2,c3,c4],[
        ("🚗","Create Ride",  "Offer seats on your route",  "#00d2ff","rgba(0,210,255,0.08)","pages/1_Create_Ride.py"),
        ("🔍","Find a Ride",  "AI matches rides for you",   "#7b2ff7","rgba(123,47,247,0.08)","pages/2_Search_Rides.py"),
        ("👥","Group Rides",  "Plan trips with friends",    "#00e676","rgba(0,230,118,0.08)","pages/7_Group_Rides.py"),
        ("🛡️","Safety Hub",  "SOS & emergency tools",      "#ff416c","rgba(255,65,108,0.08)","pages/5_Safety_Panel.py"),
    ]):
        with col:
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color}33;border-radius:20px;
                        padding:20px;text-align:center;margin-bottom:8px;'>
              <div style='font-size:34px;'>{icon}</div>
              <div style='font-weight:700;font-family:Syne,sans-serif;
                          margin:8px 0 4px;color:{color};font-size:14px;'>{title}</div>
              <div style='color:#4a7a98;font-size:12px;'>{sub}</div>
            </div>""", unsafe_allow_html=True)
            st.page_link(page, label=f"Open →", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Stats
    try:
        rides = get("/ride/my-rides") or []
        bookings = get("/booking/my-bookings") or []
        groups = get("/group/my-groups") or []
        payments = get("/payment/my-payments") or []
    except Exception as e:
        st.error(f"API Error: {e}")
        rides, bookings, groups, payments = [], [], [], []
        paid = 0 
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🚗 Rides Created", len(rides),    delta=f"{len([r for r in rides if r.get('status')=='scheduled'])} scheduled")
    c2.metric("🎟️ My Bookings",  len(bookings),  delta=f"{len([b for b in bookings if b.get('status')=='confirmed'])} active")
    c3.metric("👥 Groups",        len(groups))
    c4.metric("💳 Total Paid",    f"₹{paid:.0f}")

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1.4], gap="large")

    with col_l:
        st.markdown("<div class='section-label'>Recent Activity</div>", unsafe_allow_html=True)
        items = (rides + bookings)[:5]
        if items:
            for item in items[:4]:
                if "source_address" in item:
                    lbl  = f"{item['source_address'][:20]}… → {item['destination_address'][:20]}…"
                    meta = f"🕐 {item['departure_time'][:16].replace('T',' ')} · 💺 {item['available_seats']}/{item['total_seats']}"
                    sc   = {"scheduled":"badge-cyan","active":"badge-green","completed":"badge-purple","cancelled":"badge-red"}.get(item.get("status",""),"badge-blue")
                    st_  = item.get("status","").upper()
                else:
                    lbl  = f"{item['pickup_address'][:20]}… → {item['drop_address'][:20]}…"
                    meta = f"💺 {item['seats_booked']} seat(s) · ₹{item.get('estimated_price',0):.0f}"
                    sc   = {"confirmed":"badge-green","cancelled":"badge-red","completed":"badge-cyan"}.get(item.get("status",""),"badge-amber")
                    st_  = item.get("status","").upper()
                st.markdown(f"""
                <div class='gcard' style='padding:14px;margin-bottom:8px;'>
                  <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                      <div style='font-size:13px;font-weight:600;'>{lbl}</div>
                      <div style='font-size:11px;color:#4a7a98;margin-top:3px;'>{meta}</div>
                    </div>
                    <span class='badge {sc}'>{st_}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='gcard' style='text-align:center;padding:28px;'>
              <div style='font-size:36px;'>🚗</div>
              <div style='color:#4a7a98;margin-top:8px;font-size:13px;'>
                No rides yet — create or book your first ride!
              </div>
            </div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-label'>Hyderabad Ride Network</div>", unsafe_allow_html=True)
        try:
            import folium
            from streamlit_folium import st_folium
            m = folium.Map(location=[17.385,78.4867], zoom_start=11, tiles="CartoDB dark_matter")
            for name,lat,lng,color in [
                ("HITEC City",17.4435,78.3772,"#00d2ff"),("Charminar",17.3616,78.4747,"#ff6b9d"),
                ("Gachibowli",17.4401,78.3489,"#7b2ff7"),("Banjara Hills",17.4165,78.4480,"#ffc107"),
                ("Secunderabad",17.4399,78.4983,"#00e676"),("Madhapur",17.4478,78.3909,"#42a5f5"),
                ("LB Nagar",17.3469,78.5528,"#ff9800"),("Kukatpally",17.4849,78.4138,"#ff416c"),
            ]:
                folium.CircleMarker([lat,lng],radius=8,color=color,fill=True,
                    fill_color=color,fill_opacity=0.85,popup=name,tooltip=name).add_to(m)
            st_folium(m, height=340, use_container_width=True)
        except ImportError:
            st.markdown("""
            <div class='gcard' style='text-align:center;padding:36px;'>
              <div style='font-size:36px;'>🗺️</div>
              <div style='color:#4a7a98;font-size:13px;margin-top:10px;'>
                Run: <code>pip install streamlit-folium folium</code>
              </div>
            </div>""", unsafe_allow_html=True)


# ── MAIN ROUTING ───────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth()
else:
    try:
        render_dashboard()
    except Exception as e:
        st.error(f"🔥 Dashboard crash: {e}")