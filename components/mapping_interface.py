import streamlit as st
import pandas as pd
import json
from utils.fhir_mapper import suggest_mappings, get_fhir_resources, generate_fhir_structure
from utils.llm_service import initialize_anthropic_client, get_multiple_mapping_suggestions, analyze_complex_mapping

def render_mapping_interface():
    """
    Render the mapping interface component.
    """
    st.header("Step 3: FHIR Mapping")
    
    # Only continue if data exists in session state
    if st.session_state.df is not None:
        df = st.session_state.df
        fhir_standard = st.session_state.fhir_standard
        
        # Initialize mappings if not already present
        if 'suggested_mappings' not in st.session_state:
            with st.spinner("Generating mapping suggestions..."):
                st.session_state.suggested_mappings = suggest_mappings(df, fhir_standard)
        
        # Initialize LLM client for unmapped fields
        if 'llm_client' not in st.session_state:
            st.session_state.llm_client = initialize_anthropic_client()
        
        # Get FHIR resources for the selected standard
        fhir_resources = get_fhir_resources(fhir_standard)
        
        # Display mapping information
        st.subheader(f"Mapping to {fhir_standard}")
        st.markdown("""
        Review the suggested mappings below. For each FHIR field, the system has suggested a mapping from your data columns
        with a confidence score. You can:
        
        1. Accept the suggested mappings
        2. Modify mappings by selecting different source columns
        3. Request LLM assistance for unmapped columns
        """)
        
        # Initialize the finalized mappings if it doesn't exist
        if 'finalized_mappings' not in st.session_state:
            st.session_state.finalized_mappings = {}
            for resource, fields in st.session_state.suggested_mappings.items():
                st.session_state.finalized_mappings[resource] = {}
                for field, mapping in fields.items():
                    if mapping['confidence'] >= 0.6:  # Auto-accept high confidence mappings
                        st.session_state.finalized_mappings[resource][field] = mapping
        
        # Show available resources and mappings
        tabs = []
        resource_names = list(st.session_state.suggested_mappings.keys())
        
        # Add tabs for available resources plus one for unmapped columns
        resource_tabs = st.tabs(resource_names + ["Unmapped Columns"])
        
        # Process each resource tab
        for i, resource_name in enumerate(resource_names):
            with resource_tabs[i]:
                display_resource_mapping(resource_name, fhir_resources, df)
        
        # Handle unmapped columns
        with resource_tabs[-1]:
            handle_unmapped_columns(df, fhir_standard)
        
        # Generate final mapping preview
        st.subheader("Final Mapping Preview")
        
        if st.session_state.finalized_mappings:
            # Display a summary of the finalized mappings
            mapping_summary = []
            for resource, fields in st.session_state.finalized_mappings.items():
                for field, mapping_info in fields.items():
                    mapping_summary.append({
                        "FHIR Resource": resource,
                        "FHIR Field": field,
                        "Source Column": mapping_info['column'],
                        "Confidence": f"{mapping_info['confidence']:.2f}"
                    })
            
            if mapping_summary:
                st.dataframe(pd.DataFrame(mapping_summary), use_container_width=True)
            else:
                st.info("No mappings have been finalized yet.")
        else:
            st.info("No mappings have been finalized yet.")
        
        # Option to continue to export
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Re-generate Mappings"):
                st.session_state.suggested_mappings = suggest_mappings(df, fhir_standard)
                st.rerun()
        
        with col2:
            if st.button("Continue to Export"):
                st.session_state.export_step = True
                st.rerun()
    else:
        st.error("No data available. Please upload a file first.")
        if st.button("Go Back to File Upload"):
            st.session_state.uploaded_file = None
            st.session_state.mapping_step = False
            st.rerun()

