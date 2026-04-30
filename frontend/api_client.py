import requests
import streamlit as st
import os
from typing import Optional, Dict, Any

BACKEND_URL = os.getenv("BACKEND_URL", "https://carpoolsafe.onrender.com").rstrip("/")
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
    if resp.status_code == 401:
        st.session_state.clear()
        st.warning("Session expired — please sign in again.")
        st.rerun()
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    if not silent:
        st.error(f"❌ Error {resp.status_code}: {detail}")
    return None


def post(endpoint: str, data: dict, auth: bool = True, silent: bool = False):
    try:
        headers = get_headers() if auth else {"Content-Type": "application/json"}
        resp = requests.post(
            build_url(endpoint),
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )
        return handle_response(resp, silent)
    except requests.exceptions.Timeout:
        if not silent:
            st.error("⏱️ Backend is waking up. Please wait 30s and try again.")
        return None
    except Exception as e:
        if not silent:
            st.error(f"POST error: {e}")
        return None


def get(endpoint: str, params: dict = None, silent: bool = False):
    try:
        resp = requests.get(
            build_url(endpoint),
            params=params,
            headers=get_headers(),
            timeout=TIMEOUT,
        )
        return handle_response(resp, silent)
    except requests.exceptions.Timeout:
        if not silent:
            st.error("⏱️ Backend is waking up. Please wait 30s and try again.")
        return None
    except Exception as e:
        if not silent:
            st.error(f"GET error: {e}")
        return None


def put(endpoint: str, data: dict, silent: bool = False):
    try:
        resp = requests.put(
            build_url(endpoint),
            json=data,
            headers=get_headers(),
            timeout=TIMEOUT,
        )
        return handle_response(resp, silent)
    except requests.exceptions.Timeout:
        if not silent:
            st.error("⏱️ Request timed out. Please try again.")
        return None
    except Exception as e:
        if not silent:
            st.error(f"PUT error: {e}")
        return None


def delete(endpoint: str, silent: bool = False):
    try:
        resp = requests.delete(
            build_url(endpoint),
            headers=get_headers(),
            timeout=TIMEOUT,
        )
        return handle_response(resp, silent)
    except Exception as e:
        if not silent:
            st.error(f"DELETE error: {e}")
        return None


def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))


def do_logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def do_login(email: str, password: str) -> bool:
    result = post("/auth/login", {"email": email, "password": password}, auth=False)
    if result and result.get("access_token"):
        st.session_state.token     = result.get("access_token")
        st.session_state.user_id   = result.get("user_id")
        st.session_state.user_name = result.get("name")
        st.session_state.user_role = result.get("role")
        profile = get("/auth/me", silent=True)
        if profile:
            st.session_state.user_gender = profile.get("gender", "")
            if profile.get("name"):
                st.session_state.user_name = profile.get("name")
        return True
    return False


def do_signup(data: dict):
    return post("/auth/signup", data, auth=False)


def backend_is_up() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False