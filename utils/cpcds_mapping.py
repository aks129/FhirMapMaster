"""
CPCDS to FHIR Mapping Utility

This module provides utilities to load and use the CPCDS to FHIR Profiles Mapping
from the CARIN BB Implementation Guide.
"""

import os
import json
import pandas as pd
import streamlit as st

# File path to the CPCDS mapping spreadsheet
CPCDS_MAPPING_FILE = "cache/cpcds/CPCDStoFHIRProfilesMapping.xlsx"

def ensure_cpcds_mappings_loaded():
    """
    Ensure the CPCDS to FHIR mappings are loaded into the session state.
    
    This function caches the mapping in session state to avoid reloading the file.
    """
    if 'cpcds_mappings' not in st.session_state:
        st.session_state.cpcds_mappings = load_cpcds_mappings()
    
    return st.session_state.cpcds_mappings

def load_cpcds_mappings():
    """
    Load the CPCDS to FHIR mappings from the Excel spreadsheet.
    
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
        # Read the spreadsheet - it has multiple sheets
        sheet_names = pd.ExcelFile(CPCDS_MAPPING_FILE).sheet_names
        
        # Dictionary to store parsed mappings
        mappings = {
            "column_to_resource": {},  # Maps column names to likely resources
            "column_to_field": {},     # Maps column names to likely fields
            "resources": {}            # Details about each resource and its mappings
        }
        
        # Process each sheet (each represents different mappings)
        for sheet_name in sheet_names:
            # Skip sheets that aren't mapping tables
            if not any(x in sheet_name for x in ["Coverage", "EOB", "Patient", "Organization", "Practitioner"]):
                continue
                
            # Read the sheet
            df = pd.read_excel(CPCDS_MAPPING_FILE, sheet_name=sheet_name, header=None)
            
            # Parse the resource name from the sheet
            resource_name = None
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
            
            if resource_name:
                # Find the mapping table in the sheet
                mapping_rows = []
                mapping_started = False
                
                for _, row in df.iterrows():
                    # Check if this row is the header row
                    if not mapping_started and isinstance(row[0], str) and "CPCDS Element" in row[0]:
                        mapping_started = True
                        continue
                    
                    # If we're in the mapping section, collect the row
                    if mapping_started and pd.notna(row[0]):
                        mapping_rows.append(row)
                
                # Process the mapping rows
                for row in mapping_rows:
                    cpcds_element = row[0]
                    fhir_element = row[1] if len(row) > 1 and pd.notna(row[1]) else None
                    
                    if isinstance(cpcds_element, str) and cpcds_element and fhir_element:
                        # Clean up the CPCDS element (convert to lowercase for better matching)
                        cpcds_element_clean = cpcds_element.lower().replace(" ", "_").replace("-", "_")
                        
                        # Add to column to resource mapping
                        mappings["column_to_resource"][cpcds_element_clean] = resource_name
                        
                        # Add to column to field mapping (remove resource name prefix if present)
                        field_name = fhir_element
                        if "." in fhir_element:
                            parts = fhir_element.split(".")
                            field_name = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
                        
                        mappings["column_to_field"][cpcds_element_clean] = field_name
                        
                        # Add to resources dictionary
                        if resource_name not in mappings["resources"]:
                            mappings["resources"][resource_name] = {
                                "fields": {}
                            }
                        
                        mappings["resources"][resource_name]["fields"][field_name] = {
                            "cpcds_element": cpcds_element,
                            "description": f"Maps to CPCDS element: {cpcds_element}"
                        }
        
        # Create alternate names for common data elements to improve matching
        # This helps with common variations of field names
        column_variations = {}
        for col, resource in mappings["column_to_resource"].items():
            # Generate variations for claim_id type fields
            if "claim" in col and "id" in col:
                variations = [
                    "claim_id", "claimid", "claim_number", "claimnumber", 
                    "claim_no", "claimno", "id", "identifier"
                ]
                for var in variations:
                    column_variations[var] = resource
            
            # Generate variations for patient_id type fields  
            if "patient" in col and "id" in col:
                variations = [
                    "patient_id", "patientid", "patient_number", "patientnumber",
                    "patient_identifier", "memberid", "member_id"
                ]
                for var in variations:
                    column_variations[var] = resource
            
            # Add more variations as needed for other common fields
        
        # Add variations to the mappings
        for col, resource in column_variations.items():
            if col not in mappings["column_to_resource"]:
                mappings["column_to_resource"][col] = resource
        
        return mappings
        
    except Exception as e:
        # If there's an error, return empty mappings
        print(f"Error loading CPCDS mappings: {str(e)}")
        return {
            "column_to_resource": {},
            "column_to_field": {},
            "resources": {}
        }

def get_cpcds_mapping_knowledge():
    """
    Get a structured knowledge representation of CPCDS to FHIR mappings for LLM context.
    
    Returns:
        str: A formatted string containing CPCDS mapping knowledge
    """
    mappings = ensure_cpcds_mappings_loaded()
    
    # Create a structured, human-readable knowledge base for the LLM
    knowledge = "# CPCDS to FHIR Mapping Knowledge\n\n"
    
    # Add a section for key column naming patterns
    knowledge += "## Key Column Naming Patterns\n\n"
    
    # Group by resource for better organization
    resource_columns = {}
    for col, resource in mappings["column_to_resource"].items():
        if resource not in resource_columns:
            resource_columns[resource] = []
        resource_columns[resource].append(col)
    
    # Add each resource's column patterns
    for resource, columns in resource_columns.items():
        knowledge += f"### {resource} Columns\n"
        knowledge += "Common column names that map to this resource:\n"
        knowledge += ", ".join(columns[:20])  # Limit to 20 to avoid making the context too large
        knowledge += "\n\n"
    
    # Add specific mapping details for important resources
    knowledge += "## Detailed Field Mappings\n\n"
    
    key_resources = [r for r in mappings["resources"].keys() if "ExplanationOfBenefit" in r]
    key_resources.extend(["Coverage", "Patient", "Organization", "Practitioner"])
    
    for resource in key_resources:
        if resource in mappings["resources"]:
            knowledge += f"### {resource}\n"
            fields = mappings["resources"][resource].get("fields", {})
            for field_name, field_info in fields.items():
                knowledge += f"- {field_name}: {field_info.get('description', '')}\n"
            knowledge += "\n"
    
    return knowledge

def enhance_mapping_suggestions(suggestions, df_columns):
    """
    Enhance mapping suggestions using CPCDS mapping knowledge.
    
    Args:
        suggestions: Dict of current mapping suggestions
        df_columns: List of column names in the DataFrame
    
    Returns:
        dict: Enhanced mapping suggestions
    """
    mappings = ensure_cpcds_mappings_loaded()
    
    # Process each column to see if it matches known CPCDS patterns
    for column in df_columns:
        col_lower = column.lower().replace(" ", "_").replace("-", "_")
        
        # Check if this column has a known mapping
        if col_lower in mappings["column_to_resource"]:
            resource = mappings["column_to_resource"][col_lower]
            field = mappings["column_to_field"].get(col_lower, "id")  # Default to id if field mapping not found
            
            # Create or update the suggestion with high confidence
            if column not in suggestions:
                suggestions[column] = {}
            
            if "suggested_resource" not in suggestions[column] or suggestions[column].get("confidence", 0) < 0.9:
                suggestions[column] = {
                    "suggested_resource": resource,
                    "suggested_field": field,
                    "confidence": 0.95,  # High confidence for direct matches
                    "explanation": f"Matched to CPCDS element mapping for {resource}.{field}"
                }
    
    return suggestions

def get_cpcds_prompt_enhancement():
    """
    Get a prompt enhancement for LLM based on CPCDS mappings.
    
    Returns:
        str: Text to add to the LLM prompt
    """
    mappings = ensure_cpcds_mappings_loaded()
    
    # If no mappings loaded, return a basic guide
    if not mappings["column_to_resource"]:
        return """
        When mapping healthcare claims data, consider these common patterns:
        - claim_id, claimid -> ExplanationOfBenefit.identifier
        - patient_id, patient_identifier -> Patient.identifier
        - payer_id, payer -> Coverage.payor
        - service_date, date_of_service -> ExplanationOfBenefit.billablePeriod.start
        - provider_id, provider -> ExplanationOfBenefit.provider
        """
    
    # Create a more detailed guide based on actual mappings
    prompt = """
    # CARIN BB CPCDS Mapping Guidelines
    
    When mapping healthcare claims data, use these established mappings from the CARIN BB Implementation Guide:
    
    ## Common Column Patterns:
    """
    
    # Add key column patterns for important resources
    key_resources = [r for r in mappings["resources"].keys() if "ExplanationOfBenefit" in r]
    key_resources.extend(["Coverage", "Patient", "Organization", "Practitioner"])
    
    for resource in key_resources:
        prompt += f"\n### {resource}:\n"
        columns = [col for col, res in mappings["column_to_resource"].items() if res == resource]
        if columns:
            for i in range(0, min(10, len(columns))):
                col = columns[i]
                field = mappings["column_to_field"].get(col)
                prompt += f"- {col} → {resource}.{field}\n"
    
    return prompt