"""
FHIR Profile Compliance Metrics Utility

This module provides functionality to assess mapping compliance with FHIR profiles
based on cardinality and must-support flags.
"""
import json
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
    
    # Resource-specific requirements based on FHIR profiles
    resource_requirements = {
        "Patient": {
            "required": ["identifier", "name", "gender"],
            "must_support": ["birthDate", "address"],
            "composite_fields": {
                "name": ["name.given", "name.family"],
                "address": ["address.line", "address.city", "address.state", "address.postalCode"]
            }
        },
        "Condition": {
            "required": ["clinicalStatus", "category", "code", "subject"],
            "must_support": ["verificationStatus"],
            "composite_fields": {}
        },
        "Encounter": {
            "required": ["status", "class", "subject"],
            "must_support": ["type", "period"],
            "composite_fields": {
                "period": ["period.start", "period.end"]
            }
        },
        "Observation": {
            "required": ["status", "code", "subject"],
            "must_support": ["category", "value[x]", "effectiveDateTime", "effectivePeriod"],
            "composite_fields": {
                "effectivePeriod": ["effectivePeriod.start", "effectivePeriod.end"]
            }
        }
    }
    
    for resource_type, resource_mappings in mappings.items():
        if resource_type not in fhir_resources:
            continue
            
        # Get the resource definition
        resource_def = fhir_resources[resource_type]
        
        # Get mapped fields
        mapped_fields = set(resource_mappings.keys())
        
        # Initialize field categories
        required_fields = []
        must_support_fields = []
        optional_fields = []
        
        # Use resource-specific requirements if available
        if resource_type in resource_requirements:
            required_fields = resource_requirements[resource_type]["required"]
            must_support_fields = resource_requirements[resource_type]["must_support"]
            composite_fields = resource_requirements[resource_type]["composite_fields"]
            
            # Handle composite fields like name.given + name.family = name
            for composite_field, components in composite_fields.items():
                # Check if any component is mapped
                composite_mapped = False
                for component in components:
                    base_component = component.split('.')[0] if '.' in component else component
                    if base_component in mapped_fields:
                        composite_mapped = True
                        break
                
                # If any component is mapped, consider the composite field mapped
                if composite_mapped and composite_field in required_fields:
                    # Add composite field to mapped fields if not already there
                    mapped_fields.add(composite_field)
        else:
            # Dynamically categorize fields based on cardinality
            for field_name, field_data in resource_def.get("fields", {}).items():
                # Skip internal fields or complex nested objects
                if field_name.startswith("_") or isinstance(field_data, dict) and field_data.get("isArray", False):
                    continue
                    
                if isinstance(field_data, dict):
                    # Check if required based on cardinality
                    min_value = field_data.get("min", 0)
                    if min_value > 0:
                        required_fields.append(field_name)
                    elif field_data.get("mustSupport", False):
                        must_support_fields.append(field_name)
                    else:
                        optional_fields.append(field_name)
                else:
                    # Default to optional for simple string descriptions
                    optional_fields.append(field_name)
        
        # Get remaining optional fields
        all_fields = set(resource_def.get("fields", {}).keys())
        explicit_fields = set(required_fields) | set(must_support_fields)
        optional_fields = list(all_fields - explicit_fields)
        
        # Calculate compliance metrics
        required_mapped = [f for f in required_fields if f in mapped_fields]
        must_support_mapped = [f for f in must_support_fields if f in mapped_fields]
        optional_mapped = [f for f in optional_fields if f in mapped_fields]
        
        # Calculate percentages
        required_pct = (len(required_mapped) / len(required_fields)) * 100 if required_fields else 100
        must_support_pct = (len(must_support_mapped) / len(must_support_fields)) * 100 if must_support_fields else 100
        optional_pct = (len(optional_mapped) / len(optional_fields)) * 100 if optional_fields else 0  # If no optional fields, percentage is 0
        
        # Calculate overall completeness percentage with weighting
        # Required fields are weighted at 60%, must-support at 30%, optional at 10%
        overall_pct = (
            (required_pct * 0.6) + 
            (must_support_pct * 0.3) + 
            (optional_pct * 0.1)
        )
        
        # Determine status based on compliance
        if required_pct < 100:
            status = "red"  # Missing required fields
        elif must_support_pct < 100:
            status = "yellow"  # Missing must-support fields
        else:
            status = "green"  # All required and must-support fields mapped
        
        # Store metrics
        compliance_metrics[resource_type] = {
            "required": {
                "total": len(required_fields),
                "mapped": len(required_mapped),
                "percentage": required_pct,
                "missing": sorted(set(required_fields) - mapped_fields)
            },
            "must_support": {
                "total": len(must_support_fields),
                "mapped": len(must_support_mapped),
                "percentage": must_support_pct,
                "missing": sorted(set(must_support_fields) - mapped_fields)
            },
            "optional": {
                "total": len(optional_fields),
                "mapped": len(optional_mapped),
                "percentage": optional_pct,
                "missing": sorted(set(optional_fields) - mapped_fields)[:5]  # Limit to top 5 missing optional fields
            },
            "overall": {
                "percentage": overall_pct,
                "status": status
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
        return "🔄", "No resources mapped yet"
    
    # Count resources by status
    status_counts = {"red": 0, "yellow": 0, "green": 0}
    for resource, metrics in compliance_metrics.items():
        status = metrics.get("overall", {}).get("status", "")
        if status in status_counts:
            status_counts[status] += 1
    
    # Determine overall status
    if status_counts["red"] > 0:
        return "🟥", "Missing required fields"
    elif status_counts["yellow"] > 0:
        return "🟨", "Missing must-support fields"
    else:
        return "🟩", "Compliant with profile"

def render_compliance_metrics(compliance_metrics):
    """
    Render the compliance metrics in a user-friendly format.
    
    Args:
        compliance_metrics: Dict of compliance metrics per resource
    """
    overall_status_emoji, overall_status_desc = get_overall_compliance_status(compliance_metrics)
    
    st.markdown("### 🕸️ Mapping Compliance Metrics")
    st.write(f"**Overall Status:** {overall_status_emoji} {overall_status_desc}")
    
    for resource, metrics in compliance_metrics.items():
        # Skip resources with no fields
        if metrics["required"]["total"] == 0 and metrics["must_support"]["total"] == 0:
            continue
            
        # Add expandable section for each resource
        with st.expander(f"{resource} - {metrics['overall']['percentage']:.1f}% Complete"):
            # Status indicators
            status_indicators = {
                "red": "🟥", 
                "yellow": "🟨", 
                "green": "🟩"
            }
            status = metrics["overall"]["status"]
            
            # Create columns for metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                req_status = "🟩" if metrics["required"]["percentage"] == 100 else "🟥"
                st.markdown(f"**Required Fields:** {req_status}")
                st.write(f"{metrics['required']['mapped']}/{metrics['required']['total']} " + 
                         f"({metrics['required']['percentage']:.1f}%)")
                if metrics['required']['missing']:
                    st.markdown("**Missing:**")
                    for field in metrics['required']['missing']:
                        st.markdown(f"- {field}")
            
            with col2:
                ms_status = "🟩" if metrics["must_support"]["percentage"] == 100 else "🟨"
                st.markdown(f"**Must Support:** {ms_status}")
                st.write(f"{metrics['must_support']['mapped']}/{metrics['must_support']['total']} " + 
                         f"({metrics['must_support']['percentage']:.1f}%)")
                if metrics['must_support']['missing']:
                    st.markdown("**Missing:**")
                    for field in metrics['must_support']['missing']:
                        st.markdown(f"- {field}")
            
            with col3:
                opt_status = "🟩" if metrics["optional"]["percentage"] >= 50 else "⬜️"
                st.markdown(f"**Optional Fields:** {opt_status}")
                st.write(f"{metrics['optional']['mapped']}/{metrics['optional']['total']} " + 
                         f"({metrics['optional']['percentage']:.1f}%)")
                # Only show missing optional fields if below a certain threshold
                if metrics['optional']['percentage'] < 50 and metrics['optional']['missing']:
                    st.markdown("**Top Missing:**")
                    for field in metrics['optional']['missing'][:3]:  # Show only top 3
                        st.markdown(f"- {field}")