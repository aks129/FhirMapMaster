import streamlit as st
from components.file_uploader import render_file_uploader
from components.data_profiler import render_data_profiler
from components.mapping_interface import render_mapping_interface
from components.export_interface import render_export_interface
import os

# Set page configuration
st.set_page_config(
    page_title="Parker: Healthcare Data to FHIR HL7 Mapper",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'mappings' not in st.session_state:
    st.session_state.mappings = {}
if 'fhir_standard' not in st.session_state:
    st.session_state.fhir_standard = "US Core"
if 'mapping_step' not in st.session_state:
    st.session_state.mapping_step = False
if 'export_step' not in st.session_state:
    st.session_state.export_step = False

# App title and description with Parker branding
st.title("🕸️ Parker: Your Friendly Healthcare Data Mapper 🕸️")
st.markdown("""
### *"With great healthcare data comes great interoperability responsibility!"*

**Parker** swings to the rescue, transforming your complex healthcare data into FHIR HL7 standards with superhero speed and precision! Powered by AI-assisted mapping suggestions, Parker helps you fight the chaos of non-standardized healthcare data.

Upload your data file, select the appropriate FHIR standard, and let Parker do the heavy lifting!
""")

# Sidebar navigation and settings with Parker theme
with st.sidebar:
    st.markdown("## 🕸️ Parker's Web Console 🕸️")
    
    st.markdown("### 🕷️ Choose Your Super-Standard")
    # FHIR Standard Selection
    st.session_state.fhir_standard = st.radio(
        "Select FHIR Implementation Guide:",
        ["US Core (Clinical Data)", "CARIN BB (Payor Data)"]
    )
    
    # Display current status with Spider-Man theme
    st.markdown("### 🕸️ Spider-Sense Status Tracker")
    
    file_status = "✅ Data Captured in Web" if st.session_state.uploaded_file else "❌ No Data in the Web Yet"
    st.write(file_status)
    
    profile_status = "✅ Spider-Sense Analyzed Data" if st.session_state.df is not None else "⏳ Waiting for Data to Analyze" 
    st.write(profile_status)
    
    mapping_status = "✅ Mapped with Spider Precision" if st.session_state.mapping_step else "⏳ Waiting to Spin the Mapping Web"
    st.write(mapping_status)
    
    export_status = "✅ Web Export Complete" if st.session_state.export_step else "⏳ Ready to Launch Web Export"
    st.write(export_status)
    
    st.markdown("---")
    
    # Reset button with theme
    if st.button("🕸️ Reset Parker's Web 🕸️"):
        st.session_state.uploaded_file = None
        st.session_state.df = None
        st.session_state.mappings = {}
        st.session_state.mapping_step = False
        st.session_state.export_step = False
        st.rerun()

# Main workflow
# Step 1: File Upload and Data Preview
if st.session_state.uploaded_file is None:
    render_file_uploader()
# Step 2: Data Profiling and Statistics
elif st.session_state.df is not None and not st.session_state.mapping_step:
    render_data_profiler()
# Step 3: Mapping Interface
elif st.session_state.df is not None and st.session_state.mapping_step and not st.session_state.export_step:
    render_mapping_interface()
# Step 4: Export Interface
elif st.session_state.mapping_step and st.session_state.export_step:
    render_export_interface()

# Footer with Parker branding
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>🕸️ <b>Parker: Your Friendly Healthcare Data Mapper</b> 🕸️</p>
    <p><i>"Mapping healthcare data with great power and great responsibility!"</i></p>
    <p>© 2025 Parker Industries | FHIR HL7 Mapping Tool</p>
</div>
""", unsafe_allow_html=True)
