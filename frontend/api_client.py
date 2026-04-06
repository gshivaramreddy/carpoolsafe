import requests
import streamlit as st
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 15


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
        url = build_url(endpoint)
        headers = get_headers() if auth else {"Content-Type": "application/json"}

        resp = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        return handle_response(resp)

    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def get(endpoint: str):
    try:
        url = build_url(endpoint)
        resp = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        return handle_response(resp)
    except Exception:
        return None


def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))


def do_logout():
    st.session_state.clear()


def do_login(email: str, password: str) -> bool:
    result = post("/auth/login", {"email": email, "password": password}, auth=False)

    if result:
        user = result.get("user", {})

        st.session_state.token = result.get("access_token")
        st.session_state.user_id = user.get("id")
        st.session_state.user_name = user.get("name")
        st.session_state.user_role = user.get("role")
        st.session_state.user_gender = user.get("gender", "")

        return True

    return False


def do_signup(data: dict):
    return post("/auth/signup", data, auth=False)


def backend_is_up() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False