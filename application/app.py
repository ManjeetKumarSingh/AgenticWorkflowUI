import os
import streamlit as st
from auth.auth import AuthManager
from ui.auth_ui import render_login, render_register, render_logout_button
from ui.dashboard import render_dashboard
from utils.redis_client import redis_client
from utils.loggers import logger

# Load .env if available
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

st.set_page_config(page_title="FlowForge", page_icon="⚡", layout="wide")
st.markdown("""
<style>
#root > div:first-child { padding: 0 !important; }
.stApp > header { display: none !important; }
.stApp { margin-top: -3.75rem; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
div[data-testid="stToolbarActions"] { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }
footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

auth = AuthManager()

logger.info("app | Redis client enabled=%s", redis_client.enabled)

if "user" not in st.session_state:
    page = st.session_state.get("auth_page")
    if page == "register":
        render_register(auth)
    else:
        render_login(auth)
else:
    render_logout_button()
    render_dashboard(auth, redis_client)