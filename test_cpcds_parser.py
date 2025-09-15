"""
Test script to check the CPCDS mapping file parser and comprehensive claims data mappings
"""

import pandas as pd
import os
import json
from pprint import pprint

# Import our comprehensive claims mapping data module
try:
    from utils.claims_mapping_data import get_claims_mapping, get_claims_mapping_knowledge_base, CLAIMS_DATA_MAPPINGS
    has_claims_mapping = True
except ImportError:
    print("WARNING: Claims mapping data module not found. Testing legacy parser only.")
    has_claims_mapping = False

# File path to the CPCDS mapping spreadsheet
CPCDS_MAPPING_FILE = "cache/cpcds/CPCDStoFHIRProfilesMapping.xlsx"

def parse_cpcds_mappings():
    """
    Parse the CPCDS to FHIR mappings from the Excel spreadsheet.
    
    Returns:
        dict: A dictionary containing parsed CPCDS to FHIR mappings
    """
    # If file doesn't exist, return empty mappings
    if not os.path.exists(CPCDS_MAPPING_FILE):
        print(f"File not found: {CPCDS_MAPPING_FILE}")
        return {}
    
    print(f"Loading CPCDS mapping file: {CPCDS_MAPPING_FILE}")
    
    try:
        # Read the spreadsheet - it has multiple sheets
        xl = pd.ExcelFile(CPCDS_MAPPING_FILE)
        sheet_names = xl.sheet_names
        print(f"Found {len(sheet_names)} sheets: {sheet_names}")
        
        # Dictionary to store parsed mappings
        mappings = {
            "column_to_resource": {},  # Maps column names to likely resources
            "column_to_field": {},     # Maps column names to likely fields
            "resources": {}            # Details about each resource and its mappings
        }
        
        # Track CPCDS elements we've seen
        all_cpcds_elements = set()
        mapping_count = 0
        
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
                print(f"Skipping sheet: {sheet_name} - no resource mapping")
                continue
            
            print(f"\nProcessing sheet: {sheet_name} -> {resource_name}")
            
            # Read the sheet - try with and without headers
            try:
                # First try to read with header=None to see raw data format
                df = pd.read_excel(CPCDS_MAPPING_FILE, sheet_name=sheet_name, header=None)
                
                # Find the header row by looking for "CPCDS Element" text
                header_row = None
                for i, row in df.iterrows():
                    if isinstance(row[0], str) and "CPCDS Element" in row[0]:
                        header_row = i
                        break
                
                if header_row is not None:
                    print(f"Found header row at index {header_row}")
                    # Read again with the correct header row
                    df = pd.read_excel(CPCDS_MAPPING_FILE, sheet_name=sheet_name, header=header_row)
                else:
                    print(f"WARNING: No header row found in {sheet_name}")
                    continue
                
                # Look for the CPCDS Element and mapping columns
                cpcds_col = None
                fhir_col = None
                
                for col in df.columns:
                    if isinstance(col, str):
                        if "CPCDS Element" in col:
                            cpcds_col = col
                        elif "FHIR Element" in col or "Reference" in col or "Mapping" in col:
                            fhir_col = col
                
                if not cpcds_col or not fhir_col:
                    print(f"WARNING: Couldn't find mapping columns in {sheet_name}")
                    print(f"Column headers: {df.columns.tolist()}")
                    continue
                
                print(f"Using columns: {cpcds_col} -> {fhir_col}")
                
                # Process the mappings
                sheet_mappings = 0
                for _, row in df.iterrows():
                    cpcds_element = row.get(cpcds_col)
                    fhir_element = row.get(fhir_col)
                    
                    # Skip rows with no mapping
                    if pd.isna(cpcds_element) or pd.isna(fhir_element):
                        continue
                    
                    # Convert to strings if they aren't already
                    cpcds_element = str(cpcds_element).strip()
                    fhir_element = str(fhir_element).strip()
                    
                    if not cpcds_element or not fhir_element:
                        continue
                    
                    # Add to our tracking sets
                    all_cpcds_elements.add(cpcds_element)
                    
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
                    
                    sheet_mappings += 1
                
                print(f"Found {sheet_mappings} mappings in sheet {sheet_name}")
                mapping_count += sheet_mappings
                
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
        
        print(f"\nTotal CPCDS elements found: {len(all_cpcds_elements)}")
        print(f"Total mappings created: {mapping_count}")
        
        # Create a common claims data mapping table based on field name patterns
        # This helps with matching common column variations
        common_patterns = [
            {
                "pattern": ["claim_id", "claimid", "claim_number", "claimnumber", "claim_no", "claimno"],
                "resource": "ExplanationOfBenefit",
                "field": "identifier"
            },
            {
                "pattern": ["patient_id", "patientid", "member_id", "memberid", "patient_number"],
                "resource": "Patient",
                "field": "identifier"
            },
            {
                "pattern": ["provider_id", "providerid", "provider_npi", "provider_number"],
                "resource": "Practitioner",
                "field": "identifier"
            },
            {
                "pattern": ["service_date", "date_of_service", "dos", "service_from", "from_date"],
                "resource": "ExplanationOfBenefit",
                "field": "billablePeriod.start"
            }
        ]
        
        # Add pattern-based mappings
        for pattern_def in common_patterns:
            for pattern in pattern_def["pattern"]:
                if pattern not in mappings["column_to_resource"]:
                    mappings["column_to_resource"][pattern] = pattern_def["resource"]
                    mappings["column_to_field"][pattern] = pattern_def["field"]
                    
                    # Add to the resources dictionary if needed
                    if pattern_def["resource"] not in mappings["resources"]:
                        mappings["resources"][pattern_def["resource"]] = {"fields": {}}
                        
                    if pattern_def["field"] not in mappings["resources"][pattern_def["resource"]]["fields"]:
                        mappings["resources"][pattern_def["resource"]]["fields"][pattern_def["field"]] = {
                            "cpcds_element": f"Common pattern: {pattern}",
                            "description": f"Common claims data field: {pattern}"
                        }
        
        return mappings
        
    except Exception as e:
        print(f"Error loading CPCDS mappings: {str(e)}")
        return {}

