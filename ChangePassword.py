import streamlit as st
import sqlite3
import bcrypt

# Disable access if user not logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("You must log in first.")
    st.stop()

USERNAME = st.session_state.user


# ============================================
# Database helper functions
# ============================================
def get_user_hash(username):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def update_password(username, new_hash):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, username))
    conn.commit()
    conn.close()


# ============================================
# PAGE UI
# ============================================
st.title("🔒 Change Password")
st.write("Update your login password securely.")

old_password = st.text_input("Old Password", type="password")
new_password = st.text_input("New Password", type="password")
confirm_password = st.text_input("Confirm New Password", type="password")

if st.button("Update Password", use_container_width=True):

    if not old_password or not new_password or not confirm_password:
        st.error("All fields are required.")
        st.stop()

    if new_password != confirm_password:
        st.error("New passwords do not match.")
        st.stop()

    stored_hash = get_user_hash(USERNAME)

    if not bcrypt.checkpw(old_password.encode(), stored_hash.encode()):
        st.error("Old password is incorrect.")
        st.stop()

    # Hash new password
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    update_password(USERNAME, new_hash)

    st.success("✅ Password updated successfully!")

    st.info("You can continue using the app normally. Logout not required.")


# ==========================================================
# Logout button (same as other pages)
# ==========================================================
logout_html = """
<script>
function triggerLogout(){
    const btn = window.parent.document.querySelector('button[data-testid="logout-btn"]');
    if(btn){ btn.click(); }
}
</script>

<div style='position:fixed; top:20px; right:20px; z-index:9999;'>
    <button onclick="triggerLogout()" 
        style="
            background:linear-gradient(90deg,#00B4D8,#007BFF);
            color:white; padding:10px 25px;
            border:none; border-radius:40px;
            font-weight:600; cursor:pointer;
            box-shadow:0 2px 10px rgba(0,0,0,0.4);
        ">
        🚪 Logout
    </button>
</div>
"""

st.markdown(logout_html, unsafe_allow_html=True)

if st.button("logout", key="logout-btn"):
    st.session_state.clear()
    st.rerun()
