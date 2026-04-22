import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import get, post, is_logged_in
from frontend.theme import inject_css, HYD_LOCATIONS
from frontend.sidebar import render_sidebar
from datetime import datetime, timedelta, date, time

st.set_page_config(page_title="Group Rides – CarpoolSafe", page_icon="👥", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>👥 Group <span class='gradient-text'>Rides</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4a7a98;margin-bottom:20px;'>Plan rides together — schedule voting, group chat, shared pickups</p>", unsafe_allow_html=True)

tab_my, tab_create, tab_join, tab_detail = st.tabs(["📋 My Groups", "➕ Create", "🔑 Join via Code", "💬 Group Detail"])

with tab_my:
    if st.button("🔄 Refresh", key="ref_grp"): st.rerun()
    groups = get("/group/my-groups") or []
    if not groups:
        st.markdown("""<div style='text-align:center;padding:50px;color:#4a7a98;'>
          <div style='font-size:40px;'>👥</div>
          <div style='margin-top:10px;color:#94a3b8;'>No groups yet — create or join one</div>
        </div>""", unsafe_allow_html=True)
    for g in groups:
        sc = {"open": "#00d2ff", "locked": "#ffc107", "confirmed": "#00e676", "cancelled": "#ff416c"}.get(g["status"], "#4a7a98")
        ob = " <span class='badge badge-cyan'>Organizer</span>" if g["is_organizer"] else ""
        st.markdown(f"""<div class='gcard' style='border-left:3px solid {sc};'>
          <div style='display:flex;justify-content:space-between;'>
            <div>
              <div style='font-weight:700;font-size:15px;'>{g['name']}{ob}</div>
              <div style='color:#4a7a98;font-size:12px;margin-top:3px;'>👥 {g['member_count']} members · {g.get('destination','TBD') or 'TBD'}</div>
            </div>
            <div style='text-align:right;'>
              <span style='color:{sc};border:1px solid {sc}44;background:{sc}11;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;'>{g['status'].upper()}</span>
              <div style='font-size:11px;color:#4a7a98;margin-top:4px;'>Code: <b style='color:#00d2ff;font-family:monospace;'>{g['invite_code']}</b></div>
            </div>
          </div></div>""", unsafe_allow_html=True)
        if st.button(f"💬 Open", key=f"opn_{g['group_id']}"):
            st.session_state["active_group_id"] = g["group_id"]; st.rerun()

with tab_create:
    with st.form("create_grp"):
        name = st.text_input("Group Name *", placeholder="Office Commute Squad")
        desc = st.text_area("Description", height=70)
        c1, c2 = st.columns(2)
        with c1:
            dp = st.selectbox("Destination", list(HYD_LOCATIONS.keys()))
            da = st.text_input("Destination Address")
        with c2:
            mx = st.number_input("Max Members", 2, 12, 6)
            pd = st.date_input("Proposed Date", value=date.today() + timedelta(days=1))
            pt = st.time_input("Proposed Time", value=time(8, 0))
        if st.form_submit_button("🚀 Create Group", use_container_width=True):
            if not name:
                st.error("Group name is required.")
            else:
                coords = HYD_LOCATIONS.get(dp)
                r = post("/group/create", {
                    "name": name, "description": desc or None,
                    "destination_address": da or dp,
                    "destination_lat": coords[0] if coords else None,
                    "destination_lng": coords[1] if coords else None,
                    "proposed_date": datetime.combine(pd, pt).isoformat(),
                    "max_members": int(mx),
                })
                if r:
                    st.success(f"Group '{name}' created!")
                    st.markdown(f"<div class='invite-code'>{r['invite_code']}</div>", unsafe_allow_html=True)
                    st.info("Share this code with your friends!")
                    st.session_state["active_group_id"] = r["id"]

with tab_join:
    c1, c2 = st.columns([3, 1])
    with c1: code = st.text_input("Invite Code", placeholder="A3BX7K2M", max_chars=8)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Join", use_container_width=True) and code:
            r = post(f"/group/join/{code.strip().upper()}", {})
            if r:
                st.success(r["message"])
                st.session_state["active_group_id"] = r["group_id"]; st.rerun()

with tab_detail:
    gid = st.session_state.get("active_group_id")
    if not gid:
        st.info("Select a group from 'My Groups' tab first.")
    else:
        grp = get(f"/group/{gid}")
        if not grp:
            st.error("Could not load group.")
        else:
            col_l, col_r = st.columns([1, 1.3], gap="large")
            with col_l:
                st.markdown(f"""<div class='gcard-glow'>
                  <div style='font-weight:800;font-size:17px;font-family:Syne,sans-serif;'>{grp['name']}</div>
                  <div style='color:#4a7a98;font-size:12px;margin-top:3px;'>{grp.get('description','') or ''}</div>
                  <div style='margin-top:10px;font-size:12px;color:#94a3b8;'>
                    📍 {grp.get('destination_address','TBD')}<br>
                    👤 Organizer: <b style='color:#00d2ff;'>{grp['organizer_name']}</b><br>
                    Status: <b style='color:#00e676;'>{grp['status'].upper()}</b>
                  </div>
                  <div style='margin-top:10px;font-size:11px;color:#4a7a98;'>Invite Code</div>
                  <div class='invite-code' style='font-size:20px;letter-spacing:5px;padding:8px;'>{grp['invite_code']}</div>
                </div>""", unsafe_allow_html=True)

                st.markdown("<div class='section-label'>👥 Members</div>", unsafe_allow_html=True)
                colors = ["#00d2ff", "#a78bfa", "#ff6b9d", "#00e676", "#ffc107", "#42a5f5"]
                for i, m in enumerate(grp.get("members", [])):
                    color = colors[i % len(colors)]
                    gi = "👩" if (m.get("user_gender") or "").lower() == "female" else "👤"
                    st.markdown(f"""<div style='display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #0f2040;'>
                      <div style='width:30px;height:30px;border-radius:50%;background:{color}22;border:1px solid {color}55;
                                  display:flex;align-items:center;justify-content:center;font-size:12px;color:{color};font-weight:700;'>
                        {m['user_name'][0].upper()}
                      </div>
                      <div>
                        <div style='font-size:13px;font-weight:600;'>{gi} {m['user_name']}</div>
                        <div style='font-size:11px;color:#4a7a98;'>📍 {m.get('pickup_address','Not set')}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                with st.expander("📍 Set My Pickup"):
                    with st.form("set_pickup"):
                        pp = st.selectbox("Quick pick", list(HYD_LOCATIONS.keys()))
                        pa = st.text_input("Pickup Address")
                        pc = HYD_LOCATIONS.get(pp)
                        cl, cn = st.columns(2)
                        with cl: plat = st.number_input("Lat", value=pc[0] if pc else 17.4435, format="%.6f")
                        with cn: plng = st.number_input("Lng", value=pc[1] if pc else 78.3772, format="%.6f")
                        if st.form_submit_button("Set Pickup") and pa:
                            r = put(f"/group/{gid}/pickup", {"pickup_address": pa, "pickup_lat": plat, "pickup_lng": plng})
                            if r: st.success("Updated!"); st.rerun()

                if grp["organizer_id"] == st.session_state.get("user_id") and grp["status"] != "confirmed":
                    st.markdown("<div class='section-label' style='margin-top:12px;'>✅ Confirm Ride</div>", unsafe_allow_html=True)
                    rides = get("/ride/my-rides", silent=True) or []
                    if rides:
                        rm = {f"{r['source_address'][:18]}→{r['destination_address'][:18]}": r["id"] for r in rides}
                        sel = st.selectbox("Link your ride", list(rm.keys()))
                        if st.button("🎯 Confirm Group Ride"):
                            r = post(f"/group/{gid}/confirm", {"ride_id": rm[sel]})
                            if r: st.success(r["message"]); st.rerun()
                    else:
                        st.info("Create a ride first.")

                if grp["organizer_id"] != st.session_state.get("user_id"):
                    if st.button("🚪 Leave Group"):
                        r = delete(f"/group/{gid}/leave")
                        if r:
                            st.success("Left group.")
                            del st.session_state["active_group_id"]; st.rerun()

            with col_r:
                st.markdown("<div class='section-label'>🗓️ Schedule Voting</div>", unsafe_allow_html=True)
                scheds = grp.get("schedules", [])
                if scheds:
                    mx_v = max((s["vote_count"] for s in scheds), default=1) or 1
                    for s in sorted(scheds, key=lambda x: -x["vote_count"]):
                        pct = int((s["vote_count"] / mx_v) * 100)
                        voted = st.session_state.get("user_id", "") in (s["votes"] or [])
                        bc = "#00e676" if pct >= 75 else "#ffc107" if pct >= 40 else "#4a7a98"
                        st.markdown(f"""<div style='background:#0d1f38;border:1px solid {"rgba(0,230,118,0.25)" if voted else "#1a3a5c"};border-radius:12px;padding:10px;margin-bottom:7px;'>
                          <div style='display:flex;justify-content:space-between;'>
                            <b style='font-size:13px;color:{"#00e676" if voted else "#e8f4fd"};'>{s['proposed_time'][:16].replace("T"," ")}</b>
                            <span style='font-size:11px;color:#4a7a98;'>{"✅ Voted · " if voted else ""}{s['vote_count']} vote(s)</span>
                          </div>
                          <div style='height:5px;background:#050b18;border-radius:3px;margin-top:7px;'>
                            <div style='height:5px;width:{pct}%;background:{bc};border-radius:3px;'></div>
                          </div></div>""", unsafe_allow_html=True)
                        if st.button(f"{'✅ Unvote' if voted else '👍 Vote'}", key=f"v_{s['id']}"):
                            post(f"/group/{gid}/schedule/vote", {"schedule_vote_id": s["id"]}); st.rerun()
                else:
                    st.info("No time slots yet.")
                with st.expander("➕ Propose a time"):
                    with st.form("prop"):
                        pd2 = st.date_input("Date", value=date.today() + timedelta(days=1))
                        pt2 = st.time_input("Time", value=time(8, 0))
                        if st.form_submit_button("Propose"):
                            post(f"/group/{gid}/schedule/propose",
                                 {"proposed_time": datetime.combine(pd2, pt2).isoformat()}); st.rerun()

                st.markdown("<div class='section-label' style='margin-top:14px;'>💬 Group Chat</div>", unsafe_allow_html=True)
                for msg in grp.get("messages", [])[-20:]:
                    if msg["message_type"] == "system":
                        st.markdown(f"<div class='msg-system'>{msg['content']}</div>", unsafe_allow_html=True)
                    elif msg["sender_id"] == st.session_state.get("user_id"):
                        st.markdown(f"<div style='text-align:right;'><div class='msg-me'><div>{msg['content']}</div><div style='font-size:10px;opacity:.5;'>{msg.get('created_at','')[11:16]}</div></div></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='msg-other'><div style='font-size:10px;color:#4a7a98;'>{msg['sender_name']}</div><div>{msg['content']}</div><div style='font-size:10px;opacity:.5;'>{msg.get('created_at','')[11:16]}</div></div>", unsafe_allow_html=True)

                with st.form("chat", clear_on_submit=True):
                    c1, c2 = st.columns([5, 1])
                    with c1: txt = st.text_input("", placeholder="Type a message…", label_visibility="collapsed")
                    with c2: snd = st.form_submit_button("Send")
                    if snd and txt.strip():
                        post(f"/group/{gid}/message", {"content": txt.strip()}); st.rerun()