def test_claims_mapping():
    """
    Test our comprehensive claims mapping data module.
    """
    if not has_claims_mapping:
        print("Skipping claims mapping test - module not found.")
        return
    
    print("\n\n=== TESTING COMPREHENSIVE CLAIMS DATA MAPPINGS ===")
    
    # Test direct mappings
    print(f"Total built-in mappings: {len(CLAIMS_DATA_MAPPINGS)}")
    
    # Test direct column mapping function
    test_columns = [
        # Standard names
        "claim_id", "patient_id", "provider_id", "service_date", 
        # Common variations
        "claimid", "pat_id", "memberid", "npi", "date_of_service", "dos",
        # Compound variations  
        "claim_number", "patient_identifier", "provider_npi", "service_from_date",
        # Financial fields
        "paid_amount", "allowed_amount", "billed_amount", "copay",
        # Diagnosis and procedures
        "diagnosis_code", "diagnosis_type", "procedure_code", "cpt_code", "hcpcs",
        # Unusual variations
        "clm_id", "mbr_id", "provid", "svc_dt", "pd_amt", "dx_cd",
        # Separators
        "claim.id", "patient-id", "provider id", "service.date",
        # Made up names that should still get mapped
        "my_claim_id_field", "the_patient_identifier", "this_is_the_npi_field"
    ]
    
    matched_count = 0
    for col in test_columns:
        mapping = get_claims_mapping(col)
        if mapping:
            matched_count += 1
            print(f"[OK] {col} -> {mapping['resource']}.{mapping['field']} (Confidence: {mapping['confidence']:.2f}, Type: {mapping['match_type']})")
        else:
            print(f"[X] {col} -> No mapping found")
    
    print(f"\nSuccessfully matched {matched_count} out of {len(test_columns)} test columns ({matched_count/len(test_columns)*100:.1f}%)")
    
    # Test knowledge base generation
    knowledge = get_claims_mapping_knowledge_base()
    knowledge_length = len(knowledge.split('\n'))
    print(f"Generated knowledge base with {knowledge_length} lines")
    
    # Test pattern matching analytics
    try:
        from utils.cpcds_mapping import test_claims_pattern_matching
        print("\n=== TESTING PATTERN MATCHING ANALYTICS ===")
        
        # Create an extended list of column names for thorough testing
        extended_test_columns = test_columns + [
            # More varied forms
            "claim_number_id", "claim_identifier", "claim_key", 
            "patient_medical_record_number", "member_number", "subscriber_id",
            "rendering_provider", "billing_provider_id", "referring_provider",
            "date_of_admission", "discharge_date", "from_date", "to_date",
            # Abbreviated forms
            "clm_nbr", "pt_id", "prov_npi", "svc_from_dt", "svc_to_dt",
            # Common prefixes and suffixes
            "primary_diagnosis_code", "secondary_dx_code", "admitting_diagnosis",
            "claim_status_code", "claim_type_cd", "claim_adjustment_reason",
            # Financial variations
            "total_paid", "payment_amount", "patient_responsibility", "deductible_amount",
            "coinsurance_amt", "copayment", "out_of_pocket", "allowed_amt"
        ]
        
        # Run the pattern matching test
        results = test_claims_pattern_matching(extended_test_columns)
        
        # Display results summary
        print(f"\nMatched {len(results['success'])} out of {results['total']} columns ({results['success_rate_pct']})")
        
        # Display match type statistics
        print("\nMatch type statistics:")
        for match_type, count in results['match_types'].items():
            if count > 0:
                print(f"  - {match_type}: {count} matches")
        
        # Show a few sample successes with Spider-Man theme confidence indicators
        print("\nSample successful matches:")
        for i, match in enumerate(results['success'][:10]):  # Show first 10 matches
            confidence = match['confidence']
            # Confidence indicators
            if confidence >= 0.9:
                indicator = "[HIGH]"  # High confidence
            elif confidence >= 0.7:
                indicator = "[MED]"  # Medium confidence
            elif confidence >= 0.5:
                indicator = "[LOW]"  # Low confidence
            else:
                indicator = "[VLOW]"  # Very low confidence

            print(f"  {indicator} {match['column']} -> {match['mapped_to']} (Confidence: {match['confidence']:.2f}, Type: {match['match_type']})")
        
        # Show a few failed matches
        if results['failed']:
            print("\nSample failed matches:")
            for failed in results['failed'][:5]:  # Show first 5 failures
                print(f"  [X] {failed}")
    
    except ImportError as e:
        print(f"Error testing pattern matching: {e}")
        print("Make sure utils/cpcds_mapping.py is updated with the test_claims_pattern_matching function")

