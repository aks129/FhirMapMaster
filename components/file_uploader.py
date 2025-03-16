import streamlit as st
import pandas as pd
import os
from io import StringIO
from utils.data_processor import load_data

def load_sample_data(file_path):
    """
    Load sample data from a file path.
    
    Args:
        file_path: Path to the sample data file
        
    Returns:
        pandas DataFrame containing the sample data
    """
    try:
        # Open the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create a StringIO object to make it compatible with st.file_uploader return
        string_data = StringIO(content)
        string_data.name = os.path.basename(file_path)
        
        # Load the data
        df = load_data(string_data)
        return df, string_data
    except Exception as e:
        st.error(f"Error loading sample data: {str(e)}")
        return None, None

def render_file_uploader():
    """
    Render the file upload component and handle file processing.
    """
    st.header("🕸️ Step 1: Cast Your Web and Capture Data")
    
    st.markdown("""
    ### *"Your friendly neighborhood data mapper is ready to help!"*
    
    Cast your web and upload your healthcare data file to begin the Parker mapping process! 
    Just like Peter Parker can sense danger, Parker can sense your data structure and help transform it.
    
    **Parker's web can capture these formats:**
    - 🕸️ CSV (Comma-Separated Values)
    - 🕸️ Excel (XLSX, XLS)
    - 🕸️ JSON
    - 🕸️ Text files
    """)
    
    # Sample data buttons (TRY ME!)
    st.markdown("### 🚀 Quick Start with Sample Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        clinical_sample_clicked = st.button("🕸️ TRY ME: Clinical Data Sample", 
                                          help="Load a sample clinical dataset to try Parker's mapping features")
    
    with col2:
        claims_sample_clicked = st.button("🕸️ TRY ME: Claims Data Sample", 
                                        help="Load a sample claims dataset to try Parker's mapping features")
    
    if clinical_sample_clicked:
        with st.spinner("🕸️ Parker is fetching a clinical data sample..."):
            df, file_obj = load_sample_data('sample_data/sample_clinical_data.csv')
            if df is not None and not df.empty:
                st.session_state.df = df
                st.session_state.uploaded_file = file_obj
                st.session_state.fhir_standard = "US Core"  # Set default FHIR standard for clinical data
                st.success("🚀 Clinical data sample loaded! Parker suggests using US Core FHIR standard for this data.")
                st.rerun()
    
    if claims_sample_clicked:
        with st.spinner("🕸️ Parker is fetching a claims data sample..."):
            df, file_obj = load_sample_data('sample_data/sample_claims_data.csv')
            if df is not None and not df.empty:
                st.session_state.df = df
                st.session_state.uploaded_file = file_obj
                st.session_state.fhir_standard = "CARIN BB"  # Set default FHIR standard for claims data
                st.success("🚀 Claims data sample loaded! Parker suggests using CARIN BB FHIR standard for this data.")
                st.rerun()
    
    st.markdown("### 📤 Or Upload Your Own Data")
    
    # File uploader widget
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "json", "txt"],
        help="Upload your healthcare data file here."
    )
    
    # If file is uploaded, process it
    if uploaded_file is not None:
        try:
            with st.spinner("🕸️ Processing your data..."):
                # Load the data from the uploaded file
                df = load_data(uploaded_file)
                
                if df is not None and not df.empty:
                    st.success(f"🕸️ Web successfully captured: {uploaded_file.name}")
                    
                    # Display basic info about the data
                    st.subheader("🕷️ Spider-Sense Data Preview")
                    st.dataframe(df.head(5), use_container_width=True)
                    
                    st.markdown(f"**Web Size:** {len(df)} rows × {len(df.columns)} columns")
                    
                    # Store the data and file in session state
                    st.session_state.uploaded_file = uploaded_file
                    st.session_state.df = df
                    
                    # Show continue button
                    if st.button("🕸️ Activate Spider-Sense Data Profiling 🕸️"):
                        st.rerun()
                else:
                    st.error("Failed to load data from the file. Please check the file format.")
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Show sample file template if no file is uploaded
    if uploaded_file is None and not (clinical_sample_clicked or claims_sample_clicked):
        with st.expander("Need help with file format?"):
            st.markdown("""
            ### Sample Data Format
            
            Your data file should contain healthcare-related information. For best results, include:
            
            - Patient demographic information
            - Clinical observations
            - Conditions or diagnoses
            - Medication information
            - Healthcare provider details
            
            #### Example CSV format:
            ```
            patient_id,first_name,last_name,birth_date,gender,condition_code,condition_description
            12345,John,Doe,1980-05-15,M,E11.9,Type 2 diabetes without complications
            67890,Jane,Smith,1975-10-23,F,I10,Essential hypertension
            ```
            
            Or click one of the "TRY ME" buttons above to load a pre-configured sample dataset!
            """)