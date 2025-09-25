"""
Simple test app to verify Streamlit Cloud deployment
"""
import streamlit as st

st.set_page_config(
    page_title="FhirMapMaster Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 FhirMapMaster Deployment Test")

st.success("✅ App is running successfully!")

st.write("## System Information")
col1, col2 = st.columns(2)

with col1:
    st.metric("Streamlit Version", st.__version__)

with col2:
    import sys
    st.metric("Python Version", sys.version.split()[0])

st.write("## Import Test")

# Test basic imports
try:
    import pandas as pd
    st.success("✅ pandas imported successfully")
except ImportError as e:
    st.error(f"❌ pandas import failed: {e}")

try:
    import numpy as np
    st.success("✅ numpy imported successfully")
except ImportError as e:
    st.error(f"❌ numpy import failed: {e}")

try:
    import plotly
    st.success("✅ plotly imported successfully")
except ImportError as e:
    st.warning(f"⚠️ plotly import failed: {e}")

# Test component imports
st.write("## Component Import Test")

try:
    from components.file_uploader import render_file_uploader
    st.success("✅ file_uploader component imported")
except ImportError as e:
    st.error(f"❌ file_uploader import failed: {e}")

try:
    from components.data_profiler import render_data_profiler
    st.success("✅ data_profiler component imported")
except ImportError as e:
    st.error(f"❌ data_profiler import failed: {e}")

st.write("---")
st.info("If you can see this page, the deployment is working correctly!")

# Add a simple interactive element
if st.button("Click to test interactivity"):
    st.balloons()
    st.success("🎉 Interactivity is working!")

st.write("---")
st.write("### Debug Information")
st.write("Session ID:", st.session_state.get("session_id", "Not set"))

# Show environment info
import os
st.write("Working Directory:", os.getcwd())
st.write("Files in root:", os.listdir(".")[:10], "...")