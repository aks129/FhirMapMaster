import requests
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import time

# Cache directory for downloaded resources
CACHE_DIR = Path("./cache")

def ensure_cache_dir():
    """Ensure the cache directory exists"""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True)

def fetch_us_core_profiles():
    """
    Fetch US Core Implementation Guide profiles from GitHub.
    
    Returns:
        dict: A dictionary containing US Core profile definitions.
    """
    # Create cache file path
    cache_file = CACHE_DIR / "us_core_profiles.json"
    
    # Check if we have a cached version
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading cached US Core profiles: {str(e)}. Fetching from source.")
    
    us_core_profiles = {}
    
    # Base URL for raw GitHub content
    base_url = "https://raw.githubusercontent.com/HL7/US-Core/master/input/resources/StructureDefinition"
    
    # List of core resources to fetch
    resources = [
        "us-core-patient", 
        "us-core-practitioner", 
        "us-core-observation",
        "us-core-condition", 
        "us-core-procedure", 
        "us-core-medication",
        "us-core-encounter", 
        "us-core-medicationrequest",
        "us-core-allergyintolerance",
        "us-core-immunization",
        "us-core-diagnosticreport-lab",
        "us-core-diagnosticreport-note"
    ]
    
    try:
        for resource in resources:
            url = f"{base_url}/{resource}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                profile = response.json()
                
                # Extract relevant information
                resource_type = profile.get("type", "Unknown")
                
                # Create a clean structure with field definitions
                fields = {}
                
                # Process the differential elements to get field definitions
                for element in profile.get("differential", {}).get("element", []):
                    path = element.get("path", "")
                    
                    # Skip the base resource definition and complex nested structures
                    if "." in path and path.count(".") == 1 and resource_type in path:
                        # Extract the field name after the resource type
                        field = path.split(".")[-1]
                        
                        # Get description or definition
                        definition = element.get("definition", element.get("short", "No description"))
                        
                        fields[field] = definition
                
                # Add to our profiles dictionary
                if resource_type not in us_core_profiles:
                    us_core_profiles[resource_type] = {
                        "fields": fields,
                        "description": profile.get("description", f"US Core {resource_type} profile")
                    }
                else:
                    # Merge fields if resource already exists
                    us_core_profiles[resource_type]["fields"].update(fields)
                
            else:
                print(f"Failed to fetch {resource}: {response.status_code}")
                
        # Cache the profiles
        ensure_cache_dir()
        with open(cache_file, 'w') as f:
            json.dump(us_core_profiles, f, indent=2)
            
        return us_core_profiles
    
    except Exception as e:
        st.error(f"Error fetching US Core profiles: {str(e)}")
        return {}

def fetch_carin_bb_profiles():
    """
    Fetch CARIN BB Implementation Guide profiles from GitHub.
    
    Returns:
        dict: A dictionary containing CARIN BB profile definitions.
    """
    # Create cache file path
    cache_file = CACHE_DIR / "carin_bb_profiles.json"
    
    # Check if we have a cached version
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading cached CARIN BB profiles: {str(e)}. Fetching from source.")
    
    carin_bb_profiles = {}
    
    # Base URL for raw GitHub content
    base_url = "https://raw.githubusercontent.com/HL7/carin-bb/master/input/resources/StructureDefinition"
    
    # List of core resources to fetch
    resources = [
        "CARIN-BB-Coverage", 
        "CARIN-BB-ExplanationOfBenefit",
        "CARIN-BB-ExplanationOfBenefit-Inpatient-Institutional",
        "CARIN-BB-ExplanationOfBenefit-Outpatient-Institutional", 
        "CARIN-BB-ExplanationOfBenefit-Pharmacy", 
        "CARIN-BB-ExplanationOfBenefit-Professional",
        "CARIN-BB-Organization", 
        "CARIN-BB-Patient",
        "CARIN-BB-Practitioner"
    ]
    
    try:
        for resource in resources:
            url = f"{base_url}/{resource}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                profile = response.json()
                
                # Extract base resource type from the profile name
                full_type = profile.get("type", "")
                resource_type = full_type.split('-')[-1] if '-' in full_type else full_type
                
                # Create a clean structure with field definitions
                fields = {}
                
                # Process the differential elements to get field definitions
                for element in profile.get("differential", {}).get("element", []):
                    path = element.get("path", "")
                    
                    # Skip the base resource definition and complex nested structures
                    if "." in path and path.count(".") == 1 and resource_type.lower() in path.lower():
                        # Extract the field name after the resource type
                        field = path.split(".")[-1]
                        
                        # Get description or definition
                        definition = element.get("definition", element.get("short", "No description"))
                        
                        fields[field] = definition
                
                # Add to our profiles dictionary
                if resource_type not in carin_bb_profiles:
                    carin_bb_profiles[resource_type] = {
                        "fields": fields,
                        "description": profile.get("description", f"CARIN BB {resource_type} profile")
                    }
                else:
                    # Merge fields if resource already exists
                    carin_bb_profiles[resource_type]["fields"].update(fields)
                
            else:
                print(f"Failed to fetch {resource}: {response.status_code}")
                
        # Cache the profiles
        ensure_cache_dir()
        with open(cache_file, 'w') as f:
            json.dump(carin_bb_profiles, f, indent=2)
            
        return carin_bb_profiles
    
    except Exception as e:
        st.error(f"Error fetching CARIN BB profiles: {str(e)}")
        return {}

