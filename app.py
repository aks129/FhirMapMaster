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

**Parker** swings to the rescue, transforming your complex healthcare data into FHIR R4B standards with superhero speed and precision! Powered by AI-assisted mapping suggestions, Parker helps you fight the chaos of non-standardized healthcare data.

Upload your data file or source format (HL7 v2, C-CDA), select the appropriate FHIR Implementation Guide, and let Parker do the heavy lifting!

**Supported Source Formats:**
- 📊 **Raw Data Files** (CSV, Excel, JSON)
- 📋 **HL7 v2 Messages** (ADT, ORM, ORU and more)
- 📄 **C-CDA Documents** (Problems, Medications, Allergies and more)

**Target Format:**
- 🔬 **FHIR R4B** with support for multiple Implementation Guides:
  - US Core (versions 6.1, 7.0)
  - CARIN BB (versions 1.0, 2.0)
""")

# Sidebar navigation and settings with Parker theme
with st.sidebar:
    st.markdown("## 🕸️ Parker's Web Console 🕸️")
    
    st.markdown("### 🕷️ Configure FHIR Settings")
    
    # Add a note about FHIR R4B
    st.info("Parker maps your data to FHIR R4B standard with validation against selected Implementation Guides.")
    
    # FHIR Standard Selection with version options
    st.markdown("#### Select Implementation Guide:")
    
    ig_selection = st.radio(
        "Implementation Guide Type:",
        ["US Core (Clinical Data)", "CARIN BB (Payor Data)"]
    )
    
    # Store the implementation guide type
    if "US Core" in ig_selection:
        base_ig = "US Core"
        # Add version selection for US Core
        ig_version = st.selectbox(
            "US Core Version:",
            ["6.1.0", "7.0.0"], 
            index=0,
            help="Select the version of US Core Implementation Guide to map against"
        )
    else:
        base_ig = "CARIN BB"
        # Add version selection for CARIN BB
        ig_version = st.selectbox(
            "CARIN BB Version:",
            ["1.0.0", "2.0.0"], 
            index=0,
            help="Select the version of CARIN BB Implementation Guide to map against"
        )
    
    # Store the full IG specification in session state
    st.session_state.fhir_standard = base_ig
    st.session_state.ig_version = ig_version
    
    # Display current status with Spider-Man theme
    st.markdown("### 🕸️ Spider-Sense Status Tracker")
    
    file_status = "✅ Data Captured in Web" if st.session_state.uploaded_file else "❌ No Data in the Web Yet"
    st.write(file_status)
    
    profile_status = "✅ Spider-Sense Analyzed Data" if st.session_state.df is not None else "⏳ Waiting for Data to Analyze" 
    st.write(profile_status)
    
    resource_status = "✅ FHIR Resources Selected" if st.session_state.resource_selection_step else "⏳ Waiting to Select Resources"
    st.write(resource_status)
    
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
        st.session_state.resource_selection_step = False
        st.session_state.mapping_step = False
        st.session_state.export_step = False
        st.session_state.llm_suggestions = {}
        st.session_state.show_api_key_setup = False
        # Keep the fhir_standard and ig_version as they're configuration options
        # Also keep the llm_client intact as it's tied to the API key
        
        # Reset any resource selection
        if 'selected_resources' in st.session_state:
            st.session_state.pop('selected_resources', None)
        
        # Reset validation state
        if 'validation_results' in st.session_state:
            st.session_state.pop('validation_results', None)
            
        st.rerun()

# Import the new components
from components.resource_selector import render_resource_selector

# Add resource_selection step to session state if not present
if 'resource_selection_step' not in st.session_state:
    st.session_state.resource_selection_step = False

# Main workflow
# Step 1: File Upload and Data Preview
if st.session_state.uploaded_file is None:
    render_file_uploader()
# Step 2: Data Profiling and Statistics
elif st.session_state.df is not None and not st.session_state.resource_selection_step:
    # Move to resource selection when finished with profiling
    if render_data_profiler():
        st.session_state.resource_selection_step = True
        st.rerun()
# Step 3: Resource Selection
elif st.session_state.df is not None and st.session_state.resource_selection_step and not st.session_state.mapping_step:
    # Move to mapping when resource selection is complete
    if render_resource_selector():
        st.session_state.mapping_step = True
        st.rerun()
# Step 4: Mapping Interface
elif st.session_state.df is not None and st.session_state.mapping_step and not st.session_state.export_step:
    render_mapping_interface()
# Step 5: Export Interface
elif st.session_state.mapping_step and st.session_state.export_step:
    render_export_interface()

# Footer with Parker branding
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>🕸️ <b>Parker: Your Friendly Healthcare Data Mapper</b> 🕸️</p>
    <p><i>"Mapping healthcare data with great power and great responsibility!"</i></p>
    <p>© 2025 Parker Industries | Healthcare Data to FHIR R4B Mapping Tool</p>
    <p>Maps from HL7 v2, C-CDA, and other formats to FHIR R4B with full IG validation</p>
</div>
""", unsafe_allow_html=True)
