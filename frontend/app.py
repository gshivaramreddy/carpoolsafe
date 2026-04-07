import streamlit as st
import requests

st.title("🚗 CarpoolSafe")

if st.button("Check Backend"):
    try:
        res = requests.get("https://carpoolsafe.onrender.com")
        st.success("Backend working ✅")
    except:
        st.error("Backend failed ❌")