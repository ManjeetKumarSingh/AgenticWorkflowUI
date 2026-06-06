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
:root {
  --background-color: #ffffff;
  --border-color: #e5e7eb;
  --text-color: #111827;
}
#root > div:first-child { padding: 0 !important; }
.stApp > header { display: none !important; }
.stApp { margin-top: 0 !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
div[data-testid="stToolbarActions"] { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }
footer { display: none !important; }

/* ===== Sidebar: flex column so spacer pushes logout to bottom ===== */
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
  display: flex !important;
  flex-direction: column !important;
  height: 100vh !important;
}

/* ===== Tab bar: sticky top ===== */
div[data-testid="stTabs"] {
  position: sticky !important;
  top: 0 !important;
  z-index: 100 !important;
  background: var(--background-color, #ffffff) !important;
  padding-top: 0.5rem !important;
  padding-bottom: 0 !important;
  border-bottom: 1px solid var(--border-color, #e5e7eb) !important;
}
div[data-testid="stTabs"] button {
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
  border-bottom: 2px solid transparent !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: #6366f1 !important;
  border-bottom-color: #6366f1 !important;
}

/* ===== Messages area: fixed width/height scrollable box ===== */
.chat-marker + .element-container > div[data-testid="stVerticalBlock"] {
  max-width: 720px !important;
  margin: 0 auto !important;
  height: calc(100vh - 280px) !important;
  overflow-y: auto !important;
  border: 1px solid var(--border-color, #e5e7eb) !important;
  border-radius: 0.75rem !important;
  padding: 1rem !important;
}
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