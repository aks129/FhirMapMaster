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
if 'show_api_key_setup' not in st.session_state:
    st.session_state.show_api_key_setup = False
if 'llm_suggestions' not in st.session_state:
    st.session_state.llm_suggestions = {}

# App title and description with Parker branding
st.title("🕸️ Parker: Your Friendly Healthcare Data Mapper 🕸️")
st.markdown("""
### *"With great healthcare data comes great interoperability responsibility!"*

**Parker** swings to the rescue, transforming your complex healthcare data into multiple healthcare standards with superhero speed and precision! Powered by AI-assisted mapping suggestions, Parker helps you fight the chaos of non-standardized healthcare data.

Upload your data file, choose your target healthcare standard (FHIR, HL7 v2, or C-CDA), and let Parker do the heavy lifting!

**Supported Healthcare Standards:**
- 🔬 **FHIR HL7** (US Core or CARIN BB Implementation Guides)
- 📋 **HL7 v2 Messages** (ADT, ORM, ORU and more)
- 📄 **C-CDA Documents** (Problems, Medications, Allergies and more)
""")

# Sidebar navigation and settings with Parker theme
with st.sidebar:
    st.markdown("## 🕸️ Parker's Web Console 🕸️")
    
    st.markdown("### 🕷️ Choose Your Super-Standards")
    
    # Add a note about export options
    st.info("All healthcare standards (FHIR, HL7 v2, C-CDA) are available at export time - you can generate any format regardless of the starting standard.")
    
    # FHIR Standard Selection for initial mapping
    st.session_state.fhir_standard = st.radio(
        "Select FHIR Implementation Guide for Initial Mapping:",
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
        st.session_state.llm_suggestions = {}
        st.session_state.show_api_key_setup = False
        # Keep the llm_client intact as it's tied to the API key
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
    <p>© 2025 Parker Industries | Multi-Format Healthcare Mapping Tool</p>
    <p>Supports FHIR, HL7 v2, and C-CDA Formats</p>
</div>
""", unsafe_allow_html=True)