def enrich_fhir_resources_with_ig_profiles(resources, standard):
    """
    Enrich the existing FHIR resources with detailed Implementation Guide profiles.
    
    Args:
        resources: Dict containing the current FHIR resource definitions
        standard: The FHIR standard (US Core or CARIN BB)
        
    Returns:
        dict: Enriched FHIR resource definitions
    """
    # Make a deep copy to avoid modifying the original
    import copy
    enriched = copy.deepcopy(resources)
    
    try:
        if standard == "US Core":
            ig_profiles = fetch_us_core_profiles()
        elif standard == "CARIN BB":
            ig_profiles = fetch_carin_bb_profiles()
        else:
            return resources  # No enrichment for unknown standards
            
        # Enrich each resource with IG profile data
        for resource_name, resource_data in ig_profiles.items():
            if resource_name in enriched:
                # Merge descriptions
                if "description" in resource_data:
                    enriched[resource_name]["description"] = resource_data["description"]
                
                # Merge fields, prioritizing IG-specific definitions
                if "fields" in resource_data:
                    for field, field_data in resource_data["fields"].items():
                        # If the field exists and it's a string description, convert to dict first
                        if field in enriched[resource_name]["fields"]:
                            if isinstance(enriched[resource_name]["fields"][field], str):
                                current_description = enriched[resource_name]["fields"][field]
                                enriched[resource_name]["fields"][field] = {
                                    "description": current_description
                                }
                            
                            # Extract and add cardinality information if available
                            if isinstance(field_data, dict):
                                # Extract cardinality from the differential element
                                if "min" in field_data and "max" in field_data:
                                    min_occurs = field_data.get("min", 0)
                                    max_occurs = field_data.get("max", "*")
                                    cardinality = f"{min_occurs}..{max_occurs}"
                                    
                                    # Update with cardinality and must-support info
                                    enriched[resource_name]["fields"][field]["cardinality"] = cardinality
                                    enriched[resource_name]["fields"][field]["min"] = min_occurs
                                    enriched[resource_name]["fields"][field]["max"] = max_occurs
                                    
                                    # Add must-support flag if available
                                    must_support = field_data.get("mustSupport", False)
                                    enriched[resource_name]["fields"][field]["mustSupport"] = must_support
                                
                                # Update or add description
                                if "description" in field_data:
                                    enriched[resource_name]["fields"][field]["description"] = field_data["description"]
                                elif isinstance(field_data, str):
                                    # If field_data is just a string, it's a description
                                    enriched[resource_name]["fields"][field]["description"] = field_data
                            else:
                                # If field_data is just a string, it's a description
                                enriched[resource_name]["fields"][field]["description"] = field_data
                        else:
                            # Field doesn't exist yet, add it
                            if isinstance(field_data, dict):
                                enriched[resource_name]["fields"][field] = field_data
                            else:
                                # Just a string description
                                enriched[resource_name]["fields"][field] = {
                                    "description": field_data,
                                    "cardinality": "0..1",  # Default cardinality
                                    "min": 0,
                                    "max": "1",
                                    "mustSupport": False
                                }
            else:
                # If the resource doesn't exist in our base definitions, add it
                enriched[resource_name] = resource_data
                
        # Ensure every field has cardinality info by providing defaults where missing
        for resource_name, resource_data in enriched.items():
            for field, field_data in resource_data.get("fields", {}).items():
                if isinstance(field_data, str):
                    # Convert string descriptions to dict
                    enriched[resource_name]["fields"][field] = {
                        "description": field_data,
                        "cardinality": "0..1",  # Default cardinality
                        "min": 0,
                        "max": "1",
                        "mustSupport": False
                    }
                elif isinstance(field_data, dict) and "cardinality" not in field_data:
                    # Add default cardinality where missing
                    field_data["cardinality"] = "0..1"
                    field_data["min"] = 0
                    field_data["max"] = "1"
                    field_data["mustSupport"] = False
                
        return enriched
        
    except Exception as e:
        st.warning(f"Error enriching FHIR resources with IG profiles: {str(e)}")
        return resources  # Return original if enrichment fails