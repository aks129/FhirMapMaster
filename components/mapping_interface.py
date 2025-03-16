import streamlit as st
import pandas as pd
import json
from utils.fhir_mapper import suggest_mappings, get_fhir_resources, generate_fhir_structure
from utils.llm_service import initialize_anthropic_client, get_multiple_mapping_suggestions, analyze_complex_mapping
from utils.compliance_metrics import analyze_mapping_compliance, render_compliance_metrics

def get_composite_field_definitions(resource_name):
    """
    Get composite field definitions for a resource.
    
    Args:
        resource_name: Name of the FHIR resource
        
    Returns:
        Dict of composite fields with their components and datatype
    """
    # Get composite fields definition
    composite_fields_definition = {
        "Patient": {
            "name": {
                "fhir_datatype": "HumanName",
                "components": ["name.given", "name.family", "name.prefix", "name.suffix"],
                "column_patterns": {
                    "name.given": ["first_name", "given_name", "fname", "firstname"],
                    "name.family": ["last_name", "family_name", "lname", "lastname", "surname"],
                    "name.prefix": ["prefix", "title", "name_prefix"],
                    "name.suffix": ["suffix", "name_suffix"]
                }
            },
            "address": {
                "fhir_datatype": "Address",
                "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"],
                "column_patterns": {
                    "address.line": ["address", "street", "addr", "address_line", "line1", "address_line1"],
                    "address.city": ["city", "town", "municipality"],
                    "address.state": ["state", "province", "region", "st", "stateprovince"],
                    "address.postalCode": ["zip", "zipcode", "postal_code", "postalcode", "zip_code"],
                    "address.country": ["country", "nation"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["phone", "telephone", "phone_number", "contact", "email", "email_address"],
                    "telecom.system": ["phone_type", "contact_type", "telecom_system"],
                    "telecom.use": ["phone_use", "contact_use", "telecom_use"]
                }
            }
        },
        "Practitioner": {
            "name": {
                "fhir_datatype": "HumanName",
                "components": ["name.given", "name.family", "name.prefix", "name.suffix"],
                "column_patterns": {
                    "name.given": ["provider_first_name", "provider_given_name", "dr_first_name", "physician_first"],
                    "name.family": ["provider_last_name", "provider_family_name", "dr_last_name", "physician_last"],
                    "name.prefix": ["provider_prefix", "provider_title", "dr_title"],
                    "name.suffix": ["provider_suffix", "dr_suffix"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["provider_phone", "provider_email", "dr_phone", "doctor_contact"],
                    "telecom.system": ["provider_phone_type", "provider_contact_type"],
                    "telecom.use": ["provider_phone_use", "provider_contact_use"]
                }
            }
        },
        "Organization": {
            "address": {
                "fhir_datatype": "Address",
                "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"],
                "column_patterns": {
                    "address.line": ["org_address", "facility_address", "hospital_address", "facility_street"],
                    "address.city": ["org_city", "facility_city", "hospital_city"],
                    "address.state": ["org_state", "facility_state", "hospital_state"],
                    "address.postalCode": ["org_zip", "facility_zip", "hospital_zip"],
                    "address.country": ["org_country", "facility_country", "hospital_country"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["org_phone", "facility_phone", "hospital_phone", "org_email", "facility_email"],
                    "telecom.system": ["org_phone_type", "facility_phone_type"],
                    "telecom.use": ["org_phone_use", "facility_phone_use"]
                }
            }
        },
        "Condition": {
            "code": {
                "fhir_datatype": "CodeableConcept",
                "components": ["code.coding.code", "code.coding.system", "code.coding.display", "code.text"],
                "column_patterns": {
                    "code.coding.code": ["condition_code", "dx_code", "diagnosis_code", "icd_code", "diag_code"],
                    "code.coding.system": ["code_system", "coding_system", "system"],
                    "code.coding.display": ["code_display", "diagnosis_text", "condition_text"],
                    "code.text": ["condition_description", "diagnosis_description"]
                }
            }
        }
    }
    
    # Get composites for the requested resource
    resource_composites = composite_fields_definition.get(resource_name, {})
    
    # Convert to format needed for display
    composite_fields = {}
    for composite_name, composite_info in resource_composites.items():
        components = composite_info.get("components", [])
        fhir_datatype = composite_info.get("fhir_datatype", "")
        composite_fields[composite_name] = {
            "components": components,
            "datatype": fhir_datatype
        }
    
    return composite_fields

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
        
        # First, handle and map unmapped columns to reduce the number of unmapped items    
        st.subheader("🕸️ Step 1: Parker's Automatic Web Mapping")
        
        # Display unmapped columns and auto-map with Parker AI first
        handle_unmapped_columns(df, fhir_standard)
        st.markdown("---")
            
        # Now, show resource tabs for manual refinement
        st.subheader("🕸️ Step 2: Refine Your Resource Mappings")
        st.markdown("Review and refine Parker's mapping suggestions for each selected resource.")
        
        # Add tabs for selected resources
        # Make sure resource_names is not empty to avoid Streamlit error
        if resource_names:
            resource_tabs = st.tabs(resource_names)
            
            # Process each resource tab
            for i, resource_name in enumerate(resource_names):
                with resource_tabs[i]:
                    display_resource_mapping(resource_name, fhir_resources, df)
        else:
            st.warning("No resources selected for mapping. Please select resources in Step 2.")
        
        # Generate final mapping preview with Spider-Man theme
        st.subheader("🕸️ Parker's Web of Connections - Final Preview")
        
        if st.session_state.finalized_mappings:
            # Display a summary of the finalized mappings
            mapping_summary = []
            
            # Create a set of mapped source columns for quick lookup
            mapped_columns = set()
            for resource, fields in st.session_state.finalized_mappings.items():
                for field, mapping_info in fields.items():
                    mapping_summary.append({
                        "FHIR Resource": resource,
                        "FHIR Field": field,
                        "Source Column": mapping_info['column'],
                        "Spider-Sense Confidence": f"{mapping_info['confidence']:.2f}"
                    })
                    mapped_columns.add(mapping_info['column'])
            
            # Add unmapped columns to the summary
            unmapped = []
            for col in df.columns:
                if col not in mapped_columns:
                    unmapped.append({
                        "FHIR Resource": "⚠️ Not Mapped",
                        "FHIR Field": "⚠️ Not Mapped",
                        "Source Column": col,
                        "Spider-Sense Confidence": "N/A"
                    })
            
            # Combine mapped and unmapped for complete view
            mapping_summary.extend(unmapped)
            
            if mapping_summary:
                st.markdown("### 🕸️ Your Data Web is Ready!")
                
                # Create a dataframe from the mapping summary
                mapping_df = pd.DataFrame(mapping_summary)
                
                # Add tabs to show different views
                tab1, tab2 = st.tabs(["All Source Columns", "Mapped Fields Only"])
                
                with tab1:
                    st.markdown(f"**Showing all {len(mapping_df)} source columns with their mappings**")
                    st.dataframe(mapping_df, use_container_width=True)
                    
                    # Show summary statistics
                    mapped_count = len(mapped_columns)
                    total_count = len(df.columns)
                    mapping_percentage = (mapped_count / total_count) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Columns", total_count)
                    with col2:
                        st.metric("Mapped Columns", mapped_count)
                    with col3:
                        st.metric("Mapping Coverage", f"{mapping_percentage:.1f}%")
                        
                    # Add FHIR Profile compliance metrics
                    st.markdown("### 🕸️ FHIR Profile Compliance")
                    st.markdown("""
                    Parker's Traffic Light System for FHIR Compliance:
                    - 🔴 **Red**: Missing required fields (cardinality 1..x)
                    - 🟡 **Yellow**: All required fields satisfied, some must-support fields missing
                    - 🟢 **Green**: All required and must-support fields satisfied
                    """)
                    
                    # Calculate compliance metrics but only for selected resources
                    selected_resources = st.session_state.selected_resources.keys() if hasattr(st.session_state, 'selected_resources') else []
                    
                    # Filter finalized mappings to only include selected resources
                    filtered_mappings = {resource: mappings for resource, mappings in st.session_state.finalized_mappings.items()
                                       if resource in selected_resources}
                    
                    compliance_metrics = analyze_mapping_compliance(
                        filtered_mappings,
                        fhir_resources,
                        fhir_standard
                    )
                    
                    # Render compliance metrics
                    render_compliance_metrics(compliance_metrics)
                
                with tab2:
                    # Filter to show only mapped fields
                    mapped_only = mapping_df[mapping_df["FHIR Resource"] != "⚠️ Not Mapped"]
                    st.markdown(f"**Showing {len(mapped_only)} mapped fields across {len(st.session_state.finalized_mappings)} resources**")
                    st.dataframe(mapped_only, use_container_width=True)
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
    Shows both parent fields and their component fields for complex FHIR datatypes.
    
    Args:
        resource_name: Name of the FHIR resource
        fhir_resources: Dict containing FHIR resource definitions
        df: pandas DataFrame containing the data
    """
    # Get the suggested mappings for this resource
    suggested_mappings = st.session_state.suggested_mappings.get(resource_name, {})
    
    # Get the resource definition
    resource_def = fhir_resources.get(resource_name, {})
    
    # Apply composite field mapping logic for name, address, etc.
    handle_composite_field_mapping(resource_name, st.session_state.finalized_mappings, df)
    
    # Check if we need to refresh composite fields (when component fields were mapped)
    if hasattr(st.session_state, 'needs_composite_refresh') and st.session_state.needs_composite_refresh:
        handle_composite_field_mapping(resource_name, st.session_state.finalized_mappings, df)
        st.session_state.needs_composite_refresh = False
        st.rerun()  # Force a rerun to show the updated composite fields
    
    # Display resource information with Spider-Man theme
    st.markdown(f"### 🕸️ {resource_name} Web Connection")
    if 'description' in resource_def:
        st.markdown(f"*{resource_def['description']}*")
    
    st.markdown("""
    Connect your data strands to these FHIR web anchors. Parker has detected the most likely connections!
    """)
    
    # For CARIN BB standard, apply claims data mapping AI enhancement if we're showing ExplanationOfBenefit, Patient, Coverage, etc.
    claims_related_resources = ["ExplanationOfBenefit", "Patient", "Coverage", "Practitioner", "Organization"]
    if st.session_state.fhir_standard == "CARIN BB" and resource_name in claims_related_resources:
        enhance_current_resource = st.checkbox(f"🕸️ Use Parker's AI Claims Matching for {resource_name}", 
                                             value=True, 
                                             help="Enable automatic claims data pattern matching")
        if enhance_current_resource:
            try:
                # Apply claims data matching to all dataframe columns for this resource
                with st.spinner(f"🕸️ Parker is analyzing claims data patterns for {resource_name}..."):
                    from utils.claims_mapping_data import get_claims_mapping
                    
                    # Keep track of auto-mapped fields for this resource
                    auto_mapped_count = 0
                    auto_mappings = {}
                    
                    # Look for potential mappings in the resource's fields
                    for field in resource_def.get('fields', {}).keys():
                        # Skip fields that are already mapped with high confidence
                        if field in suggested_mappings and suggested_mappings[field].get('confidence', 0) >= 0.75:
                            continue
                        
                        # Try to find columns that could map to this field
                        potential_matches = []
                        for column in df.columns:
                            mapping = get_claims_mapping(column)
                            if mapping and mapping['resource'] == resource_name and mapping['field'] == field:
                                potential_matches.append({
                                    'column': column,
                                    'confidence': mapping['confidence'],
                                    'match_type': mapping['match_type']
                                })
                        
                        # If we found potential matches, sort by confidence and add to auto-mappings
                        if potential_matches:
                            # Sort by confidence (highest first)
                            potential_matches.sort(key=lambda x: x['confidence'], reverse=True)
                            best_match = potential_matches[0]
                            
                            # Add to auto-mappings
                            auto_mappings[field] = {
                                'column': best_match['column'],
                                'confidence': best_match['confidence'],
                                'match_type': best_match['match_type'],
                                'potential_matches': potential_matches
                            }
                            auto_mapped_count += 1
                    
                    # Show summary if we found auto-mappings
                    if auto_mapped_count > 0:
                        st.success(f"🕸️ Parker found {auto_mapped_count} additional field mappings for {resource_name}!")
                        
                        # Store these in the session state for display in the field mapping UI
                        if 'auto_mappings' not in st.session_state:
                            st.session_state.auto_mappings = {}
                        st.session_state.auto_mappings[resource_name] = auto_mappings
                    
            except Exception as e:
                st.warning(f"Error applying claims mapping: {str(e)}")
    
    # Get all available columns in the dataframe
    all_columns = list(df.columns)
    
    # Get the composite field definitions for this resource
    composite_fields = get_composite_field_definitions(resource_name)
    
    # Show mapping interface for each field
    processed_fields = set()  # Track fields we've already processed
    
    # First, show parent fields with FHIR datatypes and their component fields
    for field, description in resource_def.get('fields', {}).items():
        # Skip if not a parent field of a composite field
        if field not in composite_fields:
            continue
            
        # Create a container for this parent field
        with st.container():
            st.markdown(f"""
            <div style='background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0;'>
                <h4 style='margin: 0;'>🧩 {field} ({composite_fields[field]['datatype']})</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Check if this parent field has a composite mapping
            has_composite_mapping = False
            if (resource_name in st.session_state.finalized_mappings and 
                field in st.session_state.finalized_mappings[resource_name] and
                st.session_state.finalized_mappings[resource_name][field].get('match_type') == 'fhir_datatype_composite'):
                has_composite_mapping = True
                
                parent_mapping = st.session_state.finalized_mappings[resource_name][field]
                datatype = parent_mapping.get('datatype')
                
                # Show composite field overview
                st.markdown(f"""
                <div style='padding-left: 20px;'>
                    <p>This is a <b>composite {datatype}</b> field with the following components:</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Show each component field
            for component in composite_fields[field]['components']:
                # Add to processed fields set
                processed_fields.add(component)
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Add indentation to indicate this is a component field
                        st.markdown(f"""
                        <div style='padding-left: 20px;'>
                            <p><b>{component}</b></p>
                            <p style='font-size: 0.8em; color: #666;'>{resource_def.get('fields', {}).get(component, '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Set up mapping for this component
                    with col2:
                        # Check if this field is in the suggested mappings
                        current_mapping = None
                        current_column = None
                        confidence = 0.0
                        
                        # Check finalized mappings first
                        if resource_name in st.session_state.finalized_mappings and component in st.session_state.finalized_mappings[resource_name]:
                            current_mapping = st.session_state.finalized_mappings[resource_name][component]
                            current_column = current_mapping['column']
                            confidence = current_mapping['confidence']
                        # Then check suggested mappings
                        elif component in suggested_mappings:
                            current_mapping = suggested_mappings[component]
                            current_column = current_mapping['column']
                            confidence = current_mapping['confidence']
                        
                        # Create a selectbox for choosing the column
                        # Set default index = 0 (not mapped) or find the index if the column exists
                        default_index = 0
                        if current_column is not None and current_column in all_columns:
                            default_index = all_columns.index(current_column) + 1
                        
                        # Display the select box with special formatting for component fields
                        column_options = ["-- Not Mapped --"] + all_columns
                        
                        selected_column = st.selectbox(
                            f"Map {component.split('.')[-1]} to Column",
                            column_options,
                            index=default_index,
                            key=f"{resource_name}_{component}_column"
                        )
                        
                        # Update mapping when the user makes a selection
                        if selected_column != "-- Not Mapped --":
                            if resource_name not in st.session_state.finalized_mappings:
                                st.session_state.finalized_mappings[resource_name] = {}
                            
                            # Use a high confidence for component mappings
                            confidence = 0.85
                            
                            # Add component mapping
                            st.session_state.finalized_mappings[resource_name][component] = {
                                'column': selected_column,
                                'confidence': confidence,
                                'match_type': 'composite_pattern'
                            }
                            
                            # Update parent field if we have enough components
                            # This will trigger handle_composite_field_mapping on the next rerun
                            if not has_composite_mapping:
                                st.session_state.needs_composite_refresh = True
                        elif resource_name in st.session_state.finalized_mappings and component in st.session_state.finalized_mappings[resource_name]:
                            # Remove the mapping if "Not Mapped" is selected
                            del st.session_state.finalized_mappings[resource_name][component]
                    
                    with col3:
                        # Display confidence and match type for this component
                        if current_mapping is not None:
                            confidence = current_mapping['confidence']
                            match_type = current_mapping.get('match_type', 'standard')
                            
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
                            
                            # Show confidence score
                            st.markdown(f"<p style='color:{confidence_color}'>{confidence_icon} {confidence_text}<br>Spider-Sense: {confidence:.2f}</p>", unsafe_allow_html=True)
    
    # Now show remaining regular fields
    for field, description in resource_def.get('fields', {}).items():
        # Skip fields we've already processed (composite components)
        if field in processed_fields or field in composite_fields:
            continue
            
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
                
                # Check if we have AI-suggested mappings for this field
                if (hasattr(st.session_state, 'auto_mappings') and 
                    resource_name in st.session_state.auto_mappings and 
                    field in st.session_state.auto_mappings[resource_name]):
                    
                    auto_mapping = st.session_state.auto_mappings[resource_name][field]
                    best_match_column = auto_mapping['column']
                    
                    # If we don't already have a mapping, use the AI-suggested one as default
                    if current_column is None and best_match_column in all_columns:
                        default_index = all_columns.index(best_match_column) + 1
                        
                        # Add an info message about the AI-suggested mapping
                        confidence = auto_mapping['confidence']
                        match_type = auto_mapping['match_type']
                        
                        # Choose appropriate icon based on confidence
                        if confidence >= 0.8:
                            confidence_icon = "🟢"
                        elif confidence >= 0.6:
                            confidence_icon = "🟡"
                        else:
                            confidence_icon = "🟠"
                            
                        st.info(f"{confidence_icon} Parker suggests: **{best_match_column}** (Confidence: {confidence:.2f}, Type: {match_type})")
                    
                    # Display multiple potential matches if available
                    if len(auto_mapping.get('potential_matches', [])) > 1:
                        with st.expander("See other potential matches"):
                            for match in auto_mapping['potential_matches'][1:]:  # Skip the best match
                                st.write(f"• **{match['column']}** (Confidence: {match['confidence']:.2f}, Type: {match['match_type']})")
                
                # Display the select box with special formatting for AI-suggested options
                column_options = ["-- Not Mapped --"]
                
                # Check if we have AI suggestions to highlight
                ai_suggestions = set()
                if (hasattr(st.session_state, 'auto_mappings') and 
                    resource_name in st.session_state.auto_mappings and 
                    field in st.session_state.auto_mappings[resource_name]):
                    
                    # Get all the suggested columns for this field
                    for match in st.session_state.auto_mappings[resource_name][field].get('potential_matches', []):
                        ai_suggestions.add(match['column'])
                
                # Add each column with special formatting for AI suggestions
                for column in all_columns:
                    if column in ai_suggestions:
                        column_options.append(f"🕸️ {column}")  # Add spider web icon for AI suggestions
                    else:
                        column_options.append(column)
                
                selected_column_display = st.selectbox(
                    "Map to Column",
                    column_options,
                    index=default_index,
                    key=f"{resource_name}_{field}_column"
                )
                
                # Clean up the selected column (remove the spider web icon if present)
                selected_column = selected_column_display
                if selected_column.startswith("🕸️ "):
                    selected_column = selected_column[3:]  # Remove the spider web icon and space
                
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
                    mapping_type = current_mapping.get('mapping_type', 'direct')
                    match_type = current_mapping.get('match_type', 'standard')
                    datatype = current_mapping.get('datatype', None)
                    
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
                    
                    # Show confidence score
                    st.markdown(f"<p style='color:{confidence_color}'>{confidence_icon} {confidence_text}<br>Spider-Sense: {confidence:.2f}</p>", unsafe_allow_html=True)
                    
                    # Add special badges for FHIR datatypes
                    if mapping_type == "FHIR_DATATYPE" or datatype:
                        datatype_name = datatype if datatype else mapping_type.split('_')[-1]
                        st.markdown(f"""
                        <div style='background-color: #e6f7ff; padding: 5px; border-radius: 5px; margin-top: 5px;'>
                          <span style='color: #0078d7; font-weight: bold;'>🧩 FHIR {datatype_name}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # If this is a composite field, show its parts
                        if match_type == "fhir_datatype_composite":
                            with st.expander("View Component Fields"):
                                # Display components based on datatype
                                if datatype == "HumanName":
                                    components = {
                                        "Given Name": current_mapping.get("given"),
                                        "Family Name": current_mapping.get("family"),
                                        "Prefix": current_mapping.get("prefix"),
                                        "Suffix": current_mapping.get("suffix")
                                    }
                                elif datatype == "Address":
                                    components = {
                                        "Line": current_mapping.get("line"),
                                        "City": current_mapping.get("city"),
                                        "State": current_mapping.get("state"),
                                        "Postal Code": current_mapping.get("postalCode"),
                                        "Country": current_mapping.get("country")
                                    }
                                elif datatype == "ContactPoint":
                                    components = {
                                        "Value": current_mapping.get("value"),
                                        "System": current_mapping.get("system"),
                                        "Use": current_mapping.get("use")
                                    }
                                elif datatype == "CodeableConcept":
                                    components = {
                                        "Code": current_mapping.get("code"),
                                        "System": current_mapping.get("system"),
                                        "Display": current_mapping.get("display"),
                                        "Text": current_mapping.get("text")
                                    }
                                else:
                                    components = {}
                                
                                # Display the component fields
                                for label, column in components.items():
                                    if column:
                                        st.markdown(f"**{label}**: {column}")
                                    
                    # Show match type badge
                    if match_type and match_type != "standard":
                        match_color = {
                            "composite_pattern": "#e6f7e6", 
                            "fhir_datatype_composite": "#e6f7ff",
                            "llm_suggestion": "#fff7e6",
                            "claims_pattern": "#ffebeb"
                        }.get(match_type, "#f7f7f7")
                        
                        match_text = {
                            "composite_pattern": "Pattern Match",
                            "fhir_datatype_composite": "FHIR Datatype",
                            "llm_suggestion": "AI Suggestion",
                            "claims_pattern": "Claims Pattern"
                        }.get(match_type, match_type.replace("_", " ").title())
                        
                        st.markdown(f"""
                        <div style='background-color: {match_color}; padding: 5px; border-radius: 5px; margin-top: 5px;'>
                          <span style='font-weight: bold;'>🔍 {match_text}</span>
                        </div>
                        """, unsafe_allow_html=True)


def handle_composite_field_mapping(resource_name, finalized_mappings, df):
    """
    Handle composite fields like name.given/name.family for Patient and other resources.
    Maps fields to proper FHIR datatypes like HumanName, Address, ContactPoint.
    
    Args:
        resource_name: Name of the resource being mapped
        finalized_mappings: Dict of finalized mappings
        df: DataFrame containing the data
    """
    # Get composite field definitions from our global function
    composite_fields_def = get_composite_field_definitions(resource_name)
    
    # If no composites for this resource, return
    if not composite_fields_def:
        return
    
    # Define the column patterns for component field pattern matching
    composite_fields = {
        "Patient": {
            "name": {
                "fhir_datatype": "HumanName",
                "components": ["name.given", "name.family", "name.prefix", "name.suffix"],
                "column_patterns": {
                    "name.given": ["first_name", "given_name", "fname", "firstname"],
                    "name.family": ["last_name", "family_name", "lname", "lastname", "surname"],
                    "name.prefix": ["prefix", "title", "name_prefix"],
                    "name.suffix": ["suffix", "name_suffix"]
                }
            },
            "address": {
                "fhir_datatype": "Address",
                "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"],
                "column_patterns": {
                    "address.line": ["address", "street", "addr", "address_line", "line1", "address_line1"],
                    "address.city": ["city", "town", "municipality"],
                    "address.state": ["state", "province", "region", "st", "stateprovince"],
                    "address.postalCode": ["zip", "zipcode", "postal_code", "postalcode", "zip_code"],
                    "address.country": ["country", "nation"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["phone", "telephone", "phone_number", "contact", "email", "email_address"],
                    "telecom.system": ["phone_type", "contact_type", "telecom_system"],
                    "telecom.use": ["phone_use", "contact_use", "telecom_use"]
                }
            }
        },
        "Practitioner": {
            "name": {
                "fhir_datatype": "HumanName",
                "components": ["name.given", "name.family", "name.prefix", "name.suffix"],
                "column_patterns": {
                    "name.given": ["provider_first_name", "provider_given_name", "dr_first_name", "physician_first"],
                    "name.family": ["provider_last_name", "provider_family_name", "dr_last_name", "physician_last"],
                    "name.prefix": ["provider_prefix", "provider_title", "dr_title"],
                    "name.suffix": ["provider_suffix", "dr_suffix"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["provider_phone", "provider_email", "dr_phone", "doctor_contact"],
                    "telecom.system": ["provider_phone_type", "provider_contact_type"],
                    "telecom.use": ["provider_phone_use", "provider_contact_use"]
                }
            }
        },
        "Organization": {
            "address": {
                "fhir_datatype": "Address",
                "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"],
                "column_patterns": {
                    "address.line": ["org_address", "facility_address", "hospital_address", "facility_street"],
                    "address.city": ["org_city", "facility_city", "hospital_city"],
                    "address.state": ["org_state", "facility_state", "hospital_state"],
                    "address.postalCode": ["org_zip", "facility_zip", "hospital_zip"],
                    "address.country": ["org_country", "facility_country", "hospital_country"]
                }
            },
            "telecom": {
                "fhir_datatype": "ContactPoint",
                "components": ["telecom.value", "telecom.system", "telecom.use"],
                "column_patterns": {
                    "telecom.value": ["org_phone", "facility_phone", "hospital_phone", "org_email", "facility_email"],
                    "telecom.system": ["org_phone_type", "facility_phone_type"],
                    "telecom.use": ["org_phone_use", "facility_phone_use"]
                }
            }
        },
        "Condition": {
            "code": {
                "fhir_datatype": "CodeableConcept",
                "components": ["code.coding.code", "code.coding.system", "code.coding.display", "code.text"],
                "column_patterns": {
                    "code.coding.code": ["condition_code", "dx_code", "diagnosis_code", "icd_code", "diag_code"],
                    "code.coding.system": ["code_system", "coding_system", "system"],
                    "code.coding.display": ["code_display", "diagnosis_text", "condition_text"],
                    "code.text": ["condition_description", "diagnosis_description"]
                }
            }
        }
    }
    
    # If resource isn't in our list, return 
    if resource_name not in composite_fields:
        return
    
    # Get composite fields for this resource
    resource_composites = composite_fields[resource_name]
    
    # For each composite field
    for composite_name, composite_info in resource_composites.items():
        components = composite_info["components"]
        column_patterns = composite_info["column_patterns"]
        fhir_datatype = composite_info.get("fhir_datatype")
        
        # If parent field is already mapped, skip
        if resource_name in finalized_mappings and composite_name in finalized_mappings[resource_name]:
            continue
            
        # Track component matches for this composite field
        component_matches = {}
        
        # Find matching columns for each component
        for component, patterns in column_patterns.items():
            # Skip if component is already mapped
            if resource_name in finalized_mappings and component in finalized_mappings[resource_name]:
                continue
                
            # Look for column matches
            for column in df.columns:
                col_lower = column.lower().replace("_", "").replace("-", "").replace(" ", "")
                
                # Skip columns with 'vital' or 'bp' for address fields
                if ("vital" in col_lower or "bp" in col_lower) and "address" in component.lower():
                    continue
                
                for pattern in patterns:
                    pattern_lower = pattern.lower().replace("_", "").replace("-", "").replace(" ", "")
                    
                    # If column matches pattern
                    if pattern_lower in col_lower or col_lower in pattern_lower:
                        # Add to finalized mappings
                        if resource_name not in finalized_mappings:
                            finalized_mappings[resource_name] = {}
                            
                        # Add component mapping
                        finalized_mappings[resource_name][component] = {
                            "column": column,
                            "confidence": 0.85,  # High confidence for pattern matches
                            "match_type": "composite_pattern"
                        }
                        
                        # Track this match for creating the FHIR datatype mapping
                        component_matches[component] = column
                        
                        # Once we find a match, break
                        break
        
        # If we have component matches, create a FHIR datatype mapping
        if component_matches and fhir_datatype:
            # Only create parent field if not already present
            if composite_name not in finalized_mappings.get(resource_name, {}):
                # Create appropriate mapping based on datatype
                if fhir_datatype == "HumanName":
                    given_field = component_matches.get("name.given")
                    family_field = component_matches.get("name.family")
                    prefix_field = component_matches.get("name.prefix")
                    suffix_field = component_matches.get("name.suffix")
                    
                    # Only create if we have at least one of given or family
                    if given_field or family_field:
                        finalized_mappings[resource_name][composite_name] = {
                            "mapping_type": "FHIR_DATATYPE",
                            "datatype": "HumanName",
                            "given": given_field,
                            "family": family_field,
                            "prefix": prefix_field,
                            "suffix": suffix_field,
                            "confidence": 0.9,
                            "match_type": "fhir_datatype_composite"
                        }
                
                elif fhir_datatype == "Address":
                    line_field = component_matches.get("address.line")
                    city_field = component_matches.get("address.city")
                    state_field = component_matches.get("address.state")
                    postal_code_field = component_matches.get("address.postalCode")
                    country_field = component_matches.get("address.country")
                    
                    # Only create if we have at least line or city
                    if line_field or city_field:
                        finalized_mappings[resource_name][composite_name] = {
                            "mapping_type": "FHIR_DATATYPE",
                            "datatype": "Address",
                            "line": line_field,
                            "city": city_field, 
                            "state": state_field,
                            "postalCode": postal_code_field,
                            "country": country_field,
                            "confidence": 0.9,
                            "match_type": "fhir_datatype_composite"
                        }
                
                elif fhir_datatype == "ContactPoint":
                    value_field = component_matches.get("telecom.value")
                    system_field = component_matches.get("telecom.system")
                    use_field = component_matches.get("telecom.use")
                    
                    # Only create if we have at least a value
                    if value_field:
                        finalized_mappings[resource_name][composite_name] = {
                            "mapping_type": "FHIR_DATATYPE",
                            "datatype": "ContactPoint",
                            "value": value_field,
                            "system": system_field,
                            "use": use_field,
                            "confidence": 0.9,
                            "match_type": "fhir_datatype_composite"
                        }
                
                elif fhir_datatype == "CodeableConcept":
                    code_field = component_matches.get("code.coding.code")
                    system_field = component_matches.get("code.coding.system")
                    display_field = component_matches.get("code.coding.display")
                    text_field = component_matches.get("code.text")
                    
                    # Only create if we have at least code or text
                    if code_field or text_field:
                        finalized_mappings[resource_name][composite_name] = {
                            "mapping_type": "FHIR_DATATYPE",
                            "datatype": "CodeableConcept",
                            "code": code_field,
                            "system": system_field,
                            "display": display_field,
                            "text": text_field,
                            "confidence": 0.9,
                            "match_type": "fhir_datatype_composite"
                        }
                
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
    
    # For CARIN BB, apply claims data mapping knowledge to enhance suggestions automatically
    if fhir_standard == "CARIN BB" and unmapped_columns:
        try:
            # Import the claims mapping utility
            from utils.cpcds_mapping import enhance_mapping_suggestions
            
            # Enhance existing suggestions and pre-generate for common patterns using
            # our comprehensive claims data knowledge base
            st.session_state.llm_suggestions = enhance_mapping_suggestions(
                st.session_state.llm_suggestions, 
                df.columns
            )
            
            # Check if any new suggestions were added
            new_suggestions = [col for col in df.columns 
                              if col in st.session_state.llm_suggestions 
                              and col in unmapped_columns]
            
            if new_suggestions:
                st.success(f"🕸️ Parker's Spider-Sense automatically found {len(new_suggestions)} mappings from common claims data patterns!")
                
                # Auto-apply high confidence mappings
                auto_applied_count = 0
                with st.spinner("🕸️ Parker is automatically applying high-confidence mappings..."):
                    for col in new_suggestions:
                        suggestion = st.session_state.llm_suggestions[col]
                        
                        # Only auto-apply if the confidence is high and resource exists in our finalized mappings
                        if suggestion['confidence'] >= 0.75 and suggestion['suggested_resource'] in st.session_state.selected_resources:
                            resource = suggestion['suggested_resource']
                            field = suggestion['suggested_field']
                            
                            # Ensure the resource exists in finalized mappings
                            if resource not in st.session_state.finalized_mappings:
                                st.session_state.finalized_mappings[resource] = {}
                                
                            # Add this mapping
                            st.session_state.finalized_mappings[resource][field] = {
                                'column': col,
                                'confidence': suggestion['confidence']
                            }
                            auto_applied_count += 1
                
                if auto_applied_count > 0:
                    st.success(f"🕸️ Parker automatically applied {auto_applied_count} high-confidence mappings!")
                
                # Show the auto-detected mappings in an expander
                with st.expander("View Auto-Detected Claim Field Mappings"):
                    for col in new_suggestions:
                        suggestion = st.session_state.llm_suggestions[col]
                        confidence_icon = "🟢" if suggestion['confidence'] >= 0.8 else "🟡" if suggestion['confidence'] >= 0.6 else "🟠"
                        auto_applied = ""
                        if suggestion['confidence'] >= 0.75 and suggestion['suggested_resource'] in st.session_state.selected_resources:
                            auto_applied = " (Auto-Applied)"
                        st.markdown(f"{confidence_icon} **{col}** → {suggestion['suggested_resource']}.{suggestion['suggested_field']} (Confidence: {suggestion['confidence']:.2f}){auto_applied}")
                        st.caption(suggestion['explanation'])
                        st.divider()
        except Exception as e:
            st.warning(f"Error applying claims data mappings: {str(e)}")
    
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
