import streamlit as st
import json
import pandas as pd
from utils.export_service import export_mapping_as_file, get_download_link
from utils.fhir_mapper import generate_python_mapping_code

def render_export_interface():
    """
    Render the export interface component.
    """
    st.header("Step 4: Export Mapping")
    
    # Only continue if mappings exist in session state
    if st.session_state.finalized_mappings:
        mappings = st.session_state.finalized_mappings
        fhir_standard = st.session_state.fhir_standard
        
        st.markdown("""
        Your mapping is complete! You can now export it in the format of your choice.
        The exported files can be used to implement data pipelines that transform your
        data into FHIR resources.
        """)
        
        # Display a summary of the mapping
        st.subheader("Mapping Summary")
        
        # Count total mapped fields and resources
        total_resources = len(mappings)
        total_fields = sum(len(fields) for fields in mappings.values())
        total_columns = len(set(mapping_info['column'] for resource in mappings.values() for mapping_info in resource.values()))
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("FHIR Resources", total_resources)
        col2.metric("FHIR Fields", total_fields)
        col3.metric("Source Columns", total_columns)
        
        # Display detailed mapping table
        st.subheader("Detailed Mapping")
        
        # Create a dataframe to display the mapping details
        mapping_details = []
        for resource, fields in mappings.items():
            for field, mapping_info in fields.items():
                mapping_details.append({
                    "FHIR Resource": resource,
                    "FHIR Field": field,
                    "Source Column": mapping_info['column'],
                    "Confidence": f"{mapping_info['confidence']:.2f}"
                })
        
        if mapping_details:
            st.dataframe(pd.DataFrame(mapping_details), use_container_width=True)
        
        # Export options
        st.subheader("Export Options")
        
        export_format = st.radio(
            "Select Export Format:",
            ["Python Script", "JSON Mapping"],
            index=0,
            help="Choose the format for your exported mapping."
        )
        
        if export_format == "Python Script":
            format_key = "python"
            st.markdown("""
            **Python Script** provides a complete Python function that transforms your data into FHIR resources.
            You can integrate this script into your data pipeline or ETL process.
            """)
        else:  # JSON Mapping
            format_key = "json"
            st.markdown("""
            **JSON Mapping** provides a structured representation of your mapping that can be used by other tools
            or loaded into your own custom processing logic.
            """)
        
        # Export button
        if st.button("Generate Export"):
            with st.spinner("Generating export..."):
                # Generate the export content
                content, filename = export_mapping_as_file(format_key, mappings, fhir_standard)
                
                # Display preview of the export
                st.subheader("Export Preview")
                st.code(content, language="python" if format_key == "python" else "json")
                
                # Provide download link
                st.markdown("### Download Export")
                st.markdown(get_download_link(content, filename, f"Download {filename}"), unsafe_allow_html=True)
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go Back to Mapping"):
                st.session_state.export_step = False
                st.rerun()
        
        with col2:
            if st.button("Start New Mapping"):
                st.session_state.uploaded_file = None
                st.session_state.df = None
                st.session_state.mappings = {}
                st.session_state.mapping_step = False
                st.session_state.export_step = False
                st.session_state.pop('suggested_mappings', None)
                st.session_state.pop('finalized_mappings', None)
                st.session_state.pop('llm_suggestions', None)
                st.rerun()
    else:
        st.error("No mappings available. Please complete the mapping process first.")
        if st.button("Go Back to Mapping"):
            st.session_state.export_step = False
            st.rerun()
