import streamlit as st
from streamlit.components.v1 import html



# ==========================================================
# 🌐 PAGE CONFIGURATION
# ==========================================================
st.set_page_config(
    page_title="Home",
    page_icon="🏠",
    layout="wide",
)

# ==========================================================
# 🎨 LOAD BOOTSTRAP + ANIMATIONS + DARK THEME FIX
# ==========================================================
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

<style>

/* ---------------- GLOBAL ---------------- */
body, .main, .block-container {
    background-color: #0E1117 !important;
    color: #FAFAFA !important;
    font-family: "Poppins", sans-serif;
    animation: fadeBody 0.5s ease-in-out;
}
@keyframes fadeBody {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* ---------------- TITLES ---------------- */
h1, h2, h3, h4, h5 {
    color: #00B4D8 !important;
    font-weight: 700;
}

/* ---------------- HERO CARD ---------------- */
.hero-card {
    background: linear-gradient(140deg, rgba(0,180,216,0.25), rgba(0,0,0,0.3));
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 22px;
    padding: 35px;
    box-shadow: 0 4px 22px rgba(0,0,0,0.45);
    animation: fadeSlideDown 0.8s ease-out;
}
@keyframes fadeSlideDown {
    0% { opacity: 0; transform: translateY(-20px); }
    100% { opacity: 1; transform: translateY(0); }
}

/* ---------------- BUTTON ---------------- */
.btn-custom {
    background: linear-gradient(90deg, #00B4D8, #007BFF);
    color: white !important;
    padding: 10px 30px;
    border-radius: 40px;
    font-size: 18px;
    font-weight: 600;
    transition: 0.3s;
}
.btn-custom:hover {
    background: linear-gradient(90deg, #0096C7, #0056b3);
    transform: translateY(-2px);
}

/* ---------------- FOOTER ---------------- */
.footer-text {
    opacity: 0.8;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# HERO HEADER
# ==========================================================
st.markdown("""
<div class="container mt-4">
    <div class="hero-card text-center">
        <h1>🏠 USA Stock Screener Dashboard</h1>
        <p class="lead text-light">Professional stock screening, indicator analytics & visual tools.</p>
        <a class="btn btn-custom mt-3">🚀 Start Exploring</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# (NO FEATURE CARDS HERE — REMOVED)
# ==========================================================
st.markdown("""
<div class="container mt-5" style="opacity:0.5;">
    <p class="text-center">✨ Feature cards removed as requested.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# FOOTER
# ==========================================================
st.markdown("""
<div class="container text-center mt-5 mb-4">
    <hr style="border-color: rgba(255,255,255,0.15);" />
    <p class="footer-text">Developed by <b>Ra</b> — Architect & Quantitative Developer</p>
    <small class="footer-text">© 2025 | Built with ❤️ using Streamlit + Bootstrap + Animations</small>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# WELCOME TOAST
# ==========================================================
html("""
<script>
document.addEventListener("DOMContentLoaded", function() {
    let msg = document.createElement('div');
    msg.innerHTML = '<div style="
        position:fixed;
        top:20px;
        right:20px;
        padding:12px 22px;
        background:#00B4D8;
        color:white;
        border-radius:10px;
        font-weight:bold;
        box-shadow:0 2px 10px rgba(0,0,0,0.35);
        z-index:99999;
        animation:toastAnim 3s ease forwards;
    ">✨ Welcome Ra!</div>';

    document.body.appendChild(msg);
    setTimeout(() => msg.remove(), 2500);
});
</script>
<style>
@keyframes toastAnim {
    0% { opacity:0; transform: translateY(-10px); }
    10% { opacity:1; transform: translateY(0); }
    90% { opacity:1; }
    100% { opacity:0; transform: translateY(-10px); }
}
</style>
""", height=0)
