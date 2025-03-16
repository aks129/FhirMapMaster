import streamlit as st
import pandas as pd
import json
from utils.fhir_mapper import suggest_mappings, get_fhir_resources, generate_fhir_structure
from utils.llm_service import initialize_anthropic_client, get_multiple_mapping_suggestions, analyze_complex_mapping

def render_mapping_interface():
    """
    Render the mapping interface component.
    """
    st.header("🕸️ Step 3: Parker's Web Mapping Adventure")
    
    st.markdown("""
    ### *"Time to connect the web strands between your data and FHIR!"*
    
    Parker has analyzed your data structure and is ready to help you map it to the FHIR standard.
    With his spider-sense, he's already detected the most likely connections!
    """)
    
    # Only continue if data exists in session state
    if st.session_state.df is not None:
        df = st.session_state.df
        fhir_standard = st.session_state.fhir_standard
        
        # Get the version of the implementation guide
        ig_version = st.session_state.ig_version
        
        # Initialize mappings if not already present
        if 'suggested_mappings' not in st.session_state:
            with st.spinner("🕸️ Parker is spinning the mapping web..."):
                st.session_state.suggested_mappings = suggest_mappings(df, fhir_standard, ig_version)
        
        # Initialize LLM client for unmapped fields
        if 'llm_client' not in st.session_state:
            st.session_state.llm_client = initialize_anthropic_client()
        
        # Get FHIR resources for the selected standard and version
        fhir_resources = get_fhir_resources(fhir_standard, ig_version)
        
        # Filter to only include selected resources
        selected_resources = st.session_state.selected_resources.keys() if hasattr(st.session_state, 'selected_resources') else []
        
        # Display mapping information with Parker theme
        st.subheader(f"🕸️ Connecting Your Data to {fhir_standard}")
        st.markdown("""
        Parker has used his spider-sense to suggest mappings between your data columns and FHIR fields.
        Each mapping comes with a confidence score to help you make decisions.
        
        **Parker's Web-Slinging Options:**
        
        1. 🕸️ **Accept the Suggested Web Connections** - Trust Parker's spider-sense
        2. 🕸️ **Modify the Web Strands** - Select different source columns
        3. 🕸️ **Request AI Spider-Sense Assistance** - Get help for unmapped columns
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
        
        # Filter the suggested mappings to only include selected resources
        if selected_resources:
            resource_names = [r for r in list(st.session_state.suggested_mappings.keys()) 
                             if r in selected_resources]
        else:
            resource_names = list(st.session_state.suggested_mappings.keys())
            
        # Add tabs for selected resources plus one for unmapped columns
        resource_tabs = st.tabs(resource_names + ["Unmapped Columns"])
        
        # Process each resource tab
        for i, resource_name in enumerate(resource_names):
            with resource_tabs[i]:
                display_resource_mapping(resource_name, fhir_resources, df)
        
        # Handle unmapped columns
        with resource_tabs[-1]:
            handle_unmapped_columns(df, fhir_standard)
        
        # Generate final mapping preview with Spider-Man theme
        st.subheader("🕸️ Parker's Web of Connections - Final Preview")
        
        if st.session_state.finalized_mappings:
            # Display a summary of the finalized mappings
            mapping_summary = []
            for resource, fields in st.session_state.finalized_mappings.items():
                for field, mapping_info in fields.items():
                    mapping_summary.append({
                        "FHIR Resource": resource,
                        "FHIR Field": field,
                        "Source Column": mapping_info['column'],
                        "Spider-Sense Confidence": f"{mapping_info['confidence']:.2f}"
                    })
            
            if mapping_summary:
                st.markdown("### 🕸️ Your Data Web is Ready!")
                st.dataframe(pd.DataFrame(mapping_summary), use_container_width=True)
            else:
                st.info("🕸️ Parker hasn't spun any web connections yet. Start mapping above!")
        else:
            st.info("🕸️ Parker hasn't spun any web connections yet. Start mapping above!")
        
        # Option to continue to export with Spider-Man theme
        st.markdown("---")
        st.markdown("""
        ### *"Your web is taking shape! Ready for the next leap?"*
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🕸️ Respin the Web"):
                st.session_state.suggested_mappings = suggest_mappings(df, fhir_standard, ig_version)
                st.rerun()
        
        with col2:
            if st.button("🕸️ Export Your Web"):
                st.session_state.export_step = True
                st.rerun()
    else:
        st.error("🕸️ Parker's web is empty! No data available for mapping. Please upload a file first.")
        if st.button("🕷️ Swing Back to Web Casting"):
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
    
    # Display resource information with Spider-Man theme
    st.markdown(f"### 🕸️ {resource_name} Web Connection")
    if 'description' in resource_def:
        st.markdown(f"*{resource_def['description']}*")
    
    st.markdown("""
    Connect your data strands to these FHIR web anchors. Parker has detected the most likely connections!
    """)
    
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
                # Set default index = 0 (not mapped) or find the index if the column exists
                default_index = 0
                if current_column is not None and current_column in all_columns:
                    default_index = all_columns.index(current_column) + 1
                elif current_column is not None:
                    # If we have a mapping but the column doesn't exist, reset to not mapped
                    st.warning(f"Column '{current_column}' not found in current dataset.")
                    current_column = None
                
                selected_column = st.selectbox(
                    "Map to Column",
                    ["-- Not Mapped --"] + all_columns,
                    index=default_index,
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
                # Display confidence score with appropriate color and Spider-Man theme
                if current_mapping is not None:
                    confidence = current_mapping['confidence']
                    if confidence >= 0.8:
                        confidence_icon = "🟢"
                        confidence_text = "Strong"
                    elif confidence >= 0.6:
                        confidence_icon = "🟡"
                        confidence_text = "Good"
                    elif confidence >= 0.4:
                        confidence_icon = "🟠"
                        confidence_text = "Moderate"
                    else:
                        confidence_icon = "🔴"
                        confidence_text = "Weak"
                    
                    confidence_color = "green" if confidence >= 0.7 else "orange" if confidence >= 0.4 else "red"
                    st.markdown(f"<p style='color:{confidence_color}'>{confidence_icon} {confidence_text}<br>Spider-Sense: {confidence:.2f}</p>", unsafe_allow_html=True)

def handle_unmapped_columns(df, fhir_standard):
    """
    Handle unmapped columns with LLM assistance.
    
    Args:
        df: pandas DataFrame containing the data
        fhir_standard: The FHIR standard being used
    """
    st.markdown("### 🕸️ Loose Strands in the Web")
    st.markdown("""
    Parker's spider-sense has detected these columns in your dataset that haven't been connected to any FHIR field yet.
    You can use Parker's enhanced AI spider-sense to suggest connections for these loose strands.
    
    *"Let's make sure no data gets left hanging in the web!"*
    """)
    
    # Get all mapped columns
    mapped_columns = set()
    for resource, fields in st.session_state.finalized_mappings.items():
        for field, mapping in fields.items():
            mapped_columns.add(mapping['column'])
    
    # Get unmapped columns
    unmapped_columns = [col for col in df.columns if col not in mapped_columns]
    
    if not unmapped_columns:
        st.success("🕸️ Amazing web-slinging work! All data strands are connected!")
        return
    
    # Display unmapped columns
    st.markdown(f"**🕸️ {len(unmapped_columns)} Loose Strands Detected:**")
    
    # Initialize LLM suggestions if not already present
    if 'llm_suggestions' not in st.session_state:
        st.session_state.llm_suggestions = {}
    
    # For CARIN BB, apply CPCDS mapping knowledge to enhance suggestions automatically
    if fhir_standard == "CARIN BB" and unmapped_columns:
        try:
            # Import the CPCDS mapping utility
            from utils.cpcds_mapping import enhance_mapping_suggestions
            
            # Enhance existing suggestions and pre-generate for common patterns
            st.session_state.llm_suggestions = enhance_mapping_suggestions(
                st.session_state.llm_suggestions, 
                df.columns
            )
            
            # Check if any new suggestions were added
            new_suggestions = [col for col in df.columns 
                              if col in st.session_state.llm_suggestions 
                              and col in unmapped_columns]
            
            if new_suggestions:
                st.success(f"🕸️ Parker's Spider-Sense automatically found {len(new_suggestions)} mappings from CPCDS patterns!")
        except Exception as e:
            print(f"Error applying CPCDS mappings: {str(e)}")
    
    # Check if LLM client is available
    if not st.session_state.llm_client:
        st.warning("🕸️ Parker's enhanced Spider-Sense (AI) requires an Anthropic API key. Without this, Parker can't provide advanced mapping suggestions.")
        st.info("💡 You can still manually map these columns by selecting them in the appropriate resource tabs above.")
        
        # Add a button to set up the API key
        if st.button("🔑 Set Up Anthropic API Key"):
            st.session_state.show_api_key_setup = True
            st.rerun()
            
        # Show API key setup if requested
        if st.session_state.get('show_api_key_setup', False):
            with st.expander("Enter Anthropic API Key", expanded=True):
                st.markdown("""
                To use Parker's enhanced Spider-Sense for automatic mapping suggestions, you need an Anthropic API key.
                
                1. Sign up at [console.anthropic.com](https://console.anthropic.com/)
                2. Create an API key in your account settings
                3. Enter it below
                """)
                
                api_key = st.text_input("Anthropic API Key", type="password")
                if st.button("Save API Key"):
                    if api_key.strip():
                        # Use environment variables in a secure way
                        import os
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                        
                        # Reinitialize the client
                        from utils.llm_service import initialize_anthropic_client
                        st.session_state.llm_client = initialize_anthropic_client()
                        
                        if st.session_state.llm_client:
                            st.success("🎉 Parker's enhanced Spider-Sense is now active!")
                            st.session_state.show_api_key_setup = False
                            st.rerun()
                        else:
                            st.error("❌ Invalid API key. Please check and try again.")
    
    # Only show column-specific suggestions if we have LLM client
    if st.session_state.llm_client:
        # Handle each unmapped column
        for column in unmapped_columns:
            with st.expander(f"🧵 {column}"):
                st.dataframe(df[column].head(5), use_container_width=True)
                
                # Check if we already have a suggestion for this column
                if column in st.session_state.llm_suggestions:
                    display_llm_suggestion(column, fhir_standard)
                else:
                    # Button to get LLM suggestion with Spider-Man theme
                    if st.button(f"🕷️ Activate Spider-Sense for {column}", key=f"llm_btn_{column}"):
                        with st.spinner(f"🕸️ Parker is analyzing '{column}' with enhanced Spider-Sense..."):
                            try:
                                # Get LLM suggestion for this column
                                sample_values = df[column].dropna().unique().tolist()[:10]
                                
                                from utils.llm_service import analyze_unmapped_column
                                # Get the version of the implementation guide
                                ig_version = st.session_state.ig_version
                                
                                suggestion = analyze_unmapped_column(
                                    st.session_state.llm_client,
                                    column,
                                    sample_values,
                                    fhir_standard,
                                    ig_version
                                )
                                
                                st.session_state.llm_suggestions[column] = suggestion
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error getting suggestion: {str(e)}")
                                st.session_state.llm_suggestions[column] = {
                                    "suggested_resource": None,
                                    "suggested_field": None,
                                    "confidence": 0,
                                    "explanation": f"Error getting LLM suggestion: {str(e)}"
                                }
    else:
        # Show basic mapping instructions without LLM
        st.markdown("""
        ### Manual Mapping Instructions
        
        Since Parker's AI Spider-Sense is not available, you'll need to manually map these columns:
        
        1. Look at the sample values to understand what kind of data each column contains
        2. Go to the resource tabs above (Patient, Observation, etc.)
        3. Select the appropriate column from the dropdown for each FHIR field
        
        **Need help identifying which resource to use?**
        - **Patient**: Use for demographics and identifiers
        - **Observation**: Use for measurements, vital signs, lab results
        - **Condition**: Use for diagnoses, problems, and health conditions
        - **Procedure**: Use for treatments or interventions performed
        - **Coverage**: Use for insurance information (CARIN BB)
        - **ExplanationOfBenefit**: Use for claims data (CARIN BB)
        """)
        
        # Show unmapped columns with sample data only
        for column in unmapped_columns:
            with st.expander(f"Sample data for: {column}"):
                st.dataframe(df[column].head(5), use_container_width=True)

def display_llm_suggestion(column, fhir_standard):
    """
    Display and handle LLM suggestion for an unmapped column.
    
    Args:
        column: The column name
        fhir_standard: The FHIR standard being used
    """
    suggestion = st.session_state.llm_suggestions[column]
    
    # Display the suggestion with Spider-Man theme
    st.markdown("**🕷️ Parker's Spider-Sense Suggestion:**")
    
    if suggestion["suggested_resource"] and suggestion["suggested_field"]:
        st.markdown(f"🕸️ Connect to: **{suggestion['suggested_resource']}.{suggestion['suggested_field']}**")
        
        # Show confidence with spider theme
        confidence = suggestion['confidence']
        if confidence >= 0.8:
            confidence_label = "🟢 Spider-Sense Tingling Strongly"
        elif confidence >= 0.6:
            confidence_label = "🟡 Spider-Sense Tingling"
        elif confidence >= 0.4:
            confidence_label = "🟠 Slight Spider-Sense Tingling"
        else:
            confidence_label = "🔴 Faint Spider-Sense"
            
        st.markdown(f"**{confidence_label}** (Score: {confidence:.2f})")
        st.markdown(f"**Web Analysis:** {suggestion['explanation']}")
        
        # Button to accept the suggestion with Spider-Man theme
        if st.button(f"🕸️ Attach Web to {column}", key=f"accept_{column}"):
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
            
            st.success(f"🕸️ Web connection successful! {column} → {resource}.{field}")
            st.rerun()
    else:
        st.warning("🕸️ Parker's Spider-Sense couldn't find a clear connection.")
        st.markdown(f"**Analysis:** {suggestion['explanation']}")