if __name__ == "__main__":
    # Parse the CPCDS mappings
    mappings = parse_cpcds_mappings()
    
    # Print summary statistics
    print("\n=== MAPPING SUMMARY ===")
    print(f"Column to resource mappings: {len(mappings.get('column_to_resource', {}))}")
    print(f"Column to field mappings: {len(mappings.get('column_to_field', {}))}")
    print(f"Resources: {len(mappings.get('resources', {}))}")
    
    # Print a few examples of mappings
    print("\n=== EXAMPLE MAPPINGS ===")
    column_to_resource = mappings.get("column_to_resource", {})
    for i, (col, resource) in enumerate(list(column_to_resource.items())[:10]):
        field = mappings.get("column_to_field", {}).get(col)
        print(f"{col} -> {resource}.{field}")
    
    # Test some common claims data column names
    print("\n=== TESTING COMMON CLAIMS COLUMN NAMES ===")
    test_columns = [
        "claim_id", "claimid", "claim_no",
        "patient_id", "member_id",
        "service_date", "dos", 
        "provider_npi",
        "paid_amount", "allowed_amount"
    ]
    
    for col in test_columns:
        col_lower = col.lower().replace(" ", "_").replace("-", "_")
        resource = mappings.get("column_to_resource", {}).get(col_lower)
        field = mappings.get("column_to_field", {}).get(col_lower)
        if resource and field:
            print(f"[OK] {col} -> {resource}.{field}")
        else:
            print(f"[X] {col} -> No mapping found")
    
    # Save the mappings to a JSON file for reference
    if not os.path.exists("cache/cpcds"):
        os.makedirs("cache/cpcds", exist_ok=True)
    
    with open("cache/cpcds/parsed_mappings.json", "w") as f:
        json.dump(mappings, f, indent=2)
    
    print("\nMappings saved to cache/cpcds/parsed_mappings.json")
    
    # Test our comprehensive claims mapping module
    test_claims_mapping()