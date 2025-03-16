import streamlit as st
import json
import pandas as pd
from utils.export_service import export_mapping_as_file, get_download_link
from utils.fhir_mapper import generate_python_mapping_code
from components.fml_viewer import render_fml_viewer

def render_export_interface():
    """
    Render the export interface component.
    """
    st.header("🕸️ Step 4: Parker's Web Export")
    
    st.markdown("""
    ### *"Time to package up your web creation and send it swinging!"*
    
    Parker has completed weaving the connections between your data and FHIR standards.
    Now it's time to export your web creation so it can be used in your healthcare data pipelines!
    """)
    
    # Only continue if mappings exist in session state
    if st.session_state.finalized_mappings:
        mappings = st.session_state.finalized_mappings
        fhir_standard = st.session_state.fhir_standard
        
        st.markdown("""
        🎯 **Mission Accomplished!** Your data mapping web is complete and ready for action.
        
        Choose your preferred export format below to get your web connections in a format
        that you can integrate into your healthcare data systems.
        """)
        
        # Display a summary of the mapping with Spider-Man theme
        st.subheader("🕸️ Parker's Web Statistics")
        
        # Count total mapped fields and resources
        total_resources = len(mappings)
        total_fields = sum(len(fields) for fields in mappings.values())
        total_columns = len(set(mapping_info['column'] for resource in mappings.values() for mapping_info in resource.values()))
        
        st.markdown("""
        Parker has analyzed your web structure and provides these key metrics about your mapping:
        """)
        
        # Display metrics with Spider-Man theme
        col1, col2, col3 = st.columns(3)
        col1.metric("🏛️ FHIR Web Anchors", total_resources, help="Number of FHIR resources used in the mapping")
        col2.metric("🧵 Web Connection Points", total_fields, help="Total number of FHIR fields mapped")
        col3.metric("📊 Data Strands Connected", total_columns, help="Number of source data columns used in mapping")
        
        # Display detailed mapping table with Spider-Man theme
        st.subheader("🕸️ Complete Web Architecture")
        
        st.markdown("""
        Here's a detailed view of all the web connections Parker has created between your data and FHIR:
        """)
        
        # Create a dataframe to display the mapping details
        mapping_details = []
        for resource, fields in mappings.items():
            for field, mapping_info in fields.items():
                mapping_details.append({
                    "FHIR Resource": resource,
                    "FHIR Field": field,
                    "Source Column": mapping_info['column'],
                    "Spider-Sense Confidence": f"{mapping_info['confidence']:.2f}"
                })
        
        if mapping_details:
            st.dataframe(pd.DataFrame(mapping_details), use_container_width=True)
        
        # Export options with Spider-Man theme
        st.subheader("🕸️ Web Export Options")
        
        export_format = st.radio(
            "Choose Your Web Export Format:",
            [
                "🐍 Python Web-Shooter", 
                "📊 JSON Web Blueprint", 
                "🌐 FHIR Mapping Language (FML)"
            ],
            index=0,
            help="Choose the format for your exported mapping."
        )
        
        if "Python" in export_format:
            format_key = "python"
            st.markdown("""
            **🐍 Python Web-Shooter** provides a complete Python function that transforms your data into FHIR resources.
            Perfect for high-flying data pipelines in environments like Databricks or your ETL process.
            
            *"This Python script packs the same punch as my web-shooters!"* - Parker
            """)
        elif "JSON" in export_format:
            format_key = "json"
            st.markdown("""
            **📊 JSON Web Blueprint** provides a structured representation of your mapping that can be easily integrated
            with other tools or loaded into your own custom processing logic.
            
            *"A blueprint of my web design that any system can understand!"* - Parker
            """)
        else:  # FHIR Mapping Language
            format_key = "fml"
            st.markdown("""
            **🌐 FHIR Mapping Language (FML)** provides a standards-based mapping representation defined by HL7 FHIR.
            Includes StructureMap, Clinical Quality Language (CQL) accessors, and Liquid templates, fully compatible with FHIR mapping engines.
            
            *"For the advanced web-slingers who speak the official language of FHIR!"* - Parker
            
            [Learn more about FHIR Mapping Language](https://www.hl7.org/fhir/mapping-language.html)
            """)
            
            # Display FML viewer for detailed exploration
            if "df" in st.session_state:
                render_fml_viewer(mappings, st.session_state.df, fhir_standard)
        
        # Export button with Spider-Man theme
        if st.button("🕸️ Generate Web Export"):
            with st.spinner("🕸️ Parker is weaving your export..."):
                # Make sure we have a DataFrame for FML export
                df = None
                if format_key == "fml" and "df" in st.session_state:
                    df = st.session_state.df
                
                # Generate the export content
                content, filename = export_mapping_as_file(format_key, mappings, fhir_standard, df)
                
                # Display preview of the export with Spider-Man theme
                st.subheader("🕸️ Web Design Preview")
                st.markdown("""
                Parker has crafted your export with precision. Here's a preview of your web design:
                """)
                st.code(content, language="python" if format_key == "python" else "json")
                
                # Provide download link with Spider-Man theme
                st.markdown("### 🕸️ Launch Your Web")
                st.markdown("""
                *"Your web is ready to swing into action! Click below to download."*
                """)
                st.markdown(get_download_link(content, filename, f"🕸️ Download {filename}"), unsafe_allow_html=True)
        
        # Navigation with Spider-Man theme
        st.markdown("---")
        st.markdown("""
        ### 🕸️ Where to Swing Next?
        
        *"With great power comes great navigation options!"*
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Swing Back to Mapping"):
                st.session_state.export_step = False
                st.rerun()
        
        with col2:
            if st.button("🆕 Start a New Web"):
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
        st.error("🕸️ Web not found! Parker's Spider-Sense is telling you to complete the mapping process first.")
        if st.button("🔙 Swing Back to Mapping"):
            st.session_state.export_step = False
            st.rerun()
