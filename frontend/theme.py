"""
Shared theme injector — imports master CSS from app.py context.
All pages call inject_css() at top.
"""
import streamlit as st

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');
html,body,[data-testid="stApp"]{background:#050b18!important;color:#e8f4fd!important;font-family:'Inter',sans-serif!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#080f1f,#0a1628)!important;border-right:1px solid #0f2040!important}
[data-testid="stSidebar"] *{color:#e8f4fd!important}
h1,h2,h3,h4{font-family:'Syne',sans-serif!important}
.stButton>button{background:linear-gradient(135deg,#00d2ff,#7b2ff7)!important;color:#fff!important;font-weight:700!important;font-family:'Syne',sans-serif!important;border:none!important;border-radius:14px!important;padding:11px 24px!important;font-size:14px!important;box-shadow:0 4px 24px rgba(0,210,255,0.2)!important;transition:all 0.2s!important}
.stButton>button:hover{transform:translateY(-2px) scale(1.02)!important;box-shadow:0 8px 32px rgba(123,47,247,0.4)!important}
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div>div,.stNumberInput>div>div>input,.stDateInput>div>div>input,.stTimeInput>div>div>input{background:#0d1f38!important;color:#e8f4fd!important;border:1px solid #1a3a5c!important;border-radius:12px!important;font-family:'Inter',sans-serif!important}
.stTabs [data-baseweb="tab-list"]{background:#0d1f38!important;border-radius:14px!important;padding:5px!important;gap:4px!important;border:1px solid #1a3a5c!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#6b8fa8!important;border-radius:10px!important;font-family:'Inter',sans-serif!important;font-weight:500!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#00d2ff22,#7b2ff722)!important;color:#00d2ff!important;border-bottom:2px solid #00d2ff!important}
[data-testid="metric-container"]{background:linear-gradient(135deg,#0d1f38,#0a172d)!important;border:1px solid #1a3a5c!important;border-radius:16px!important;padding:18px!important}
[data-testid="stMetricValue"]{color:#e8f4fd!important;font-family:'Syne',sans-serif!important}
.stCheckbox label,.stRadio label{color:#b8d4e8!important}
.streamlit-expanderHeader{background:#0d1f38!important;border-radius:12px!important;border:1px solid #1a3a5c!important;color:#e8f4fd!important}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#080f1f}::-webkit-scrollbar-thumb{background:#1a3a5c;border-radius:3px}
[data-testid="stPageLink"] a{color:#6b8fa8!important;border-radius:10px!important}
[data-testid="stPageLink"] a:hover{background:#0d1f38!important;color:#00d2ff!important}
.gcard{background:linear-gradient(135deg,#0d1f38,#0a172d);border:1px solid #1a3a5c;border-radius:20px;padding:20px;margin-bottom:12px;transition:border-color 0.2s}
.gcard:hover{border-color:#00d2ff44}
.gcard-glow{background:linear-gradient(135deg,#0d1f38,#0a172d);border:1px solid #00d2ff55;border-radius:20px;padding:20px;margin-bottom:12px;box-shadow:0 0 30px rgba(0,210,255,0.07)}
.gradient-text{background:linear-gradient(135deg,#00d2ff,#7b2ff7,#ff6b9d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.badge{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:600;font-family:'Inter',sans-serif}
.badge-cyan{background:rgba(0,210,255,0.12);color:#00d2ff;border:1px solid rgba(0,210,255,0.3)}
.badge-purple{background:rgba(123,47,247,0.12);color:#a78bfa;border:1px solid rgba(123,47,247,0.3)}
.badge-pink{background:rgba(255,107,157,0.12);color:#ff6b9d;border:1px solid rgba(255,107,157,0.3)}
.badge-green{background:rgba(0,230,118,0.12);color:#00e676;border:1px solid rgba(0,230,118,0.3)}
.badge-amber{background:rgba(255,193,7,0.12);color:#ffc107;border:1px solid rgba(255,193,7,0.3)}
.badge-red{background:rgba(255,65,108,0.12);color:#ff416c;border:1px solid rgba(255,65,108,0.3)}
.badge-blue{background:rgba(33,150,243,0.12);color:#42a5f5;border:1px solid rgba(33,150,243,0.3)}
.badge-orange{background:rgba(255,152,0,0.12);color:#ff9800;border:1px solid rgba(255,152,0,0.3)}
.section-label{font-size:11px;font-weight:600;color:#4a7a98;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;font-family:'Inter',sans-serif}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #0f2040;font-size:13px}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#4a7a98}
.live-pill{display:inline-flex;align-items:center;gap:6px;background:rgba(0,230,118,0.1);border:1px solid rgba(0,230,118,0.25);border-radius:999px;padding:4px 12px;font-size:12px;color:#00e676}
.live-dot{width:7px;height:7px;background:#00e676;border-radius:50%;animation:blink 1.2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.score-track{height:6px;background:#0d1f38;border-radius:3px}
.score-fill{height:6px;border-radius:3px}
.msg-me{background:linear-gradient(135deg,#1a2f50,#142440);border:1px solid rgba(0,210,255,0.15);border-radius:14px 14px 2px 14px;padding:9px 14px;margin:4px 0;font-size:13px}
.msg-other{background:#0d1f38;border:1px solid #1a3a5c;border-radius:14px 14px 14px 2px;padding:9px 14px;margin:4px 0;font-size:13px}
.msg-system{background:rgba(123,47,247,0.07);border:1px solid rgba(123,47,247,0.15);border-radius:8px;padding:5px 12px;text-align:center;font-size:11px;color:#6b8fa8;margin:4px 0}
.invite-code{font-family:monospace;font-size:26px;font-weight:800;letter-spacing:8px;color:#00d2ff;text-align:center;padding:14px;background:#0d1f38;border:2px dashed #1a3a5c;border-radius:14px;margin:10px 0}
.upi-box{background:rgba(0,230,118,0.06);border:2px dashed rgba(0,230,118,0.25);border-radius:14px;padding:16px;text-align:center;font-family:monospace;color:#00e676;word-break:break-all;margin:10px 0}
.sos-wrap .stButton>button{background:linear-gradient(135deg,#ff416c,#ff0040)!important;font-size:18px!important;height:80px!important;border-radius:18px!important;box-shadow:0 0 50px rgba(255,65,108,0.4)!important}
.signout-btn .stButton>button{background:linear-gradient(135deg,#ff416c,#ff4b2b)!important;box-shadow:0 4px 20px rgba(255,65,108,0.3)!important}
</style>
""", unsafe_allow_html=True)

HYD_LOCATIONS = {
    "Custom": None,
    "HITEC City": (17.4435, 78.3772),
    "Gachibowli": (17.4401, 78.3489),
    "Charminar": (17.3616, 78.4747),
    "Banjara Hills": (17.4165, 78.4480),
    "Secunderabad": (17.4399, 78.4983),
    "Kukatpally": (17.4849, 78.4138),
    "Madhapur": (17.4478, 78.3909),
    "LB Nagar": (17.3469, 78.5528),
    "Uppal": (17.4054, 78.5581),
    "Ameerpet": (17.4374, 78.4487),
}
