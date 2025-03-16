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
            "components": ["name.family", "name.given", "name.prefix", "name.suffix", "name.use", "name.text"]
        }
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use", "address.type", "address.text"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.system", "telecom.value", "telecom.use", "telecom.rank"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.system", "identifier.value", "identifier.use"]
        }
    
    elif resource_name == "Practitioner":
        composite_fields["name"] = {
            "datatype": "HumanName",
            "components": ["name.family", "name.given", "name.prefix", "name.suffix", "name.use", "name.text"]
        }
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use", "address.type", "address.text"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.system", "telecom.value", "telecom.use", "telecom.rank"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.system", "identifier.value", "identifier.use"]
        }
    
    elif resource_name == "Organization":
        composite_fields["address"] = {
            "datatype": "Address",
            "components": ["address.line", "address.city", "address.state", "address.postalCode", "address.country", "address.use", "address.type", "address.text"]
        }
        composite_fields["telecom"] = {
            "datatype": "ContactPoint",
            "components": ["telecom.system", "telecom.value", "telecom.use", "telecom.rank"]
        }
        composite_fields["identifier"] = {
            "datatype": "Identifier",
            "components": ["identifier.system", "identifier.value", "identifier.use"]
        }
    
    elif resource_name == "Condition":
        composite_fields["code"] = {
            "datatype": "CodeableConcept",
            "components": ["code.coding.code", "code.coding.system", "code.coding.display", "code.text"]
        }
        composite_fields["category"] = {
            "datatype": "CodeableConcept",
            "components": ["category.coding.code", "category.coding.system", "category.coding.display", "category.text"]
        }
    
    elif resource_name == "Observation":
        composite_fields["code"] = {
            "datatype": "CodeableConcept",
            "components": ["code.coding.code", "code.coding.system", "code.coding.display", "code.text"]
        }
        composite_fields["valueCodeableConcept"] = {
            "datatype": "CodeableConcept",
            "components": ["valueCodeableConcept.coding.code", "valueCodeableConcept.coding.system", "valueCodeableConcept.coding.display", "valueCodeableConcept.text"]
        }
    
    elif resource_name == "Encounter":
        composite_fields["type"] = {
            "datatype": "CodeableConcept",
            "components": ["type.coding.code", "type.coding.system", "type.coding.display", "type.text"]
        }
        composite_fields["diagnosis.condition"] = {
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
    Render the mapping interface component that works with the resources
    selected by the resource_selector component.
    """
    # Initialize session state variables if they don't exist
    if 'finalized_mappings' not in st.session_state:
        st.session_state.finalized_mappings = {}
        
    if 'mapping_tab' not in st.session_state:
        st.session_state.mapping_tab = 0
    
    # If we don't have a DataFrame at this point, return to file upload
    if 'df' not in st.session_state:
        st.warning("Please upload a file first.")
        return
    
    if 'fhir_standard' not in st.session_state:
        st.warning("Please select a FHIR standard first.")
        return
    
    # Make sure we have resources selected
    if 'selected_resources' not in st.session_state or not st.session_state.selected_resources:
        st.warning("No resources selected. Please select resources in the previous step.")
        return
        
    # Show export interface if we're in export step
    if st.session_state.export_step:
        from components.export_interface import render_export_interface
        render_export_interface()
        return
    
    # Check if we have FHIR resources loaded
    if 'fhir_resources' not in st.session_state:
        # Get resources for the selected implementation guide
        with st.spinner("Loading FHIR resource definitions..."):
            from utils.fhir_mapper import get_fhir_resources
            st.session_state.fhir_resources = get_fhir_resources(
                st.session_state.fhir_standard, 
                st.session_state.ig_version
            )
    
    # Map Data to FHIR Resources
    st.markdown("## 🕸️ Step 3: Healthcare Data Mapping")
    st.markdown("""
    ### *"Spidey sense tingling! Time to map your data to FHIR resources!"*
    
    Parker will help you map your data columns to FHIR fields. Choose the appropriate mappings
    for each resource you've selected.
    """)
    
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
            if st.button("⬅️ Previous Resource"):
                st.session_state.mapping_tab = selected_tab - 1
                st.rerun()
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center;">
            <p>Mapping Resource {selected_tab + 1} of {len(selected_resources)}: <b>{selected_resources[selected_tab]}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        if selected_tab < len(tabs) - 1:
            if st.button("Next Resource ➡️"):
                st.session_state.mapping_tab = selected_tab + 1
                st.rerun()
    
    # Show progress and actions
    st.markdown("---")
    
    # Check for unmapped resources
    unmapped_columns = get_unmapped_columns()
    
    if unmapped_columns:
        st.info(f"You have {len(unmapped_columns)} unmapped columns. Parker can help suggest mappings for them.")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🕸️ Suggest Mappings for Unmapped Columns"):
                handle_unmapped_columns(st.session_state.df, st.session_state.fhir_standard)
                st.success("Generated mapping suggestions! Review them in the appropriate resource tabs.")
                st.rerun()
                
    # Show compliance metrics
    if st.session_state.finalized_mappings:
        st.markdown("## 🕸️ FHIR Compliance Spider-Sense")
        
        if st.button("🕸️ Check Compliance with Implementation Guide"):
            with st.spinner("Spider-sense analyzing compliance..."):
                compliance_metrics = analyze_mapping_compliance(
                    st.session_state.finalized_mappings,
                    st.session_state.fhir_resources,
                    st.session_state.fhir_standard
                )
                
                st.session_state.compliance_metrics = compliance_metrics
        
        if 'compliance_metrics' in st.session_state:
            render_compliance_metrics(st.session_state.compliance_metrics)
    
    # Export option
    st.markdown("## 🕸️ Ready to Export?")
    
    # Add validation
    if st.session_state.finalized_mappings:
        if st.button("Export & Implement Parker's Mapping Web", key="export_button"):
            st.session_state.export_step = True
            st.rerun()
    else:
        st.warning("Please map at least one field before exporting.")

def render_resource_mapping(resource_name, fhir_resources, df):
    """
    Render the mapping interface for a specific FHIR resource.
    This is a complete rewrite to fix the issues with the previous implementation.
    
    Args:
        resource_name: Name of the FHIR resource
        fhir_resources: Dict containing FHIR resource definitions
        df: pandas DataFrame containing the data
    """
    if resource_name not in fhir_resources:
        st.error(f"Resource {resource_name} not found in FHIR resources.")
        return
    
    # Get resource fields and information
    resource_fields = fhir_resources[resource_name].get('fields', {})
    
    # Initialize resource in finalized mappings if not present
    if resource_name not in st.session_state.finalized_mappings:
        st.session_state.finalized_mappings[resource_name] = {}
    
    # Get suggested mappings for this resource
    resource_suggestions = {}
    for column, suggestions in st.session_state.suggested_mappings.items():
        for suggestion in suggestions:
            if suggestion['resource'] == resource_name:
                if column not in resource_suggestions:
                    resource_suggestions[column] = []
                resource_suggestions[column].append(suggestion)
    
    # Get composite field definitions
    composite_fields = get_composite_field_definitions(resource_name)
    
    # Display resource header with Spider-Man theme
    st.markdown(f"### 🕸️ Mapping Data to {resource_name} Resource")
    
    # Tab for mapping FHIR fields
    field_df = pd.DataFrame({
        'Field': list(resource_fields.keys())
    })
    
    # Filter fields to show required first, then organized by importance
    required_fields = []
    must_support_fields = []
    other_fields = []
    
    for field_name, field_info in resource_fields.items():
        if field_info.get('required', False):
            required_fields.append(field_name)
        elif field_info.get('must_support', False):
            must_support_fields.append(field_name)
        else:
            other_fields.append(field_name)
    
    # Sort fields with required first, then must-support, then others
    sorted_fields = required_fields + must_support_fields + other_fields
    
    # Create expandable sections for different field types
    with st.expander("🚨 Required Fields", expanded=True):
        if required_fields:
            for field in required_fields:
                render_field_mapping(resource_name, field, resource_fields[field], df)
        else:
            st.info("No required fields for this resource.")
    
    with st.expander("⭐ Must-Support Fields", expanded=True):
        if must_support_fields:
            for field in must_support_fields:
                render_field_mapping(resource_name, field, resource_fields[field], df)
        else:
            st.info("No must-support fields for this resource.")
    
    with st.expander("📋 Other Fields", expanded=False):
        for field in other_fields:
            render_field_mapping(resource_name, field, resource_fields[field], df)
    
    # Special handling for composite fields like HumanName, Address, etc.
    if composite_fields:
        with st.expander("🌐 Composite Fields (HumanName, Address, etc.)", expanded=True):
            st.markdown("These special FHIR datatypes need multiple source columns to map properly.")
            
            for composite_field, field_info in composite_fields.items():
                st.markdown(f"#### {composite_field} ({field_info['datatype']})")
                
                # Initialize composite mapping if not present
                composite_key = f"{resource_name}_{composite_field}"
                if composite_key not in st.session_state:
                    st.session_state[composite_key] = {
                        "enabled": False,
                        "mappings": {}
                    }
                
                st.checkbox(
                    f"Use composite mapping for {composite_field}",
                    key=f"{composite_key}_enabled",
                    value=st.session_state[composite_key]["enabled"],
                    help=f"Enable to map multiple columns to this {field_info['datatype']} field"
                )
                
                if st.session_state[f"{composite_key}_enabled"]:
                    st.session_state[composite_key]["enabled"] = True
                    
                    for component in field_info['components']:
                        component_key = f"{composite_key}_{component}"
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown(f"**{component}**")
                        
                        with col2:
                            # Get current mapping if exists
                            current_mapping = st.session_state[composite_key]["mappings"].get(component, "")
                            
                            # Create a selectbox for column selection
                            columns = [""] + list(df.columns)
                            selected_column = st.selectbox(
                                f"Select column for {component}",
                                columns,
                                index=0 if not current_mapping else columns.index(current_mapping),
                                key=component_key
                            )
                            
                            # Update mapping
                            if selected_column:
                                st.session_state[composite_key]["mappings"][component] = selected_column
                            elif component in st.session_state[composite_key]["mappings"]:
                                del st.session_state[composite_key]["mappings"][component]
                    
                    # Handle the composite field mapping in finalized mappings
                    handle_composite_field_mapping(resource_name, st.session_state.finalized_mappings, df)
                else:
                    st.session_state[composite_key]["enabled"] = False
                    # Remove any mappings if disabled
                    for component in field_info['components']:
                        field_path = component.split('.')
                        base_field = field_path[0]
                        
                        # Remove from finalized mappings if present
                        if base_field in st.session_state.finalized_mappings[resource_name]:
                            del st.session_state.finalized_mappings[resource_name][base_field]

def render_field_mapping(resource_name, field_name, field_info, df):
    """
    Render the mapping interface for a specific field.
    
    Args:
        resource_name: Name of the FHIR resource
        field_name: Name of the field
        field_info: Dict containing field information
        df: pandas DataFrame containing the data
    """
    # Get current mapping if exists
    current_mapping = st.session_state.finalized_mappings[resource_name].get(field_name, {})
    
    # Display field with metadata indicators
    field_label = field_name
    if field_info.get('required', False):
        field_label = f"{field_label} 🚨"
    elif field_info.get('must_support', False):
        field_label = f"{field_label} ⭐"
    
    # Get field type
    field_type = field_info.get('type', 'string')
    
    # Don't show mapping UI for complex types that should be handled in composite fields
    if field_type in ['HumanName', 'Address', 'ContactPoint', 'Identifier', 'CodeableConcept'] and "." not in field_name:
        return
    
    # Create layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"**{field_label}**")
        st.caption(f"Type: {field_type}")
    
    with col2:
        # Get suggested columns for this field
        suggested_columns = []
        for column, suggestions in st.session_state.suggested_mappings.items():
            for suggestion in suggestions:
                if suggestion['resource'] == resource_name and suggestion['field'] == field_name:
                    suggested_columns.append(column)
        
        # Create a selectbox with suggestions highlighted
        columns = [""] + list(df.columns)
        selected_column = st.selectbox(
            f"Select column for {field_name}",
            columns,
            index=0 if not current_mapping.get('column') else columns.index(current_mapping.get('column')),
            key=f"{resource_name}_{field_name}_column"
        )
        
        # Show sample data for the selected column
        if selected_column:
            try:
                sample_values = df[selected_column].dropna().head(3).tolist()
                if sample_values:
                    st.caption(f"Sample values: {', '.join(str(v) for v in sample_values)}")
            except:
                pass
        
        # Add transformation options for the field
        transformation_types = ["None", "String Format", "Code Lookup", "Date Format", "Boolean Transform"]
        
        # Get current transformation type
        current_transform = current_mapping.get('transform_type', 'None')
        transform_type = st.selectbox(
            f"Transform {field_name}",
            transformation_types,
            index=transformation_types.index(current_transform) if current_transform in transformation_types else 0,
            key=f"{resource_name}_{field_name}_transform"
        )
        
        # Show transform options based on selected type
        transform_params = {}
        if transform_type == "String Format":
            transform_params['format'] = st.text_input(
                "Format string (use {value} as placeholder)",
                current_mapping.get('transform_params', {}).get('format', '{value}'),
                key=f"{resource_name}_{field_name}_format"
            )
        elif transform_type == "Code Lookup":
            transform_params['system'] = st.text_input(
                "Code system URI",
                current_mapping.get('transform_params', {}).get('system', ''),
                key=f"{resource_name}_{field_name}_system"
            )
        elif transform_type == "Date Format":
            transform_params['source_format'] = st.text_input(
                "Source date format",
                current_mapping.get('transform_params', {}).get('source_format', '%Y-%m-%d'),
                key=f"{resource_name}_{field_name}_source_format"
            )
            transform_params['target_format'] = st.text_input(
                "Target date format",
                current_mapping.get('transform_params', {}).get('target_format', '%Y-%m-%d'),
                key=f"{resource_name}_{field_name}_target_format"
            )
        elif transform_type == "Boolean Transform":
            transform_params['true_values'] = st.text_input(
                "True values (comma-separated)",
                current_mapping.get('transform_params', {}).get('true_values', 'Yes,Y,True,1'),
                key=f"{resource_name}_{field_name}_true_values"
            )
            transform_params['false_values'] = st.text_input(
                "False values (comma-separated)",
                current_mapping.get('transform_params', {}).get('false_values', 'No,N,False,0'),
                key=f"{resource_name}_{field_name}_false_values"
            )
        
        # Update mapping in session state
        if selected_column:
            st.session_state.finalized_mappings[resource_name][field_name] = {
                'column': selected_column,
                'transform_type': transform_type if transform_type != "None" else '',
                'transform_params': transform_params
            }
        elif field_name in st.session_state.finalized_mappings[resource_name]:
            # Remove mapping if column is deselected
            del st.session_state.finalized_mappings[resource_name][field_name]
    
    with col3:
        if st.button("❌", key=f"{resource_name}_{field_name}_clear"):
            if field_name in st.session_state.finalized_mappings[resource_name]:
                del st.session_state.finalized_mappings[resource_name][field_name]
                st.rerun()

def handle_composite_field_mapping(resource_name, finalized_mappings, df):
    """
    Handle composite fields like name.given/name.family for Patient and other resources.
    Maps fields to proper FHIR datatypes like HumanName, Address, ContactPoint.
    
    Args:
        resource_name: Name of the resource being mapped
        finalized_mappings: Dict of finalized mappings
        df: DataFrame containing the data
    """
    # Get composite field definitions for this resource
    composite_fields = get_composite_field_definitions(resource_name)
    
    for composite_field, field_info in composite_fields.items():
        # Get the base field name (e.g., "name" from "name.given")
        base_field = composite_field.split('.')[0]
        
        # Check if the composite mapping is enabled
        composite_key = f"{resource_name}_{composite_field}"
        if composite_key in st.session_state and st.session_state[composite_key]["enabled"]:
            # Get mappings for this composite field
            field_mappings = st.session_state[composite_key]["mappings"]
            
            if not field_mappings:
                continue
                
            # Create a single mapping entry for the base field
            datatype = field_info['datatype']
            
            # Convert the composite mappings to FHIR datatype format
            if datatype == "HumanName":
                # Extract mapped columns
                family = field_mappings.get("name.family", "")
                given = field_mappings.get("name.given", "")
                prefix = field_mappings.get("name.prefix", "")
                suffix = field_mappings.get("name.suffix", "")
                use = field_mappings.get("name.use", "")
                text = field_mappings.get("name.text", "")
                
                # Add to finalized mappings
                finalized_mappings[resource_name][base_field] = {
                    'datatype': 'HumanName',
                    'mapping': {
                        'family': {'column': family} if family else None,
                        'given': {'column': given} if given else None,
                        'prefix': {'column': prefix} if prefix else None,
                        'suffix': {'column': suffix} if suffix else None,
                        'use': {'column': use} if use else None,
                        'text': {'column': text} if text else None
                    }
                }
                
            elif datatype == "Address":
                # Extract mapped columns
                line = field_mappings.get("address.line", "")
                city = field_mappings.get("address.city", "")
                state = field_mappings.get("address.state", "")
                postalCode = field_mappings.get("address.postalCode", "")
                country = field_mappings.get("address.country", "")
                use = field_mappings.get("address.use", "")
                type_val = field_mappings.get("address.type", "")
                text = field_mappings.get("address.text", "")
                
                # Add to finalized mappings
                finalized_mappings[resource_name][base_field] = {
                    'datatype': 'Address',
                    'mapping': {
                        'line': {'column': line} if line else None,
                        'city': {'column': city} if city else None,
                        'state': {'column': state} if state else None,
                        'postalCode': {'column': postalCode} if postalCode else None,
                        'country': {'column': country} if country else None,
                        'use': {'column': use} if use else None,
                        'type': {'column': type_val} if type_val else None,
                        'text': {'column': text} if text else None
                    }
                }
                
            elif datatype == "ContactPoint":
                # Extract mapped columns
                system = field_mappings.get("telecom.system", "")
                value = field_mappings.get("telecom.value", "")
                use = field_mappings.get("telecom.use", "")
                rank = field_mappings.get("telecom.rank", "")
                
                # Add to finalized mappings
                finalized_mappings[resource_name][base_field] = {
                    'datatype': 'ContactPoint',
                    'mapping': {
                        'system': {'column': system} if system else None,
                        'value': {'column': value} if value else None,
                        'use': {'column': use} if use else None,
                        'rank': {'column': rank} if rank else None
                    }
                }
                
            elif datatype == "Identifier":
                # Extract mapped columns
                system = field_mappings.get("identifier.system", "")
                value = field_mappings.get("identifier.value", "")
                use = field_mappings.get("identifier.use", "")
                
                # Add to finalized mappings
                finalized_mappings[resource_name][base_field] = {
                    'datatype': 'Identifier',
                    'mapping': {
                        'system': {'column': system} if system else None,
                        'value': {'column': value} if value else None,
                        'use': {'column': use} if use else None
                    }
                }
                
            elif datatype == "CodeableConcept":
                # Extract mapped columns for CodeableConcept
                code = field_mappings.get(f"{composite_field}.coding.code", "")
                system = field_mappings.get(f"{composite_field}.coding.system", "")
                display = field_mappings.get(f"{composite_field}.coding.display", "")
                text = field_mappings.get(f"{composite_field}.text", "")
                
                # Add to finalized mappings
                finalized_mappings[resource_name][composite_field] = {
                    'datatype': 'CodeableConcept',
                    'mapping': {
                        'coding': {
                            'code': {'column': code} if code else None,
                            'system': {'column': system} if system else None,
                            'display': {'column': display} if display else None
                        },
                        'text': {'column': text} if text else None
                    }
                }

def get_unmapped_columns():
    """
    Get columns that have not been mapped to any FHIR field.
    
    Returns:
        list: List of unmapped column names
    """
    if 'df' not in st.session_state:
        return []
        
    all_columns = set(st.session_state.df.columns)
    mapped_columns = set()
    
    # Check direct mappings
    for resource, fields in st.session_state.finalized_mappings.items():
        for field, mapping in fields.items():
            if isinstance(mapping, dict) and 'column' in mapping:
                mapped_columns.add(mapping['column'])
            elif isinstance(mapping, dict) and 'mapping' in mapping:
                # Handle composite fields
                for component, component_mapping in mapping['mapping'].items():
                    if component_mapping and 'column' in component_mapping:
                        mapped_columns.add(component_mapping['column'])
    
    # Check composite mappings in session state
    for key in st.session_state:
        if key.startswith('Patient_') or key.startswith('Practitioner_') or key.startswith('Organization_'):
            if isinstance(st.session_state[key], dict) and 'mappings' in st.session_state[key]:
                for component, column in st.session_state[key]['mappings'].items():
                    if column:
                        mapped_columns.add(column)
    
    # Filter out empty strings
    mapped_columns = {col for col in mapped_columns if col}
    
    return list(all_columns - mapped_columns)

def handle_unmapped_columns(df, fhir_standard):
    """
    Handle unmapped columns with LLM assistance.
    
    Args:
        df: pandas DataFrame containing the data
        fhir_standard: The FHIR standard being used
    """
    # Get unmapped columns
    unmapped_columns = get_unmapped_columns()
    
    if not unmapped_columns:
        st.success("All columns are already mapped!")
        return
    
    # Check if we have an Anthropic API client
    client = initialize_anthropic_client()
    
    if not client:
        st.error("Anthropic API client could not be initialized. Please check your API key.")
        return
    
    # Get suggestions for unmapped columns
    with st.spinner("Parker is analyzing unmapped columns..."):
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
                
                # Add the suggestion
                st.session_state.finalized_mappings[resource][field] = {
                    'column': column,
                    'transform_type': '',
                    'transform_params': {}
                }
            
            # Check for composite fields
            composite_fields = get_composite_field_definitions(resource)
            for composite_field, composite_info in composite_fields.items():
                components = composite_info['components']
                
                for component in components:
                    if field == component:
                        # Set up composite mapping
                        composite_key = f"{resource}_{composite_field}"
                        
                        if composite_key not in st.session_state:
                            st.session_state[composite_key] = {
                                "enabled": True,
                                "mappings": {}
                            }
                        
                        # Enable and map
                        st.session_state[composite_key]["enabled"] = True
                        st.session_state[composite_key]["mappings"][component] = column
                        
                        # Handle the composite mapping
                        handle_composite_field_mapping(resource, st.session_state.finalized_mappings, df)
        
        st.success(f"Added {len(suggestions)} mapping suggestions from LLM analysis!")