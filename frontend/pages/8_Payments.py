import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.api_client import get, post, is_logged_in
from frontend.theme import inject_css
from frontend.sidebar import render_sidebar

st.set_page_config(page_title="Payments – CarpoolSafe", page_icon="💳", layout="wide")
inject_css()

st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important;}</style>', unsafe_allow_html=True)
if not is_logged_in():
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="← Go to Login")
    st.stop()
render_sidebar()

st.markdown("<h1 style='font-family:Syne,sans-serif;'>💳 Payments & <span class='gradient-text'>Cost Split</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4a7a98;margin-bottom:20px;'>Automated fare splitting, UPI payments, and tracking</p>", unsafe_allow_html=True)

STATUS_STYLE = {
    "pending":   ("badge-amber", "⏳ Pending"),
    "completed": ("badge-green", "✅ Paid"),
    "failed":    ("badge-red",   "❌ Failed"),
    "refunded":  ("badge-purple","↩️ Refunded"),
}

tab_pay, tab_split, tab_summary, tab_history = st.tabs(["💸 Pay for Ride", "⚖️ Cost Split", "📊 Ride Summary", "📜 History"])

with tab_pay:
    st.markdown("### 💸 Pay for a Booking")
    bookings = get("/booking/my-bookings") or []
    conf = [b for b in bookings if b["status"] == "confirmed"]
    if not conf:
        st.info("No confirmed bookings to pay for.")
    else:
        bmap = {f"{b['pickup_address'][:22]}→{b['drop_address'][:22]} (₹{b.get('estimated_price',0):.0f})": b for b in conf}
        sel_label = st.selectbox("Select Booking", list(bmap.keys()))
        sel = bmap[sel_label]
        fare = sel.get("estimated_price", 0)
        st.markdown(f"""
        <div class='gcard-glow'>
          <div style='display:flex;justify-content:space-between;align-items:center;'>
            <div>
              <div style='font-weight:700;font-size:14px;'>📍 {sel['pickup_address']} → {sel['drop_address']}</div>
              <div style='color:#4a7a98;font-size:12px;margin-top:4px;'>💺 {sel['seats_booked']} seat(s)</div>
            </div>
            <div style='text-align:right;'>
              <div style='font-size:26px;font-weight:800;color:#00e676;'>₹{fare:.2f}</div>
              <div style='font-size:10px;color:#4a7a98;'>Total fare</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        method = st.radio("Payment Method", ["upi", "cash", "wallet", "card"], horizontal=True,
            format_func=lambda x: {"upi": "📱 UPI", "cash": "💵 Cash", "wallet": "👛 Wallet", "card": "💳 Card"}[x])

        if st.button(f"🚀 Pay ₹{fare:.0f} via {method.upper()}", use_container_width=True):
            result = post("/payment/initiate", {"booking_id": sel["id"], "payment_method": method})
            if result:
                st.session_state["pending_payment"] = result

        pending = st.session_state.get("pending_payment")
        if pending:
            if pending.get("payment_method") == "upi":
                st.markdown(f"""
                <div class='upi-box'>
                  <div style='font-size:12px;color:#4a7a98;margin-bottom:6px;'>Pay to (UPI ID)</div>
                  <div style='font-size:16px;font-weight:700;color:#00e676;'>{pending.get('upi_id','')}</div>
                  <div style='font-size:13px;margin-top:8px;'>Amount: <b style='color:#00e676;font-size:18px;'>₹{pending.get('amount',0):.2f}</b></div>
                </div>""", unsafe_allow_html=True)
                st.code(pending.get("upi_link", ""), language=None)
                st.caption("Open in GPay, PhonePe, or Paytm")
                with st.form("confirm_upi"):
                    txn = st.text_input("UPI Transaction ID (after paying)")
                    if st.form_submit_button("✅ Confirm Payment", use_container_width=True):
                        r = post("/payment/confirm", {"payment_id": pending["payment_id"], "transaction_id": txn or None})
                        if r:
                            st.success(f"✅ Confirmed! Txn: {r['transaction_id']}")
                            st.session_state.pop("pending_payment", None); st.rerun()
            else:
                st.info(pending.get("instruction", ""))
                if st.button("✅ Confirm Payment", use_container_width=True, key="conf_pay"):
                    r = post("/payment/confirm", {"payment_id": pending["payment_id"]})
                    if r:
                        st.success(f"✅ ₹{r['amount']:.2f} confirmed!")
                        st.session_state.pop("pending_payment", None); st.rerun()

with tab_split:
    st.markdown("### ⚖️ Compute Cost Split")
    rides = get("/ride/my-rides") or []
    if not rides:
        st.info("No rides as driver.")
    else:
        rmap = {f"{r['source_address'][:18]}→{r['destination_address'][:18]} ({r['departure_time'][:10]})": r["id"] for r in rides}
        sel_label = st.selectbox("Select Your Ride", list(rmap.keys()))
        ride_id = rmap[sel_label]
        method = st.selectbox("Split Method", ["equal", "distance", "seats", "custom"],
            format_func=lambda x: {"equal": "🟰 Equal — split evenly", "distance": "📏 By distance",
                                    "seats": "💺 By seats booked", "custom": "✏️ Custom amounts"}[x])
        if st.button("⚖️ Compute Split", use_container_width=True):
            result = post("/payment/split/compute", {"ride_id": ride_id, "split_method": method})
            if result: st.session_state["split_result"] = result

        split = st.session_state.get("split_result")
        if split and split.get("ride_id") == ride_id:
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total", f"₹{split['total_cost']:.2f}")
            c2.metric("⚖️ Method", split["split_method"].title())
            c3.metric("👥 Riders", len(split["per_person"]))
            colors = ["#00d2ff", "#a78bfa", "#ff6b9d", "#00e676", "#ffc107"]
            for i, p in enumerate(split["per_person"]):
                color = colors[i % len(colors)]
                pct = int((p["amount"] / split["total_cost"]) * 100) if split["total_cost"] else 0
                st.markdown(f"""
                <div style='background:{color}0d;border:1px solid {color}33;border-radius:14px;padding:12px 16px;margin-bottom:8px;'>
                  <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div><span style='font-weight:700;font-size:14px;color:{color};'>{p['name']}</span>
                      <span style='color:#4a7a98;font-size:12px;margin-left:8px;'>💺 {p['seats']} seat(s)</span></div>
                    <span style='font-size:20px;font-weight:800;color:{color};'>₹{p['amount']:.2f}</span>
                  </div>
                  <div style='height:4px;background:#050b18;border-radius:2px;margin-top:8px;'>
                    <div style='height:4px;width:{pct}%;background:{color};border-radius:2px;'></div>
                  </div>
                  <div style='font-size:11px;color:#4a7a98;margin-top:3px;'>{pct}% of total</div>
                </div>""", unsafe_allow_html=True)

with tab_summary:
    st.markdown("### 📊 Ride Payment Summary")
    rid = st.text_input("Ride ID", placeholder="Enter ride ID")
    if st.button("Load Summary") and rid:
        summary = get(f"/payment/ride/{rid}/summary")
        if summary:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Expected", f"₹{summary['total_expected']:.2f}")
            c2.metric("✅ Collected", f"₹{summary['total_collected']:.2f}")
            c3.metric("⏳ Pending", f"₹{summary['total_pending']:.2f}")
            c4.metric("📊 Rate", summary["collection_rate"])
            for b in summary.get("bookings", []):
                ps = b.get("payment_status", "not_initiated")
                bc, bl = STATUS_STYLE.get(ps, ("badge-cyan", ps.title()))
                st.markdown(f"""
                <div style='display:flex;justify-content:space-between;align-items:center;
                            padding:8px 0;border-bottom:1px solid #0f2040;'>
                  <div><b>{b['rider']}</b> <span style='color:#4a7a98;font-size:12px;'>· {b['seats']} seat(s)</span></div>
                  <div style='display:flex;gap:10px;align-items:center;'>
                    <span style='color:#00e676;font-weight:700;'>₹{b.get('fare',0):.2f}</span>
                    <span class='badge {bc}'>{bl}</span>
                  </div>
                </div>""", unsafe_allow_html=True)

with tab_history:
    st.markdown("### 📜 My Payment History")
    if st.button("🔄 Refresh", key="ref_pay"): st.rerun()
    payments = get("/payment/my-payments") or []
    if not payments:
        st.info("No payments yet.")
    else:
        paid = sum(p["amount"] for p in payments if p["status"] == "completed")
        pend = sum(p["amount"] for p in payments if p["status"] == "pending")
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ Total Paid", f"₹{paid:.2f}")
        c2.metric("⏳ Pending", f"₹{pend:.2f}")
        c3.metric("📊 Transactions", len(payments))
        colors = ["#00d2ff", "#a78bfa", "#00e676", "#ffc107"]
        for i, p in enumerate(payments):
            bc, bl = STATUS_STYLE.get(p["status"], ("badge-cyan", "?"))
            color = colors[i % len(colors)]
            st.markdown(f"""
            <div style='background:{color}08;border:1px solid {color}22;border-radius:14px;padding:12px 16px;margin-bottom:8px;'>
              <div style='display:flex;justify-content:space-between;align-items:center;'>
                <div>
                  <div style='font-weight:700;font-size:13px;'>To: {p['payee']}</div>
                  <div style='font-size:12px;color:#4a7a98;'>
                    {p.get('method','?').upper()} · {p.get('created_at','')[:10]}
                    {f" · Txn: {p['transaction_id']}" if p.get('transaction_id') else ''}
                  </div>
                </div>
                <div style='text-align:right;'>
                  <div style='font-size:20px;font-weight:800;color:{color};'>₹{p['amount']:.2f}</div>
                  <span class='badge {bc}'>{bl}</span>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
