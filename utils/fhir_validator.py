"""
FHIR Validator module to validate FHIR resources against implementation guides.
"""
import json
import os
import requests
import streamlit as st
from pathlib import Path

# Cache directory for validation artifacts
VALIDATOR_CACHE_DIR = Path("./cache/validator")

def ensure_validator_cache():
    """
    Ensure the validator cache directory exists.
    """
    VALIDATOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return VALIDATOR_CACHE_DIR

def get_ig_package_url(ig_name, version):
    """
    Get the URL for the implementation guide package.
    
    Args:
        ig_name: The name of the implementation guide (US Core or CARIN BB)
        version: The version of the implementation guide
        
    Returns:
        str: URL to the implementation guide package
    """
    base_urls = {
        "US Core": "https://hl7.org/fhir/us/core/",
        "CARIN BB": "https://hl7.org/fhir/us/carin-bb/"
    }
    
    # Map version numbers to specific package URLs
    version_map = {
        "US Core": {
            "6.1.0": "STU6.1/package.tgz",
            "7.0.0": "STU7/package.tgz"
        },
        "CARIN BB": {
            "1.0.0": "STU1/package.tgz",
            "2.0.0": "STU2/package.tgz"
        }
    }
    
    if ig_name in base_urls and version in version_map.get(ig_name, {}):
        return f"{base_urls[ig_name]}{version_map[ig_name][version]}"
    
    # Default fallback URLs if specific version not found
    fallback_urls = {
        "US Core": "https://hl7.org/fhir/us/core/package.tgz",
        "CARIN BB": "https://hl7.org/fhir/us/carin-bb/package.tgz"
    }
    
    return fallback_urls.get(ig_name, fallback_urls["US Core"])

