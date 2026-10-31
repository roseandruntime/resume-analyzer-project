"""
Streamlit authentication UI for Resume Analyzer.

Place this file beside app.py, auth.py and database.py.
The existing app.py can call render_auth_gate() before rendering the analyzer.
"""

import streamlit as st

from database import init_db
from auth import register_user, authenticate_user


def render_auth_gate():
    """Render login/registration UI and return the logged-in user or None."""
    init_db()

    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if st.session_state.current_user:
        user = st.session_state.current_user
        left, right = st.columns([4, 1])
        with left:
            st.caption(
                f"Signed in as **{user['full_name']}** "
                f"({user['role'].title()})"
            )
        with right:
            if st.button("Log out", key="auth_logout"):
                st.session_state.current_user = None
                st.rerun()
        return user

    st.markdown(
        """
        <div style="
            max-width:760px;margin:2rem auto 1rem auto;padding:1.5rem;
            border:1px solid rgba(167,139,250,.45);border-radius:18px;
            background:rgba(255,255,255,.05);text-align:center;">
            <h1>🔐 Resume Analyzer</h1>
            <p>Sign in or create an account to continue.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            submitted = st.form_submit_button(
                "Login", type="primary", use_container_width=True
            )

        if submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state.current_user = user
                st.rerun()
            else:
                st.error("Invalid email or password, or account is inactive.")

    with register_tab:
        st.info("Admin accounts are created separately by a trusted administrator.")
        with st.form("register_form"):
            full_name = st.text_input("Full name", key="register_name")
            new_email = st.text_input("Email address", key="register_email")
            new_password = st.text_input(
                "Password (at least 8 characters)",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="register_confirm_password",
            )
            role = st.selectbox(
                "Account type",
                ["student", "recruiter"],
                format_func=lambda value: value.title(),
            )
            register_submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )

        if register_submitted:
            if new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                success, message = register_user(
                    full_name, new_email, new_password, role
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

    return None
