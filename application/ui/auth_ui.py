import streamlit as st


def render_login(auth):
    st.markdown(
        """
    <style>
    .auth-container {
        max-width: 380px;
        margin: 8vh auto 0;
        padding: 2rem 2rem 2.5rem;
        border-radius: 1.25rem;
        border: 1px solid rgba(229,231,235,0.5);
        background: #ffffff;
        box-shadow: 0 4px 32px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03);
    }
    .auth-title {
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.25rem;
        color: #1a1a2e;
    }
    .auth-sub {
        font-size: 0.85rem;
        text-align: center;
        color: #999;
        margin-bottom: 1.5rem;
    }
    .auth-divider {
        margin: 1rem 0;
        border: none;
        border-top: 1px solid #f0f0f0;
    }
    @media (prefers-color-scheme: dark) {
        .auth-container {
            background: #1e1e20;
            border-color: rgba(60,60,65,0.5);
        }
        .auth-title { color: #e4e4e7; }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🔐 Agentic Workflows</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Sign in to your account</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Please enter your username and password.")
            else:
                user = auth.login(username, password)
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
        st.markdown(
            "<div style='text-align:center;font-size:0.75rem;color:#bbb;padding-top:0.35rem;'>Guest access<br>not available</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_register(auth):
    st.markdown(
        """
    <style>
    .auth-container {
        max-width: 380px;
        margin: 6vh auto 0;
        padding: 2rem 2rem 2.5rem;
        border-radius: 1.25rem;
        border: 1px solid rgba(229,231,235,0.5);
        background: #ffffff;
        box-shadow: 0 4px 32px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03);
    }
    .auth-title { font-size:1.5rem; font-weight:700; text-align:center; margin-bottom:0.25rem; color:#1a1a2e; }
    .auth-sub { font-size:0.85rem; text-align:center; color:#999; margin-bottom:1.5rem; }
    @media (prefers-color-scheme: dark) {
        .auth-container { background:#1e1e20; border-color:rgba(60,60,65,0.5); }
        .auth-title { color:#e4e4e7; }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">📝 Create Account</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Register to access the platform</div>', unsafe_allow_html=True)

    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Choose a username", key="reg_user")
        password = st.text_input("Password", type="password", placeholder="At least 4 characters", key="reg_pass")
        confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="reg_confirm")
        submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                err = auth.register(username, password)
                if err:
                    st.error(err)
                else:
                    st.success("Account created! You can now sign in.")
                    st.session_state.auth_page = None
                    st.rerun()

    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_page = None
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_logout_button():
    user = st.session_state.get("user", {})
    username = user.get("username", "")
    role = user.get("role", "")
    badge_color = {
        "admin": "#ef4444",
        "user": "#3b82f6",
        "viewer": "#22c55e",
    }.get(role, "#999")

    with st.sidebar:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<span style='font-size:0.85rem;font-weight:600;color:var(--text-color);'>{username}</span>"
                f"<span style='font-size:0.6rem;margin-left:0.4rem;color:{badge_color};background:{badge_color}20;padding:0.1rem 0.4rem;border-radius:6px;font-weight:500;'>{role}</span>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("🚪", key="logout_btn", help="Sign out"):
                for key in ["user", "auth_page", "chat_history", "last_workflow", "last_workflow_id", "chat_lm_connected", "chat_lm_models", "chat_lm_model", "chat_settings_open", "_loaded_for_user"]:
                    st.session_state.pop(key, None)
                st.rerun()