def display_resource_mapping(resource_name, fhir_resources, df):
    """
    Display and manage mapping for a specific FHIR resource.
    
    Args:
        resource_name: Name of the FHIR resource
        fhir_resources: Dict containing FHIR resource definitions
        df: pandas DataFrame containing the data
    """
    # Get the suggested mappings for this resource
    suggested_mappings = st.session_state.suggested_mappings.get(resource_name, {})
    
    # Get the resource definition
    resource_def = fhir_resources.get(resource_name, {})
    
    # Display resource information
    st.markdown(f"### {resource_name}")
    if 'description' in resource_def:
        st.markdown(f"*{resource_def['description']}*")
    
    # Get all available columns in the dataframe
    all_columns = list(df.columns)
    
    # Show mapping interface for each field
    for field, description in resource_def.get('fields', {}).items():
        # Create a container for this field mapping
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{field}**")
                st.caption(description)
            
            with col2:
                # Check if this field is in the suggested mappings
                current_mapping = None
                current_column = None
                confidence = 0.0
                
                # Check finalized mappings first
                if resource_name in st.session_state.finalized_mappings and field in st.session_state.finalized_mappings[resource_name]:
                    current_mapping = st.session_state.finalized_mappings[resource_name][field]
                    current_column = current_mapping['column']
                    confidence = current_mapping['confidence']
                # Then check suggested mappings
                elif field in suggested_mappings:
                    current_mapping = suggested_mappings[field]
                    current_column = current_mapping['column']
                    confidence = current_mapping['confidence']
                
                # Create a selectbox for choosing the column
                selected_column = st.selectbox(
                    "Map to Column",
                    ["-- Not Mapped --"] + all_columns,
                    index=0 if current_column is None else all_columns.index(current_column) + 1,
                    key=f"{resource_name}_{field}_column"
                )
                
                # Update mapping when the user makes a selection
                if selected_column != "-- Not Mapped --":
                    if resource_name not in st.session_state.finalized_mappings:
                        st.session_state.finalized_mappings[resource_name] = {}
                    
                    # If it's a new mapping (not from suggestions), use a default confidence
                    if field not in suggested_mappings or suggested_mappings[field]['column'] != selected_column:
                        confidence = 0.5
                    
                    st.session_state.finalized_mappings[resource_name][field] = {
                        'column': selected_column,
                        'confidence': confidence
                    }
                elif resource_name in st.session_state.finalized_mappings and field in st.session_state.finalized_mappings[resource_name]:
                    # Remove the mapping if "Not Mapped" is selected
                    del st.session_state.finalized_mappings[resource_name][field]
            
            with col3:
                # Display confidence score with appropriate color
                if current_mapping is not None:
                    confidence = current_mapping['confidence']
                    confidence_color = "green" if confidence >= 0.7 else "orange" if confidence >= 0.4 else "red"
                    st.markdown(f"<p style='color:{confidence_color}'>Confidence: {confidence:.2f}</p>", unsafe_allow_html=True)

def handle_unmapped_columns(df, fhir_standard):
    """
    Handle unmapped columns with LLM assistance.
    
    Args:
        df: pandas DataFrame containing the data
        fhir_standard: The FHIR standard being used
    """
    st.markdown("### Unmapped Columns")
    st.markdown("""
    The following columns from your dataset have not been mapped to any FHIR field.
    You can get LLM-assisted suggestions for these columns.
    """)
    
    # Get all mapped columns
    mapped_columns = set()
    for resource, fields in st.session_state.finalized_mappings.items():
        for field, mapping in fields.items():
            mapped_columns.add(mapping['column'])
    
    # Get unmapped columns
    unmapped_columns = [col for col in df.columns if col not in mapped_columns]
    
    if not unmapped_columns:
        st.success("All columns have been mapped!")
        return
    
    # Display unmapped columns
    st.markdown(f"**{len(unmapped_columns)} Unmapped Columns:**")
    
    # Initialize LLM suggestions if not already present
    if 'llm_suggestions' not in st.session_state:
        st.session_state.llm_suggestions = {}
    
    # Handle each unmapped column
    for column in unmapped_columns:
        with st.expander(f"{column}"):
            st.dataframe(df[column].head(5), use_container_width=True)
            
            # Check if we already have a suggestion for this column
            if column in st.session_state.llm_suggestions:
                display_llm_suggestion(column, fhir_standard)
            else:
                # Button to get LLM suggestion
                if st.button(f"Get LLM Suggestion for {column}", key=f"llm_btn_{column}"):
                    with st.spinner(f"Analyzing '{column}' with LLM..."):
                        # Get LLM suggestion for this column
                        sample_values = df[column].dropna().unique().tolist()[:10]
                        suggestion = {}
                        
                        if st.session_state.llm_client:
                            from utils.llm_service import analyze_unmapped_column
                            suggestion = analyze_unmapped_column(
                                st.session_state.llm_client,
                                column,
                                sample_values,
                                fhir_standard
                            )
                        else:
                            suggestion = {
                                "suggested_resource": None,
                                "suggested_field": None,
                                "confidence": 0,
                                "explanation": "LLM service is not available. Please check your API key configuration."
                            }
                        
                        st.session_state.llm_suggestions[column] = suggestion
                        st.rerun()

def display_llm_suggestion(column, fhir_standard):
    """
    Display and handle LLM suggestion for an unmapped column.
    
    Args:
        column: The column name
        fhir_standard: The FHIR standard being used
    """
    suggestion = st.session_state.llm_suggestions[column]
    
    # Display the suggestion
    st.markdown("**LLM Suggestion:**")
    
    if suggestion["suggested_resource"] and suggestion["suggested_field"]:
        st.markdown(f"Map to: **{suggestion['suggested_resource']}.{suggestion['suggested_field']}**")
        st.markdown(f"Confidence: {suggestion['confidence']:.2f}")
        st.markdown(f"Explanation: {suggestion['explanation']}")
        
        # Button to accept the suggestion
        if st.button(f"Accept Suggestion for {column}", key=f"accept_{column}"):
            resource = suggestion["suggested_resource"]
            field = suggestion["suggested_field"]
            
            # Initialize resource if it doesn't exist
            if resource not in st.session_state.finalized_mappings:
                st.session_state.finalized_mappings[resource] = {}
            
            # Add the mapping
            st.session_state.finalized_mappings[resource][field] = {
                'column': column,
                'confidence': suggestion['confidence']
            }
            
            st.success(f"Added mapping: {column} → {resource}.{field}")
            st.rerun()
    else:
        st.warning("No specific mapping could be suggested.")
        st.markdown(f"Explanation: {suggestion['explanation']}")
