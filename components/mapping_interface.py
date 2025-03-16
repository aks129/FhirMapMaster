import streamlit as st
import pandas as pd
from utils.fhir_datatypes import HumanName, Address, ContactPoint, Identifier, CodeableConcept
from utils.compliance_metrics import analyze_mapping_compliance, get_overall_compliance_status, render_compliance_metrics
from utils.llm_service import initialize_anthropic_client, get_multiple_mapping_suggestions
from utils.enhanced_mapper import generate_enhanced_mapping_code
from utils.export_service import export_mapping_as_file

def get_composite_field_definitions(resource_name):
    """
    Get composite field definitions for a resource.
    
    Args:
        resource_name: Name of the FHIR resource
        
    Returns:
        Dict of composite fields with their components and datatype
    """
    # Define composite fields for different resources
    composite_fields = {}
    
    if resource_name == "Patient":
        composite_fields["name"] = {
            "datatype": "HumanName",
            "components": ["name.family", "name.given", "name.prefix", "name.suffix", "name.use"]
        }
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.value", "telecom.system", "telecom.use"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.value", "identifier.system", "identifier.use"]
        }
        
    elif resource_name == "Practitioner":
        composite_fields["name"] = {
            "datatype": "HumanName",
            "components": ["name.family", "name.given", "name.prefix", "name.suffix", "name.use"]
        }
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.value", "telecom.system", "telecom.use"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.value", "identifier.system", "identifier.use"]
        }
        composite_fields["qualification.code"] = {
            "datatype": "CodeableConcept",
            "components": ["qualification.code.coding.code", "qualification.code.coding.system", "qualification.code.coding.display", "qualification.code.text"]
        }
        
    elif resource_name == "Organization":
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.value", "telecom.system", "telecom.use"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.value", "identifier.system", "identifier.use"]
        }
        composite_fields["type"] = {
            "datatype": "CodeableConcept",
            "components": ["type.coding.code", "type.coding.system", "type.coding.display", "type.text"]
        }
        
    elif resource_name == "Coverage":
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.value", "identifier.system", "identifier.use"]
        }
        composite_fields["type"] = {
            "datatype": "CodeableConcept",
            "components": ["type.coding.code", "type.coding.system", "type.coding.display", "type.text"]
        }
        
    elif resource_name == "ExplanationOfBenefit":
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.value", "identifier.system", "identifier.use"]
        }
        composite_fields["type"] = {
            "datatype": "CodeableConcept",
            "components": ["type.coding.code", "type.coding.system", "type.coding.display", "type.text"]
        }
        composite_fields["diagnosis.diagnosis"] = {
            "datatype": "CodeableConcept",
            "components": ["diagnosis.diagnosis.coding.code", "diagnosis.diagnosis.coding.system", "diagnosis.diagnosis.coding.display", "diagnosis.diagnosis.text"]
        }
        composite_fields["procedure.procedure"] = {
            "datatype": "CodeableConcept",
            "components": ["procedure.procedure.coding.code", "procedure.procedure.coding.system", "procedure.procedure.coding.display", "procedure.procedure.text"]
        }
        
    return composite_fields

