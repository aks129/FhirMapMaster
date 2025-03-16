"""
Claims Data Mapping Utility for FHIR

This module provides utilities to map healthcare claims data to FHIR resources,
with special focus on CARIN BB Implementation Guide and CPCDS mapping patterns.
"""

import os
import json
import pandas as pd
import streamlit as st
from utils.claims_mapping_data import get_claims_mapping, get_claims_mapping_knowledge_base, CLAIMS_DATA_MAPPINGS

# File path to the CPCDS mapping spreadsheet
CPCDS_MAPPING_FILE = "cache/cpcds/CPCDStoFHIRProfilesMapping.xlsx"

def ensure_cpcds_mappings_loaded():
    """
    Ensure the claims data mappings are loaded into the session state.
    
    This function caches the mappings in session state to avoid reloading.
    """
    if 'claims_mappings' not in st.session_state:
        # First try to load from our comprehensive claims mapping knowledge base
        st.session_state.claims_mappings = {
            "column_to_resource": {},
            "column_to_field": {},
            "resources": {}
        }
        
        # Import all the mappings from our claims mapping data module
        for col, mapping in CLAIMS_DATA_MAPPINGS.items():
            st.session_state.claims_mappings["column_to_resource"][col] = mapping["resource"]
            st.session_state.claims_mappings["column_to_field"][col] = mapping["field"]
            
            # Initialize resource if needed
            if mapping["resource"] not in st.session_state.claims_mappings["resources"]:
                st.session_state.claims_mappings["resources"][mapping["resource"]] = {
                    "fields": {}
                }
            
            # Add field information
            st.session_state.claims_mappings["resources"][mapping["resource"]]["fields"][mapping["field"]] = {
                "description": f"Common claims data field for {col}"
            }
        
        # Then try to enhance with the CPCDS file if available
        try:
            cpcds_mappings = load_cpcds_mappings()
            
            # Merge CPCDS mappings with our knowledge base
            for col, resource in cpcds_mappings.get("column_to_resource", {}).items():
                if col not in st.session_state.claims_mappings["column_to_resource"]:
                    st.session_state.claims_mappings["column_to_resource"][col] = resource
            
            for col, field in cpcds_mappings.get("column_to_field", {}).items():
                if col not in st.session_state.claims_mappings["column_to_field"]:
                    st.session_state.claims_mappings["column_to_field"][col] = field
            
            # Merge resource field information
            for resource, resource_info in cpcds_mappings.get("resources", {}).items():
                if resource not in st.session_state.claims_mappings["resources"]:
                    st.session_state.claims_mappings["resources"][resource] = {"fields": {}}
                
                for field, field_info in resource_info.get("fields", {}).items():
                    if field not in st.session_state.claims_mappings["resources"][resource]["fields"]:
                        st.session_state.claims_mappings["resources"][resource]["fields"][field] = field_info
        except Exception as e:
            print(f"Error loading CPCDS mappings: {str(e)}")
            # Continue with our knowledge base if CPCDS loading fails
    
    return st.session_state.claims_mappings

