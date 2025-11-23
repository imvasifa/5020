import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io, base64

st.set_page_config(page_title="Scroll Test", layout="wide")

# Big figure
fig = plt.figure(figsize=(12, 3), dpi=350)
plt.plot(np.random.randn(100).cumsum())
plt.title("PNG Scroll Test - Should ALWAYS Scroll Horizontally")

# Convert to PNG
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=350, bbox_inches="tight")
buf.seek(0)
img_bytes = buf.getvalue()
img_base64 = base64.b64encode(img_bytes).decode()

# CSS + Display
st.markdown("""
<style>
.scroll-x {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    border: 2px solid #555;
    padding: 10px;
}
.scroll-x img {
    max-width: none !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f'<div class="scroll-x"><img src="data:image/png;base64,{img_base64}"></div>',
    unsafe_allow_html=True,
)