def render_mapping_interface():
    """
    Render the mapping interface component.
    This is a complete rewrite to fix the issues with the previous implementation.
    """
    # Initialize session state variables if they don't exist
    if 'finalized_mappings' not in st.session_state:
        st.session_state.finalized_mappings = {}
    
    if 'mapping_step' not in st.session_state:
        st.session_state.mapping_step = 1
        
    if 'export_step' not in st.session_state:
        st.session_state.export_step = False
        
    if 'mapping_tab' not in st.session_state:
        st.session_state.mapping_tab = 0
    
    # If we don't have a DataFrame at this point, return to file upload
    if 'df' not in st.session_state:
        st.warning("Please upload a file first.")
        st.session_state.active_tab = "upload"
        st.rerun()
    
    if 'fhir_standard' not in st.session_state:
        st.warning("Please select a FHIR standard first.")
        st.session_state.mapping_step = 1
    
    # Show export interface if we're in export step
    if st.session_state.export_step:
        from components.export_interface import render_export_interface
        render_export_interface()
        return
    
    # Step 1: Select FHIR Implementation Guide and Resources
    if st.session_state.mapping_step == 1:
        st.markdown("## Step 1: Select FHIR Implementation Guide")
        
        # Select FHIR standard
        fhir_standard = st.selectbox(
            "Select FHIR Implementation Guide",
            options=["US Core", "CARIN BB"],
            index=1 if st.session_state.get('fhir_standard') == "CARIN BB" else 0,
            help="US Core is for clinical data; CARIN BB is for claims data"
        )
        
        # Store the selected standard in session state
        st.session_state.fhir_standard = fhir_standard
        
        # Select IG version
        if fhir_standard == "US Core":
            ig_version = st.selectbox(
                "Select US Core Version",
                options=["6.1.0", "5.0.1", "4.0.0"],
                index=0,
                help="Select the version of the US Core Implementation Guide"
            )
        else:  # CARIN BB
            ig_version = st.selectbox(
                "Select CARIN BlueButton Version",
                options=["2.0.0", "1.1.0", "1.0.0"],
                index=0,
                help="Select the version of the CARIN BlueButton Implementation Guide"
            )
        
        # Store the selected version in session state
        st.session_state.ig_version = ig_version
        
        # Continue button
        if st.button("Continue to Resource Selection", key="continue_to_resources"):
            # Import here to avoid circular imports
            from utils.fhir_mapper import get_fhir_resources
            
            # Load FHIR resources
            st.session_state.fhir_resources = get_fhir_resources(st.session_state.fhir_standard, st.session_state.ig_version)
            
            # Set mapping step to 2
            st.session_state.mapping_step = 2
            st.rerun()
    
    # Step 2: Select Resources to Map
    elif st.session_state.mapping_step == 2:
        st.markdown("## Step 2: Select Resources to Map")
        
        from components.resource_selector import render_resource_selector
        render_resource_selector()
    
    # Step 3: Map Fields to Resources
    elif st.session_state.mapping_step == 3:
        st.markdown("## Step 3: Map Data Fields to FHIR Resources")
        
        # Check if we have the required session state variables
        if 'df' not in st.session_state or 'fhir_resources' not in st.session_state:
            st.error("Missing required data for mapping. Please go back to Step 1.")
            return
        
        # Get selected resources from session state
        selected_resources = st.session_state.get('selected_resources', [])
        
        if not selected_resources:
            st.warning("No resources selected. Please go back to Step 2 and select at least one resource.")
            return
        
        # Generate suggested mappings if not already done
        if 'suggested_mappings' not in st.session_state:
            with st.spinner("Parker is generating initial mapping suggestions..."):
                from utils.fhir_mapper import suggest_mappings
                st.session_state.suggested_mappings = suggest_mappings(
                    st.session_state.df, 
                    st.session_state.fhir_standard,
                    st.session_state.ig_version
                )
                
                # Apply claims data mapping enhancement if using CARIN BB
                if st.session_state.fhir_standard == "CARIN BB":
                    try:
                        from utils.cpcds_mapping import enhance_mapping_suggestions
                        st.session_state.suggested_mappings = enhance_mapping_suggestions(
                            st.session_state.suggested_mappings,
                            list(st.session_state.df.columns)
                        )
                    except Exception as e:
                        st.error(f"Error enhancing mappings with claims data knowledge: {str(e)}")
        
        # Display resources in tabs
        tabs = st.tabs([f"🕸️ {resource}" for resource in selected_resources])
        
        # Process the selected tab
        selected_tab = st.session_state.mapping_tab
        
        # Check if the selected tab is valid
        if selected_tab >= len(tabs):
            selected_tab = 0
            st.session_state.mapping_tab = 0
            
        with tabs[selected_tab]:
            current_resource = selected_resources[selected_tab]
            render_resource_mapping(current_resource, st.session_state.fhir_resources, st.session_state.df)
            
        # Navigation between tabs
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if selected_tab > 0:
                if st.button("⬅️ Previous Resource", key="prev_resource"):
                    st.session_state.mapping_tab = selected_tab - 1
                    st.rerun()
                    
        with col2:
            # Add button to handle unmapped columns using LLM
            if st.button("🔄 Map Unmapped Columns with Parker", key="map_unmapped"):
                handle_unmapped_columns(st.session_state.df, st.session_state.fhir_standard)
                st.rerun()
                
        with col3:
            if selected_tab < len(tabs) - 1:
                if st.button("Next Resource ➡️", key="next_resource"):
                    st.session_state.mapping_tab = selected_tab + 1
                    st.rerun()
        
        # Divider before compliance metrics
        st.divider()
        
        # Display compliance metrics
        if 'finalized_mappings' in st.session_state and st.session_state.finalized_mappings:
            st.markdown("### 🕸️ Mapping Compliance")
            try:
                compliance_metrics = analyze_mapping_compliance(
                    st.session_state.finalized_mappings,
                    st.session_state.fhir_resources,
                    st.session_state.fhir_standard
                )
                
                # Render compliance metrics
                render_compliance_metrics(compliance_metrics)
                
                # Get overall status
                status_emoji, status_description = get_overall_compliance_status(compliance_metrics)
                
                # Display status
                st.markdown(f"### {status_emoji} Overall Compliance: {status_description}")
                
                # Proceed to export button
                if st.button("Continue to Export", key="continue_to_export"):
                    # Get list of unmapped required fields
                    required_unmapped = []
                    for resource, metrics in compliance_metrics.items():
                        for field, field_metrics in metrics.get('fields', {}).items():
                            if field_metrics.get('required', False) and not field_metrics.get('mapped', False):
                                required_unmapped.append(f"{resource}.{field}")
                    
                    if required_unmapped and status_description != "Excellent":
                        st.warning(f"There are {len(required_unmapped)} required fields not mapped. Are you sure you want to continue?")
                        st.write("Missing required fields:")
                        for field in required_unmapped[:10]:  # Show only the first 10
                            st.write(f"- {field}")
                        if len(required_unmapped) > 10:
                            st.write(f"... and {len(required_unmapped) - 10} more")
                            
                        # Confirm button
                        if st.button("Yes, Continue Anyway", key="continue_anyway"):
                            # Set export step to True to move to export page
                            st.session_state.export_step = True
                            st.rerun()
                    else:
                        # Set export step to True to move to export page
                        st.session_state.export_step = True
                        st.rerun()
                
            except Exception as e:
                st.error(f"Error calculating compliance metrics: {str(e)}")
                import traceback
                st.write(traceback.format_exc())