def load_cpcds_mappings():
    """
    Load the CPCDS to FHIR mappings from the Excel spreadsheet.
    This is a fallback to try to enhance our built-in mappings.
    
    Returns:
        dict: A dictionary containing parsed CPCDS to FHIR mappings
    """
    # If file doesn't exist, return empty mappings
    if not os.path.exists(CPCDS_MAPPING_FILE):
        return {
            "column_to_resource": {},
            "column_to_field": {},
            "resources": {}
        }
    
    try:
        # Use our test parser logic that's more robust
        xl = pd.ExcelFile(CPCDS_MAPPING_FILE)
        sheet_names = xl.sheet_names
        
        # Dictionary to store parsed mappings
        mappings = {
            "column_to_resource": {},  # Maps column names to likely resources
            "column_to_field": {},     # Maps column names to likely fields
            "resources": {}            # Details about each resource and its mappings
        }
        
        # Track CPCDS elements we've seen
        all_cpcds_elements = set()
        
        # Process each sheet (each represents different mappings)
        for sheet_name in sheet_names:
            resource_name = None
            
            # Map sheet names to resource types
            if "EOB" in sheet_name:
                resource_name = "ExplanationOfBenefit"
                # Add the specific subtype if it's mentioned
                if "Inpatient" in sheet_name:
                    resource_name += "-Inpatient-Institutional"
                elif "Outpatient" in sheet_name:
                    resource_name += "-Outpatient-Institutional"
                elif "Pharmacy" in sheet_name:
                    resource_name += "-Pharmacy"
                elif "Professional" in sheet_name:
                    resource_name += "-Professional"
            elif "Coverage" in sheet_name:
                resource_name = "Coverage"
            elif "Patient" in sheet_name:
                resource_name = "Patient"
            elif "Organization" in sheet_name:
                resource_name = "Organization"
            elif "Practitioner" in sheet_name:
                resource_name = "Practitioner"
            
            if not resource_name:
                continue
            
            # Read the sheet - try with and without headers
            try:
                # First try to read with header=None to see raw data format
                df = pd.read_excel(CPCDS_MAPPING_FILE, sheet_name=sheet_name, header=None)
                
                # Find the header row by looking for "CPCDS Element" text
                header_row = None
                for i, row in df.iterrows():
                    for cell in row:
                        if isinstance(cell, str) and "CPCDS Element" in cell:
                            header_row = i
                            break
                    if header_row is not None:
                        break
                
                if header_row is not None:
                    # Read again with the correct header row
                    df = pd.read_excel(CPCDS_MAPPING_FILE, sheet_name=sheet_name, header=header_row)
                else:
                    # Try to find rows with mapping information without headers
                    for i, row in df.iterrows():
                        if len(row) >= 2 and isinstance(row[0], str) and isinstance(row[1], str):
                            cpcds_element = row[0].strip()
                            fhir_element = row[1].strip()
                            
                            if cpcds_element and fhir_element and "." in fhir_element:
                                # Found a mapping row
                                cpcds_element_clean = cpcds_element.lower().replace(" ", "_").replace("-", "_")
                                
                                mappings["column_to_resource"][cpcds_element_clean] = resource_name
                                
                                field_name = fhir_element
                                if "." in fhir_element:
                                    parts = fhir_element.split(".")
                                    field_name = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
                                
                                mappings["column_to_field"][cpcds_element_clean] = field_name
                                
                                if resource_name not in mappings["resources"]:
                                    mappings["resources"][resource_name] = {"fields": {}}
                                
                                mappings["resources"][resource_name]["fields"][field_name] = {
                                    "cpcds_element": cpcds_element,
                                    "description": f"Maps to CPCDS element: {cpcds_element}"
                                }
                
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
        
        return mappings
        
    except Exception as e:
        print(f"Error loading CPCDS mappings: {str(e)}")
        return {
            "column_to_resource": {},
            "column_to_field": {},
            "resources": {}
        }

def enhance_mapping_suggestions(suggestions, df_columns):
    """
    Enhance mapping suggestions using our comprehensive claims data knowledge.
    
    Args:
        suggestions: Dict of current mapping suggestions
        df_columns: List of column names in the DataFrame
    
    Returns:
        dict: Enhanced mapping suggestions
    """
    # Load our mappings 
    mappings = ensure_cpcds_mappings_loaded()
    
    # Process each column to find mappings
    for column in df_columns:
        # See if we already have a high-confidence suggestion
        if column in suggestions and suggestions[column].get("confidence", 0) >= 0.9:
            # Skip columns that already have high-confidence suggestions
            continue
        
        # Try to find a mapping using our comprehensive knowledge base
        mapping = get_claims_mapping(column)
        
        if mapping and mapping["confidence"] >= 0.5:  # Only use reasonably confident mappings
            # Create a new suggestion based on the mapping
            suggestions[column] = {
                "suggested_resource": mapping["resource"],
                "suggested_field": mapping["field"],
                "confidence": mapping["confidence"],
                "explanation": f"Column '{column}' matches a common claims data pattern for {mapping['resource']}.{mapping['field']} ({mapping['match_type']})"
            }
        else:
            # Try direct lookup in our mappings as a fallback
            col_lower = column.lower().replace(" ", "_").replace("-", "_")
            if col_lower in mappings["column_to_resource"]:
                resource = mappings["column_to_resource"][col_lower]
                field = mappings["column_to_field"].get(col_lower, "id")  # Default to id if field mapping not found
                
                # Create or update the suggestion with high confidence
                suggestions[column] = {
                    "suggested_resource": resource,
                    "suggested_field": field,
                    "confidence": 0.9,  # High confidence for direct matches
                    "explanation": f"Column '{column}' directly matches a known claims data field in {resource}.{field}"
                }
    
    return suggestions

def get_claims_mapping_prompt_enhancement():
    """
    Get a prompt enhancement for LLM based on claims data mappings.
    
    Returns:
        str: Text to add to the LLM prompt
    """
    # Use our comprehensive knowledge base directly
    return get_claims_mapping_knowledge_base()