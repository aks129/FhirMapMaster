"""
FHIR Profile Compliance Metrics Utility

This module provides functionality to assess mapping compliance with FHIR profiles
based on cardinality and must-support flags.
"""
import streamlit as st

def analyze_mapping_compliance(mappings, fhir_resources, fhir_standard):
    """
    Analyze mapping compliance with FHIR profiles based on cardinality and must-support flags.
    
    Args:
        mappings: Dict containing the finalized mappings
        fhir_resources: Dict containing FHIR resource definitions with profile information
        fhir_standard: The FHIR standard being used
    
    Returns:
        dict: Dictionary containing compliance metrics for each resource
    """
    compliance_metrics = {}
    
    for resource_name, resource_mappings in mappings.items():
        # Get profile information for this resource
        resource_def = fhir_resources.get(resource_name, {})
        
        # Initialize counters
        required_fields = []
        required_mapped = []
        must_support_fields = []
        must_support_mapped = []
        optional_fields = []
        optional_mapped = []
        
        # Extract fields info from resource definition
        for field_path, field_info in resource_def.get('fields', {}).items():
            # Skip if no cardinality info (shouldn't happen with proper IG profiles)
            if isinstance(field_info, str) or 'cardinality' not in field_info:
                continue
                
            cardinality = field_info.get('cardinality', '0..1')
            must_support = field_info.get('mustSupport', False)
            
            # Check if field is required (min cardinality > 0)
            min_cardinality = int(cardinality.split('..')[0])
            is_required = min_cardinality > 0
            
            if is_required:
                required_fields.append(field_path)
                if any(mapping.get('target', '').startswith(field_path) for mapping in resource_mappings.values()):
                    required_mapped.append(field_path)
            elif must_support:
                must_support_fields.append(field_path)
                if any(mapping.get('target', '').startswith(field_path) for mapping in resource_mappings.values()):
                    must_support_mapped.append(field_path)
            else:
                optional_fields.append(field_path)
                if any(mapping.get('target', '').startswith(field_path) for mapping in resource_mappings.values()):
                    optional_mapped.append(field_path)
        
        # Calculate percentages
        required_pct = (len(required_mapped) / max(len(required_fields), 1)) * 100
        must_support_pct = (len(must_support_mapped) / max(len(must_support_fields), 1)) * 100
        optional_pct = (len(optional_mapped) / max(len(optional_fields), 1)) * 100
        
        # Determine overall status
        if required_pct < 100:
            status = "🔴"  # Red - missing required fields
        elif must_support_pct < 100:
            status = "🟡"  # Yellow - all required but missing some must-support
        else:
            status = "🟢"  # Green - all required and must-support fields mapped
        
        # Store metrics
        compliance_metrics[resource_name] = {
            'status': status,
            'required': {
                'mapped': len(required_mapped),
                'total': len(required_fields),
                'percentage': required_pct,
                'fields': required_fields,
                'mapped_fields': required_mapped
            },
            'must_support': {
                'mapped': len(must_support_mapped),
                'total': len(must_support_fields),
                'percentage': must_support_pct,
                'fields': must_support_fields,
                'mapped_fields': must_support_mapped
            },
            'optional': {
                'mapped': len(optional_mapped),
                'total': len(optional_fields),
                'percentage': optional_pct,
                'fields': optional_fields,
                'mapped_fields': optional_mapped
            }
        }
    
    return compliance_metrics

def get_overall_compliance_status(compliance_metrics):
    """
    Get the overall compliance status based on all resources.
    
    Args:
        compliance_metrics: Dict of compliance metrics per resource
    
    Returns:
        tuple: (status_emoji, status_description)
    """
    if not compliance_metrics:
        return "⚠️", "No mappings available"
    
    all_required_satisfied = all(
        metrics['required']['percentage'] == 100 
        for metrics in compliance_metrics.values()
    )
    
    all_must_support_satisfied = all(
        metrics['must_support']['percentage'] == 100 
        for metrics in compliance_metrics.values()
    )
    
    if not all_required_satisfied:
        return "🔴", "Required fields missing (Cardinality 1..x)"
    elif not all_must_support_satisfied:
        return "🟡", "All required fields satisfied, some must-support fields missing"
    else:
        return "🟢", "All required and must-support fields satisfied"

def render_compliance_metrics(compliance_metrics):
    """
    Render the compliance metrics in a user-friendly format.
    
    Args:
        compliance_metrics: Dict of compliance metrics per resource
    """
    overall_status, status_desc = get_overall_compliance_status(compliance_metrics)
    
    st.subheader(f"{overall_status} Profile Compliance Metrics")
    st.markdown(f"**Overall Status: {status_desc}**")
    
    for resource_name, metrics in compliance_metrics.items():
        with st.expander(f"{metrics['status']} {resource_name} Compliance"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Required Fields", 
                    f"{metrics['required']['mapped']}/{metrics['required']['total']}",
                    f"{metrics['required']['percentage']:.1f}%"
                )
                if metrics['required']['percentage'] < 100:
                    missing = set(metrics['required']['fields']) - set(metrics['required']['mapped_fields'])
                    st.markdown(f"**Missing required:** {', '.join(missing)}")
            
            with col2:
                st.metric(
                    "Must-Support Fields", 
                    f"{metrics['must_support']['mapped']}/{metrics['must_support']['total']}",
                    f"{metrics['must_support']['percentage']:.1f}%"
                )
                if metrics['must_support']['percentage'] < 100:
                    missing = set(metrics['must_support']['fields']) - set(metrics['must_support']['mapped_fields'])
                    if len(missing) <= 3:  # Only show if not too many
                        st.markdown(f"**Missing must-support:** {', '.join(missing)}")
            
            with col3:
                st.metric(
                    "Optional Fields", 
                    f"{metrics['optional']['mapped']}/{metrics['optional']['total']}",
                    f"{metrics['optional']['percentage']:.1f}%"
                )