import streamlit as st
from liquidleaders_backend import run_liquid_leaders  # import from the root backend file

st.set_page_config(page_title="Liquid Leaders")
st.title("Liquid Leaders (US Markets)")

st.write("Daily leadership scanner for US stocks.")

if st.button("Run Scanner"):
    with st.spinner("Running scan..."):
        df = run_liquid_leaders("usastocks.txt")
    if df.empty:
        st.warning("No qualifying stocks today.")
    else:
        st.success(f"Found {len(df)} leaders")
        st.dataframe(df, use_container_width=True)
