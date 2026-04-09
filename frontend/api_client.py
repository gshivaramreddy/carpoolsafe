import requests
import streamlit as st
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()

BACKEND_URL = "https://carpoolsafe.onrender.com"
st.write("🚀 BACKEND URL:", BACKEND_URL)
TIMEOUT = 60


def build_url(endpoint: str) -> str:
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return f"{BACKEND_URL}{endpoint}"


def get_headers() -> Dict[str, str]:
    token = st.session_state.get("token")
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def handle_response(resp: requests.Response, silent: bool = False) -> Optional[Any]:
    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except Exception:
            return {"ok": True}

    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text

    if not silent:
        st.error(f"❌ Error {resp.status_code}: {detail}")

    return None


def post(endpoint: str, data: dict, auth: bool = True):
    try:
        res = requests.post(
            build_url(endpoint),
            json=data,
            headers=get_headers() if auth else {"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        return res.json()

    except Exception as e:
        st.error(f"POST error: {e}")
        return None

def get(endpoint):
    try:
        res = requests.get(
            build_url(endpoint),
            headers=get_headers(),   # ✅ ADD THIS LINE
            timeout=TIMEOUT
        )

        if res.status_code == 401:
            st.warning("⚠️ Please login first")
            return []

        if res.status_code != 200:
            st.error(f"API error: {res.status_code}")
            return []

        return res.json()

    except Exception as e:
        st.error(f"⚠️ Backend error: {e}")
        return []


def is_logged_in():
    return False   # 🔥 FORCE LOGOUT ALWAYS

def do_logout():
    st.session_state.clear()


def do_login(email, password):
    try:
        url = build_url("/auth/login")

        response = requests.post(
            url,
            json={
                "email": email,
                "password": password
            },
            timeout=TIMEOUT
        )

        data = handle_response(response)

        if data and "access_token" in data:
            # ✅ STORE EVERYTHING
            st.session_state.token = data["access_token"]
            st.session_state.user_id = data.get("user_id")
            st.session_state.user_name = data.get("name")
            st.session_state.role = data.get("role")
            st.session_state.logged_in = True

            return True

        return False

    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return False

def do_signup(data: dict):
    return post("/auth/signup", data, auth=False)


def backend_is_up() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False