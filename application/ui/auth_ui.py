import streamlit as st


def _auth_styles():
    return """
    <style>
    @keyframes authFadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stApp:has(.auth-card) .auth-card {
        max-width: 400px;
        margin: 5vh auto 0;
        background: rgba(255,255,255,0.98);
        backdrop-filter: blur(20px);
        border-radius: 1.5rem;
        padding: 2.5rem 2rem 2rem;
        box-shadow: 0 25px 80px rgba(0,0,0,0.3), 0 8px 32px rgba(99,102,241,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        animation: authFadeIn 0.5s ease-out;
    }
    .stApp:has(.auth-card) .auth-logo {
        width: 52px; height: 52px;
        border-radius: 14px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.5rem;
        margin: 0 auto 1rem;
        color: #fff;
        box-shadow: 0 8px 24px rgba(99,102,241,0.3);
    }
    .stApp:has(.auth-card) .auth-title {
        font-size: 1.6rem; font-weight: 800;
        text-align: center; color: #1a1a2e;
        letter-spacing: -0.5px;
        margin-bottom: 0.15rem;
    }
    .stApp:has(.auth-card) .auth-sub {
        font-size: 0.85rem; text-align: center;
        color: #94a3b8; margin-bottom: 1.75rem;
        font-weight: 400;
    }
    .stApp:has(.auth-card) .auth-divider {
        margin: 1.25rem 0 0.75rem;
        border: none; border-top: 1px solid #f1f5f9;
    }
    .stApp:has(.auth-card) .auth-footer {
        text-align: center; font-size: 0.75rem;
        color: #94a3b8; margin-top: 0.75rem;
    }
    .stApp:has(.auth-card) div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
    .stApp:has(.auth-card) div[data-testid="stForm"] .stTextInput input { border-radius: 0.75rem !important; border: 1px solid #e2e8f0 !important; padding: 0.6rem 0.9rem !important; font-size: 0.85rem !important; }
    .stApp:has(.auth-card) div[data-testid="stForm"] .stTextInput input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important; }
    .stApp:has(.auth-card) div[data-testid="stForm"] button[kind="primary"] { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; border: none !important; border-radius: 0.75rem !important; padding: 0.5rem 1rem !important; font-weight: 600 !important; font-size: 0.9rem !important; box-shadow: 0 4px 14px rgba(99,102,241,0.3) !important; transition: all 0.2s ease !important; }
    .stApp:has(.auth-card) div[data-testid="stForm"] button[kind="primary"]:hover { box-shadow: 0 6px 20px rgba(99,102,241,0.4) !important; transform: translateY(-1px) !important; }
    .stApp:has(.auth-card) .stButton button { border-radius: 0.75rem !important; font-size: 0.8rem !important; font-weight: 500 !important; }
    .stApp:has(.auth-card) .stAlert { border-radius: 0.75rem !important; font-size: 0.8rem !important; }
    .stApp:has(.auth-card) .stApp { background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%) !important; }
    @media (prefers-color-scheme: dark) {
        .stApp:has(.auth-card) .auth-card { background: rgba(30,30,35,0.98); border-color: rgba(60,60,70,0.3); }
        .stApp:has(.auth-card) .auth-title { color: #e4e4e7; }
        .stApp:has(.auth-card) div[data-testid="stForm"] .stTextInput input { background: #2a2a2e !important; border-color: #3a3a3e !important; color: #e4e4e7 !important; }
    }
    </style>
    """


def render_login(auth):
    st.markdown(_auth_styles(), unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">FlowForge</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Sign in to your workspace</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.text_input("Username", placeholder="Enter your username", key="login_user")
        st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not st.session_state.login_user or not st.session_state.login_pass:
                st.error("Please enter your username and password.")
            else:
                user = auth.login(st.session_state.login_user, st.session_state.login_pass)
                if user:
                    st.session_state.user = user
                    st.session_state.auth_page = None
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()
    with col2:
        st.markdown("<div class='auth-footer' style='padding-top:0.35rem;'>Guest access<br>not available</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_register(auth):
    st.markdown(_auth_styles(), unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Join FlowForge</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Create your workspace account</div>', unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        st.text_input("Username", placeholder="Choose a username", key="reg_user")
        st.text_input("Email", placeholder="your@email.com", key="reg_email")
        st.text_input("Password", type="password", placeholder="At least 4 characters", key="reg_pass")
        st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="reg_confirm")
        submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

        if submitted:
            if not st.session_state.reg_user or not st.session_state.reg_pass:
                st.error("Please fill in all fields.")
            elif st.session_state.reg_pass != st.session_state.reg_confirm:
                st.error("Passwords do not match.")
            else:
                err = auth.register(st.session_state.reg_user, st.session_state.reg_pass, st.session_state.reg_email)
                if err:
                    st.error(err)
                else:
                    st.success("Account created! You can now sign in.")
                    st.session_state.auth_page = None
                    st.rerun()

    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_page = None
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


APP_VERSION = "1.0.0"


def render_logout_button():
    user = st.session_state.get("user", {})
    username = user.get("username", "")
    email = user.get("email", "")
    role = user.get("role", "")
    initial = username[0].upper() if username else "?"
    badge_color = {
        "admin": "#ef4444",
        "user": "#3b82f6",
        "viewer": "#22c55e",
    }.get(role, "#999")

    st.markdown(f"""
    <style>
    .user-card {{
        background: var(--background-color);
        border: 1px solid var(--border-color, rgba(229,231,235,0.3));
        border-radius: 1rem;
        padding: 1rem 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        transition: all 0.2s ease;
    }}
    .user-card:hover {{
        border-color: rgba(99,102,241,0.2);
        box-shadow: 0 2px 12px rgba(99,102,241,0.06);
    }}
    .user-avatar {{
        width: 40px; height: 40px;
        border-radius: 10px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; font-weight: 700;
        color: #fff; flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(99,102,241,0.25);
    }}
    .user-name {{
        font-size: 0.85rem; font-weight: 600;
        color: var(--text-color);
        line-height: 1.3;
    }}
    .user-email {{
        font-size: 0.65rem; color: #94a3b8;
        line-height: 1.2;
    }}
    .user-role-badge {{
        font-size: 0.6rem; font-weight: 500;
        color: {badge_color};
        background: {badge_color}18;
        padding: 0.1rem 0.45rem;
        border-radius: 6px;
        display: inline-block;
        margin-top: 0.1rem;
    }}
    .sidebar-version {{
        font-size: 0.6rem; color: #94a3b8;
        text-align: center;
        padding: 0.5rem 0 0.25rem;
        letter-spacing: 0.3px;
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"""
        <div class="user-card">
            <div class="user-avatar">{initial}</div>
            <div>
                <div class="user-name">{username}</div>
                <div class="user-email">{email}</div>
                <span class="user-role-badge">{role}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown(f'<div style="min-height:calc(100vh - 260px);"></div>', unsafe_allow_html=True)

        st.markdown(f'<div class="sidebar-version">FlowForge v{APP_VERSION}</div>', unsafe_allow_html=True)

        if st.button("⏻  Sign Out", key="logout_btn", help="Sign out of your account", use_container_width=True):
            for key in ["user", "auth_page", "chat_history", "last_workflow", "last_workflow_id", "chat_lm_connected", "chat_lm_models", "chat_lm_model", "chat_settings_open", "_loaded_for_user", "chat_attachments"]:
                st.session_state.pop(key, None)
            st.rerun()