def render_resource_mapping(resource_name, fhir_resources, df):
    """
    Render the mapping interface for a specific FHIR resource.
    This is a complete rewrite to fix the issues with the previous implementation.
    
    Args:
        resource_name: Name of the FHIR resource
        fhir_resources: Dict containing FHIR resource definitions
        df: pandas DataFrame containing the data
    """
    # Get the resource definition
    resource_def = fhir_resources.get(resource_name, {})
    
    # Get the suggested mappings for this resource
    suggested_mappings = st.session_state.suggested_mappings.get(resource_name, {})
    
    # Get all available columns from the dataframe
    all_columns = list(df.columns)
    
    # Display resource information with Spider-Man theme
    if 'description' in resource_def:
        st.markdown(f"*{resource_def['description']}*")
    
    st.markdown("""
    Connect your data strands to these FHIR web anchors. Parker has detected the most likely connections!
    """)
    
    # Create or initialize finalized mappings for this resource if it doesn't exist
    if resource_name not in st.session_state.finalized_mappings:
        st.session_state.finalized_mappings[resource_name] = {}
    
    # For CARIN BB standard, apply claims data mapping enhancement for claims-related resources
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
    
    # Get composite field definitions
    composite_fields = get_composite_field_definitions(resource_name)
    
    # Process composite fields (name, address, etc.)
    if composite_fields:
        st.markdown("### 🕸️ Composite Fields")
        for field, field_info in composite_fields.items():
            datatype = field_info.get('datatype', '')
            components = field_info.get('components', [])
            description = resource_def.get('fields', {}).get(field, 'Complex field')
            
            # Create a container for this composite field
            with st.container():
                st.markdown(f"""
                <div style='background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0;'>
                    <h4 style='margin: 0;'>🧩 {field} ({datatype})</h4>
                    <p style='margin: 5px 0 0 0; font-size: 0.9em;'>{description}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Process each component of the composite field
                if components:
                    for component in components:
                        # Create a row for this component
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            # Display component information
                            st.markdown(f"""
                            <div style='padding-left: 20px;'>
                                <p><b>{component.split('.')[-1]}</b></p>
                                <p style='font-size: 0.8em; color: #666;'>{resource_def.get('fields', {}).get(component, '')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Get current mapping info
                            current_column = None
                            confidence = 0.0
                            
                            # Check if already mapped in finalized mappings
                            if (resource_name in st.session_state.finalized_mappings and 
                                component in st.session_state.finalized_mappings[resource_name]):
                                mapping = st.session_state.finalized_mappings[resource_name][component]
                                current_column = mapping.get('column')
                                confidence = mapping.get('confidence', 0.0)
                            # Or check suggested mappings
                            elif component in suggested_mappings:
                                mapping = suggested_mappings[component]
                                current_column = mapping.get('column')
                                confidence = mapping.get('confidence', 0.0)
                            
                            # Create column selection dropdown
                            default_index = 0
                            if current_column and current_column in all_columns:
                                default_index = all_columns.index(current_column) + 1
                            
                            # Display dropdown with all columns
                            columns_with_empty = ["-- Not Mapped --"] + all_columns
                            selected_column = st.selectbox(
                                f"Map to Column",
                                columns_with_empty,
                                index=default_index,
                                key=f"{resource_name}_{component}_col"
                            )
                            
                            # Handle selection
                            if selected_column != "-- Not Mapped --":
                                # Create mapping entry
                                if resource_name not in st.session_state.finalized_mappings:
                                    st.session_state.finalized_mappings[resource_name] = {}
                                
                                st.session_state.finalized_mappings[resource_name][component] = {
                                    'column': selected_column,
                                    'confidence': confidence if confidence > 0 else 0.7,
                                    'match_type': 'manual_component'
                                }
                                
                                # Mark that we need to update composite fields
                                if 'needs_composite_refresh' not in st.session_state:
                                    st.session_state.needs_composite_refresh = True
                            # Remove mapping if "Not Mapped" selected
                            elif (resource_name in st.session_state.finalized_mappings and 
                                  component in st.session_state.finalized_mappings[resource_name]):
                                del st.session_state.finalized_mappings[resource_name][component]
                        
                        with col3:
                            # Display confidence indicators if mapped
                            if current_column:
                                if confidence >= 0.8:
                                    st.markdown("🟢 **Strong**")
                                elif confidence >= 0.6:
                                    st.markdown("🟡 **Good**") 
                                elif confidence >= 0.4:
                                    st.markdown("🟠 **Moderate**")
                                else:
                                    st.markdown("🔴 **Weak**")
    
    # Process simple fields (non-composite)
    st.markdown("### 🕸️ Standard Fields")
    
    # Track fields we've already processed in composite sections
    processed_fields = set()
    if composite_fields:
        for field, field_info in composite_fields.items():
            processed_fields.add(field)
            for component in field_info.get('components', []):
                processed_fields.add(component)
    
    # Get regular fields (not composite or component fields)
    regular_fields = []
    for field in resource_def.get('fields', {}):
        if field not in processed_fields:
            regular_fields.append(field)
    
    # Display regular fields
    if regular_fields:
        for field in regular_fields:
            description = resource_def.get('fields', {}).get(field, '')
            
            # Create a row for this field
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                # Display field information
                st.markdown(f"**{field}**")
                st.caption(description)
            
            with col2:
                # Get current mapping info
                current_column = None
                confidence = 0.0
                
                # Check if already mapped in finalized mappings
                if (resource_name in st.session_state.finalized_mappings and 
                    field in st.session_state.finalized_mappings[resource_name]):
                    mapping = st.session_state.finalized_mappings[resource_name][field]
                    current_column = mapping.get('column')
                    confidence = mapping.get('confidence', 0.0)
                # Or check suggested mappings
                elif field in suggested_mappings:
                    mapping = suggested_mappings[field]
                    current_column = mapping.get('column')
                    confidence = mapping.get('confidence', 0.0)
                
                # Create column selection dropdown
                default_index = 0
                if current_column and current_column in all_columns:
                    default_index = all_columns.index(current_column) + 1
                
                # Check for AI suggestions from claims mapping
                ai_suggestion = None
                if (hasattr(st.session_state, 'auto_mappings') and
                    resource_name in st.session_state.auto_mappings and
                    field in st.session_state.auto_mappings[resource_name]):
                    ai_suggestion = st.session_state.auto_mappings[resource_name][field]
                    
                    # If we don't have a current mapping but have an AI suggestion,
                    # use the AI suggestion
                    if not current_column and 'column' in ai_suggestion:
                        suggested_col = ai_suggestion['column']
                        if suggested_col in all_columns:
                            default_index = all_columns.index(suggested_col) + 1
                            st.info(f"🕸️ Parker suggests: {suggested_col}")
                
                # Display dropdown with all columns
                columns_with_empty = ["-- Not Mapped --"] + all_columns
                selected_column = st.selectbox(
                    f"Map to Column",
                    columns_with_empty,
                    index=default_index,
                    key=f"{resource_name}_{field}_col"
                )
                
                # Handle selection
                if selected_column != "-- Not Mapped --":
                    # Create mapping entry
                    if resource_name not in st.session_state.finalized_mappings:
                        st.session_state.finalized_mappings[resource_name] = {}
                    
                    # Get confidence - use existing, AI suggestion, or default
                    if confidence > 0:
                        pass  # Use existing confidence
                    elif ai_suggestion and ai_suggestion.get('confidence'):
                        confidence = ai_suggestion.get('confidence')
                    else:
                        confidence = 0.7  # Default for manual mapping
                    
                    st.session_state.finalized_mappings[resource_name][field] = {
                        'column': selected_column,
                        'confidence': confidence,
                        'match_type': 'manual'
                    }
                # Remove mapping if "Not Mapped" selected
                elif (resource_name in st.session_state.finalized_mappings and 
                      field in st.session_state.finalized_mappings[resource_name]):
                    del st.session_state.finalized_mappings[resource_name][field]
            
            with col3:
                # Display confidence indicators if mapped
                if (resource_name in st.session_state.finalized_mappings and 
                    field in st.session_state.finalized_mappings[resource_name]):
                    mapping = st.session_state.finalized_mappings[resource_name][field]
                    confidence = mapping.get('confidence', 0.0)
                    
                    if confidence >= 0.8:
                        st.markdown("🟢 **Strong**")
                    elif confidence >= 0.6:
                        st.markdown("🟡 **Good**") 
                    elif confidence >= 0.4:
                        st.markdown("🟠 **Moderate**")
                    else:
                        st.markdown("🔴 **Weak**")
    else:
        st.info("No standard fields available for this resource.")
    
    # Apply composite field mapping logic to ensure proper FHIR datatype usage
    handle_composite_field_mapping(resource_name, st.session_state.finalized_mappings, df)

def handle_composite_field_mapping(resource_name, finalized_mappings, df):
    """
    Handle composite fields like name.given/name.family for Patient and other resources.
    Maps fields to proper FHIR datatypes like HumanName, Address, ContactPoint.
    
    Args:
        resource_name: Name of the resource being mapped
        finalized_mappings: Dict of finalized mappings
        df: DataFrame containing the data
    """
    if resource_name not in finalized_mappings:
        return
    
    # Get composite field definitions for this resource
    composite_fields = get_composite_field_definitions(resource_name)
    if not composite_fields:
        return
    
    # Check each composite field
    for field, field_info in composite_fields.items():
        datatype = field_info.get('datatype', '')
        components = field_info.get('components', [])
        
        # Check if we have mappings for components
        component_mappings = {}
        for component in components:
            if component in finalized_mappings[resource_name]:
                component_mappings[component] = finalized_mappings[resource_name][component]
        
        # If we have at least one component mapped, create a composite mapping
        if component_mappings:
            # Create composite field mapping entry
            finalized_mappings[resource_name][field] = {
                'columns': [mapping.get('column') for component, mapping in component_mappings.items()],
                'components': component_mappings,
                'match_type': 'fhir_datatype_composite',
                'datatype': datatype,
                'confidence': max([mapping.get('confidence', 0.5) for mapping in component_mappings.values()], default=0.5)
            }

def handle_unmapped_columns(df, fhir_standard):
    """
    Handle unmapped columns with LLM assistance.
    
    Args:
        df: pandas DataFrame containing the data
        fhir_standard: The FHIR standard being used
    """
    # Get all columns in the dataframe
    all_columns = list(df.columns)
    
    # Get all mapped columns from finalized mappings
    mapped_columns = set()
    for resource, fields in st.session_state.finalized_mappings.items():
        for field, mapping in fields.items():
            if 'column' in mapping:
                mapped_columns.add(mapping['column'])
            if 'columns' in mapping:
                mapped_columns.update(mapping['columns'])
    
    # Find unmapped columns
    unmapped_columns = [col for col in all_columns if col not in mapped_columns]
    
    if not unmapped_columns:
        st.success("All columns are already mapped!")
        return
    
    st.markdown(f"### Analyzing {len(unmapped_columns)} Unmapped Columns")
    
    # Initialize LLM client
    client = initialize_anthropic_client()
    if not client:
        st.error("Failed to initialize LLM client. Please check your API key.")
        return
    
    # Get mapping suggestions using LLM
    with st.spinner(f"🕸️ Parker is analyzing {len(unmapped_columns)} unmapped columns..."):
        try:
            suggestions = get_multiple_mapping_suggestions(
                client, 
                unmapped_columns, 
                df, 
                fhir_standard,
                st.session_state.ig_version
            )
            
            if not suggestions:
                st.warning("No suggestions could be generated for unmapped columns.")
                return
            
            # Display suggestions and add to mappings
            for column, suggestion in suggestions.items():
                if not suggestion.get('resource') or not suggestion.get('field'):
                    continue
                
                resource = suggestion['resource']
                field = suggestion['field']
                
                # Skip if resource not in our selected resources
                if resource not in st.session_state.get('selected_resources', []):
                    continue
                
                # Check if the field exists in the resource definition
                if resource in st.session_state.fhir_resources and field in st.session_state.fhir_resources[resource].get('fields', {}):
                    # Create resource mapping if it doesn't exist
                    if resource not in st.session_state.finalized_mappings:
                        st.session_state.finalized_mappings[resource] = {}
                    
                    # Add mapping with medium confidence
                    st.session_state.finalized_mappings[resource][field] = {
                        'column': column,
                        'confidence': 0.65,  # Medium confidence for LLM suggestions
                        'match_type': 'llm_suggestion'
                    }
            
            st.success(f"🕸️ Parker has added mappings for unmapped columns!")
            
        except Exception as e:
            st.error(f"Error analyzing unmapped columns: {str(e)}")
            import traceback
            st.write(traceback.format_exc())

def display_llm_suggestion(column, fhir_standard):
    """
    Display and handle LLM suggestion for an unmapped column.
    
    Args:
        column: The column name
        fhir_standard: The FHIR standard being used
    """
    st.markdown(f"### 🕸️ Analyzing Column: {column}")
    
    # Get sample values
    if 'df' in st.session_state:
        sample_values = st.session_state.df[column].dropna().head(5).tolist()
        st.write("Sample values:", sample_values)
    
    # Initialize LLM client
    client = initialize_anthropic_client()
    if not client:
        st.error("Failed to initialize LLM client. Please check your API key.")
        return
    
    # Get suggestion
    with st.spinner("Parker is analyzing this column..."):
        try:
            from utils.llm_service import analyze_unmapped_column
            suggestion = analyze_unmapped_column(
                client, 
                column, 
                sample_values, 
                fhir_standard,
                st.session_state.ig_version
            )
            
            if suggestion:
                st.markdown("### Suggestion")
                st.markdown(f"**Resource**: {suggestion['resource']}")
                st.markdown(f"**Field**: {suggestion['field']}")
                st.markdown(f"**Confidence**: {suggestion['confidence']:.2f}")
                st.markdown(f"**Explanation**: {suggestion['explanation']}")
                
                # Add button to apply suggestion
                if st.button("Apply This Suggestion"):
                    resource = suggestion['resource']
                    field = suggestion['field']
                    
                    # Create resource mapping if it doesn't exist
                    if resource not in st.session_state.finalized_mappings:
                        st.session_state.finalized_mappings[resource] = {}
                    
                    # Add mapping
                    st.session_state.finalized_mappings[resource][field] = {
                        'column': column,
                        'confidence': suggestion['confidence'],
                        'match_type': 'llm_suggestion'
                    }
                    
                    st.success(f"Applied mapping: {column} → {resource}.{field}")
                    st.rerun()
            else:
                st.warning("Could not generate a suggestion for this column.")
                
        except Exception as e:
            st.error(f"Error analyzing column: {str(e)}")