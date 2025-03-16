import streamlit as st
import pandas as pd
from utils.data_processor import load_data

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
    
    # File uploader widget
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "json", "txt"],
        help="Upload your healthcare data file here."
    )
    
    # If file is uploaded, process it
    if uploaded_file is not None:
        try:
            with st.spinner("Processing file..."):
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
    if uploaded_file is None:
        with st.expander("Need a sample file?"):
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
            """)