def download_validation_package(ig_name, version):
    """
    Download the validation package for the specified implementation guide.
    
    Args:
        ig_name: The name of the implementation guide
        version: The version of the implementation guide
        
    Returns:
        Path: Path to the downloaded package
    """
    cache_dir = ensure_validator_cache()
    package_filename = f"{ig_name.lower().replace(' ', '-')}-{version}.tgz"
    package_path = cache_dir / package_filename
    
    # Check if package already exists
    if package_path.exists():
        return package_path
    
    # Download the package
    package_url = get_ig_package_url(ig_name, version)
    try:
        with st.spinner(f"🕸️ Parker is downloading {ig_name} {version} validation package..."):
            response = requests.get(package_url, stream=True)
            response.raise_for_status()
            
            with open(package_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return package_path
    except Exception as e:
        st.error(f"Failed to download validation package: {str(e)}")
        return None

def validate_fhir_resource(resource_json, ig_name, version):
    """
    Validate a FHIR resource against the specified implementation guide.
    
    Uses the FHIR Validator API from clinFHIR or the official FHIR Validator API.
    
    Args:
        resource_json: The FHIR resource as a JSON object
        ig_name: The name of the implementation guide
        version: The version of the implementation guide
        
    Returns:
        dict: Validation results with status and messages
    """
    try:
        # Convert dictionary to JSON string if needed
        if isinstance(resource_json, dict):
            resource_str = json.dumps(resource_json)
        else:
            resource_str = resource_json
            
        # Use the clinFHIR validator API (public and free to use)
        validation_url = "https://clinfhir.com/fhirValidator"
        
        payload = {
            "resource": resource_str,
            "profile": f"{ig_name.lower().replace(' ', '-')}-{version}",
            "implementationGuide": ig_name.lower().replace(' ', '-')
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(validation_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            validation_result = response.json()
            
            # Process the validation result
            issues_found = validation_result.get("issue", [])
            
            # Sort issues by severity
            errors = [issue for issue in issues_found if issue.get("severity") == "error"]
            warnings = [issue for issue in issues_found if issue.get("severity") == "warning"]
            
            # Create structured result
            result = {
                "status": "success" if not errors else ("warning" if warnings and not errors else "error"),
                "message": f"Found {len(errors)} errors and {len(warnings)} warnings" if errors or warnings else "Validation passed successfully",
                "details": []
            }
            
            # Add detailed issues
            for issue in issues_found:
                result["details"].append({
                    "severity": issue.get("severity", "info"),
                    "message": issue.get("diagnostics", "No details provided"),
                    "location": issue.get("location", ["Unknown"])[0] if issue.get("location") else "Unknown location"
                })
                
            return result
        else:
            # Fallback to a basic validation if the API fails
            return perform_basic_validation(resource_json, ig_name, version)
            
    except Exception as e:
        st.warning(f"FHIR validation error: {str(e)}. Using basic validation instead.")
        return perform_basic_validation(resource_json, ig_name, version)

def perform_basic_validation(resource_json, ig_name, version):
    """
    Perform basic validation when external validation is not available.
    
    This checks for resource type, required fields based on the implementation guide,
    and other basic structural requirements.
    
    Args:
        resource_json: The FHIR resource as a JSON object
        ig_name: The name of the implementation guide
        version: The version of the implementation guide
        
    Returns:
        dict: Validation results with status and messages
    """
    result = {
        "status": "warning",
        "message": "Using basic validation (server validation unavailable)",
        "details": []
    }
    
    # Check if it's a valid JSON
    if not isinstance(resource_json, dict):
        try:
            resource_json = json.loads(resource_json)
        except Exception as e:
            result["status"] = "error"
            result["message"] = "Invalid JSON format"
            result["details"].append({
                "severity": "error",
                "message": f"Invalid JSON format: {str(e)}",
                "location": "Resource"
            })
            return result
    
    # Check resource type
    if "resourceType" not in resource_json:
        result["status"] = "error"
        result["details"].append({
            "severity": "error",
            "message": "Missing required field 'resourceType'",
            "location": "Resource"
        })
    
    # Basic requirements for US Core and CARIN BB
    # This is a simplified validation and should be expanded with actual IG requirements
    if ig_name == "US Core":
        if resource_json.get("resourceType") == "Patient":
            if not resource_json.get("name"):
                result["details"].append({
                    "severity": "error",
                    "message": "US Core Patient requires at least one name",
                    "location": "Patient.name"
                })
            
            if version >= "6.0.0" and not resource_json.get("identifier"):
                result["details"].append({
                    "severity": "warning",
                    "message": "US Core Patient should have at least one identifier",
                    "location": "Patient.identifier"
                })
    
    elif ig_name == "CARIN BB":
        if resource_json.get("resourceType") == "ExplanationOfBenefit":
            if not resource_json.get("status"):
                result["details"].append({
                    "severity": "error",
                    "message": "CARIN BB ExplanationOfBenefit requires status",
                    "location": "ExplanationOfBenefit.status"
                })
                
            if not resource_json.get("type"):
                result["details"].append({
                    "severity": "error",
                    "message": "CARIN BB ExplanationOfBenefit requires type",
                    "location": "ExplanationOfBenefit.type"
                })
    
    # Determine final status based on issues found
    errors = [issue for issue in result["details"] if issue["severity"] == "error"]
    warnings = [issue for issue in result["details"] if issue["severity"] == "warning"]
    
    if errors:
        result["status"] = "error"
        result["message"] = f"Found {len(errors)} errors and {len(warnings)} warnings in basic validation"
    elif warnings:
        result["status"] = "warning"
        result["message"] = f"Found {len(warnings)} warnings in basic validation"
    else:
        result["status"] = "success"
        result["message"] = "Basic validation passed"
    
    return result

def validate_fhir_mapping(mappings, source_data_sample, ig_name, version):
    """
    Validate a complete FHIR mapping against the implementation guide.
    
    Args:
        mappings: Dictionary of resource mappings
        source_data_sample: Sample row of source data
        ig_name: The name of the implementation guide
        version: The version of the implementation guide
        
    Returns:
        dict: Validation results with status and messages per resource
    """
    overall_results = {
        "status": "success",
        "resources": {},
        "message": "",
        "details": []
    }
    
    try:
        # Generate sample resources based on mappings and validate each
        for resource_name, fields in mappings.items():
            # Create a sample resource based on the mapping and source data
            resource = {
                "resourceType": resource_name
            }
            
            # Apply mappings to create resource fields
            for field_path, field_mapping in fields.items():
                column_name = field_mapping.get('column')
                if column_name and column_name in source_data_sample:
                    # Handle nested paths (e.g., "name[0].given[0]")
                    parts = field_path.split('.')
                    current = resource
                    
                    for i, part in enumerate(parts):
                        # Handle array notation like "name[0]"
                        if '[' in part and ']' in part:
                            base = part.split('[')[0]
                            index = int(part.split('[')[1].split(']')[0])
                            
                            if base not in current:
                                current[base] = []
                                
                            # Ensure array has enough elements
                            while len(current[base]) <= index:
                                current[base].append({})
                                
                            if i == len(parts) - 1:
                                current[base][index] = source_data_sample[column_name]
                            else:
                                current = current[base][index]
                        else:
                            if i == len(parts) - 1:
                                current[part] = source_data_sample[column_name]
                            else:
                                if part not in current:
                                    current[part] = {}
                                current = current[part]
            
            # Validate the resource
            validation_result = validate_fhir_resource(resource, ig_name, version)
            overall_results["resources"][resource_name] = validation_result
            
            # Aggregate issues
            if validation_result["status"] == "error":
                overall_results["status"] = "error"
                for detail in validation_result.get("details", []):
                    if detail["severity"] == "error":
                        overall_results["details"].append({
                            "severity": "error",
                            "message": f"{resource_name}: {detail['message']}",
                            "location": f"{resource_name}.{detail['location']}"
                        })
            elif validation_result["status"] == "warning" and overall_results["status"] != "error":
                overall_results["status"] = "warning"
                for detail in validation_result.get("details", []):
                    if detail["severity"] == "warning":
                        overall_results["details"].append({
                            "severity": "warning",
                            "message": f"{resource_name}: {detail['message']}",
                            "location": f"{resource_name}.{detail['location']}"
                        })
        
        # Set overall message
        error_count = len([d for d in overall_results["details"] if d["severity"] == "error"])
        warning_count = len([d for d in overall_results["details"] if d["severity"] == "warning"])
        
        if error_count > 0:
            overall_results["message"] = f"Found {error_count} errors and {warning_count} warnings across all resources"
        elif warning_count > 0:
            overall_results["message"] = f"Found {warning_count} warnings across all resources"
        else:
            overall_results["message"] = "All resources validated successfully"
        
        return overall_results
    
    except Exception as e:
        overall_results["status"] = "error"
        overall_results["message"] = f"Validation error: {str(e)}"
        overall_results["details"].append({
            "severity": "error",
            "message": str(e),
            "location": "Overall validation"
        })
        return overall_results

def suggest_mapping_improvements(validation_results):
    """
    Suggest improvements to mapping based on validation results.
    
    Args:
        validation_results: Results from validate_fhir_mapping
        
    Returns:
        dict: Suggestions for improving mappings
    """
    suggestions = {
        "critical": [],
        "recommended": [],
        "optional": []
    }
    
    # Process validation details
    for detail in validation_results.get("details", []):
        severity = detail.get("severity")
        message = detail.get("message", "")
        location = detail.get("location", "")
        
        if "required but not found" in message or "Missing required" in message:
            # Critical suggestion for missing required fields
            resource_path = location.split(".")
            resource_type = resource_path[0] if len(resource_path) > 0 else "Unknown"
            field_path = ".".join(resource_path[1:]) if len(resource_path) > 1 else ""
            
            suggestions["critical"].append({
                "resource": resource_type,
                "field": field_path,
                "message": f"Add mapping for required field: {field_path}",
                "original_error": message
            })
        
        elif severity == "error":
            # Other error-level suggestions
            resource_path = location.split(".")
            resource_type = resource_path[0] if len(resource_path) > 0 else "Unknown"
            field_path = ".".join(resource_path[1:]) if len(resource_path) > 1 else ""
            
            suggestions["critical"].append({
                "resource": resource_type,
                "field": field_path,
                "message": f"Fix error in field mapping: {field_path}",
                "original_error": message
            })
        
        elif severity == "warning":
            # Warning-level suggestions
            resource_path = location.split(".")
            resource_type = resource_path[0] if len(resource_path) > 0 else "Unknown"
            field_path = ".".join(resource_path[1:]) if len(resource_path) > 1 else ""
            
            suggestions["recommended"].append({
                "resource": resource_type,
                "field": field_path,
                "message": f"Consider addressing warning: {field_path}",
                "original_error": message
            })
    
    return suggestions