import streamlit as st
from components.file_uploader import render_file_uploader
from components.data_profiler import render_data_profiler
from components.mapping_interface import render_mapping_interface
from components.export_interface import render_export_interface
import os

# Set page configuration
st.set_page_config(
    page_title="Healthcare Data to FHIR HL7 Mapper",
    page_icon="🏥",
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

# App title and description
st.title("Healthcare Data to FHIR HL7 Mapper")
st.markdown("""
This tool helps you map healthcare data to FHIR HL7 format with LLM-assisted suggestions.
Upload your data file, select the appropriate FHIR standard, and follow the steps to create a mapping.
""")

# Sidebar navigation and settings
with st.sidebar:
    st.header("Navigation")
    
    # FHIR Standard Selection
    st.session_state.fhir_standard = st.radio(
        "Select FHIR Implementation Guide:",
        ["US Core (Clinical Data)", "CARIN BB (Payor Data)"]
    )
    
    # Display current status
    st.subheader("Process Status")
    
    file_status = "✅ File Uploaded" if st.session_state.uploaded_file else "❌ No File Uploaded"
    st.write(file_status)
    
    profile_status = "✅ Data Profiled" if st.session_state.df is not None else "⏳ Waiting for Data"
    st.write(profile_status)
    
    mapping_status = "✅ Mapping Created" if st.session_state.mapping_step else "⏳ Waiting for Mapping"
    st.write(mapping_status)
    
    export_status = "✅ Mapping Exported" if st.session_state.export_step else "⏳ Waiting for Export"
    st.write(export_status)
    
    # Reset button
    if st.button("Reset Process"):
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

# Footer
st.markdown("---")
st.markdown("© 2023 Healthcare Data Mapper | FHIR HL7 Mapping Tool")
