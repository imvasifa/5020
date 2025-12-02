import streamlit as st
from streamlit.components.v1 import html
import sqlite3
import bcrypt

from db_setup import init_db, ensure_admin

init_db()
ensure_admin()

# ==========================================================
# INIT DATABASE
# ==========================================================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)
    conn.commit()
    conn.close()


def validate_login(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if row is None:
        return False
    return bcrypt.checkpw(password.encode(), row[0].encode())


def change_password(username, old_password, new_password):
    """Change user password after validating old password"""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "User not found"
    
    # Verify old password
    if not bcrypt.checkpw(old_password.encode(), row[0].encode()):
        conn.close()
        return False, "Old password is incorrect"
    
    # Hash and update new password
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    c.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, username))
    conn.commit()
    conn.close()
    
    return True, "Password updated successfully!"


init_db()

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Home",
    page_icon="🏠",
    layout="wide",
)


# ==========================================================
# LOAD BOOTSTRAP
# ==========================================================
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

<style>

body, .main, .block-container {
    background-color: #0E1117 !important;
    color: #FAFAFA !important;
    font-family: "Poppins", sans-serif;
}

/* Login Card */
.login-card {
    background: rgba(0,0,0,0.45);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 18px;
    padding: 35px;
    width: 420px;
    margin: auto;
    margin-top: 80px;
    box-shadow: 0 4px 22px rgba(0,0,0,0.55);
    animation: fadeSlide 0.8s ease-out;
}
@keyframes fadeSlide {
    0% { opacity:0; transform:translateY(-15px); }
    100% { opacity:1; transform:translateY(0); }
}

/* Buttons */
.btn-custom {
    background: linear-gradient(90deg, #00B4D8, #007BFF);
    color:white !important;
    padding:12px 25px;
    border-radius:50px;
    font-weight:600;
    border: none;
    cursor: pointer;
}
.btn-custom:hover {
    background: linear-gradient(90deg, #0096C7, #0056b3);
    transform:translateY(-2px);
}

</style>
""", unsafe_allow_html=True)


# ==========================================================
# SESSION INIT
# ==========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_change_pw" not in st.session_state:
    st.session_state.show_change_pw = False


# ==========================================================
# HIDE SIDEBAR BEFORE LOGIN
# ==========================================================
if not st.session_state.logged_in:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)


# ==========================================================
# LOGOUT & CHANGE PASSWORD
# ==========================================================
if st.session_state.logged_in:

    # LOGOUT BUTTON (Fixed positioning)
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🚪 Logout", key="logout-btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")

    # CHANGE PASSWORD SECTION
    with st.expander("🔐 Change Password", expanded=st.session_state.show_change_pw):
        with st.form("change_password_form"):
            old_pw = st.text_input("Old Password", type="password", key="old_pw")
            new_pw = st.text_input("New Password", type="password", key="new_pw")
            confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
            
            submitted = st.form_submit_button("Update Password", use_container_width=True)
            
            if submitted:
                if not old_pw or not new_pw or not confirm_pw:
                    st.error("❌ All fields are required")
                elif new_pw != confirm_pw:
                    st.error("❌ New passwords don't match")
                elif len(new_pw) < 6:
                    st.warning("⚠️ Password should be at least 6 characters long")
                else:
                    success, message = change_password(st.session_state.user, old_pw, new_pw)
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state.show_change_pw = False
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")


# ==========================================================
# LOGIN SCREEN
# ==========================================================
if not st.session_state.logged_in:

    st.markdown("""
        <div class="login-card text-center">
            <h2>🔐 Login</h2>
            <p style="opacity:0.7;">Secure Access to USA Stock Screener</p>
        </div>
    """, unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if validate_login(username, password):
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.stop()


# ==========================================================
# MAIN DASHBOARD CONTENT
# ==========================================================
st.markdown("""
<div class="container mt-4">
    <div class="hero-card text-center">
        <h1>🏠 USA Stock Screener Dashboard</h1>
        <p class="lead text-light">Professional stock screening, indicator analytics & visual tools.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="container text-center mt-5 mb-4">
    <hr style="border-color: rgba(255,255,255,0.15);" />
    <p>Developed by <b>Ra</b></p>
    <small>© 2025 | Built with ❤️ using Streamlit + Bootstrap</small>
</div>
""", unsafe_allow_html=True)