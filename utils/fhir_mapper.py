import pandas as pd
import numpy as np
import streamlit as st
import json
import re
from utils.fhir_ig_loader import fetch_us_core_profiles, fetch_carin_bb_profiles, enrich_fhir_resources_with_ig_profiles

# FHIR Resource Type definitions
US_CORE_RESOURCES = {
    'Patient': {
        'description': 'Demographics and other administrative information about an individual or animal receiving care or other health-related services.',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business Identifiers for the patient (MRN, SSN, etc.)',
            'name': 'A name associated with the patient',
            'telecom': 'A contact detail for the individual',
            'gender': 'male | female | other | unknown',
            'birthDate': 'The date of birth for the individual',
            'address': 'Address for the individual',
            'maritalStatus': 'Marital (civil) status of a patient',
            'communication': 'A language which may be used to communicate with the patient about his or her health',
            'extension': 'US Core Race Extension, US Core Ethnicity Extension, etc.'
        }
    },
    'Condition': {
        'description': 'A clinical condition, problem, diagnosis, or other event, situation, issue, or clinical concept.',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business identifier',
            'clinicalStatus': 'active | recurrence | relapse | inactive | remission | resolved',
            'verificationStatus': 'unconfirmed | provisional | differential | confirmed | refuted | entered-in-error',
            'category': 'problem-list-item | encounter-diagnosis',
            'code': 'Identification of the condition, problem or diagnosis',
            'subject': 'Reference to the patient',
            'onsetDateTime': 'Estimated or actual date or date-time condition began',
            'abatementDateTime': 'When in resolution/remission'
        }
    },
    'Observation': {
        'description': 'Measurements and assertions about a patient',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business identifier',
            'status': 'registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown',
            'category': 'Type of observation (vital-signs | laboratory | etc.)',
            'code': 'Type of observation (code / type)',
            'subject': 'Reference to the patient',
            'effectiveDateTime': 'Clinically relevant time/time-period for observation',
            'valueQuantity': 'Actual result',
            'valueCodeableConcept': 'Actual result',
            'valueString': 'Actual result',
            'valueBoolean': 'Actual result',
            'valueInteger': 'Actual result',
            'valueRange': 'Actual result',
            'valueRatio': 'Actual result',
            'valueTime': 'Actual result',
            'valueDateTime': 'Actual result'
        }
    },
    'Procedure': {
        'description': 'An action that is being or was performed on or for a patient',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business identifier',
            'status': 'preparation | in-progress | not-done | on-hold | stopped | completed | entered-in-error | unknown',
            'code': 'Identification of the procedure',
            'subject': 'Reference to the patient',
            'performedDateTime': 'Date/Period the procedure was performed',
            'performedPeriod': 'Date/Period the procedure was performed',
            'performer': 'The people who performed the procedure',
            'reasonCode': 'Coded reason procedure performed'
        }
    },
    'MedicationRequest': {
        'description': 'An order or request for both supply of the medication and the instructions for administration',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business identifier',
            'status': 'active | on-hold | cancelled | completed | entered-in-error | stopped | draft | unknown',
            'intent': 'proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option',
            'medication': 'What medication was requested',
            'subject': 'Reference to the patient',
            'authoredOn': 'When request was initially authored',
            'requester': 'Who/What requested the medication',
            'dosageInstruction': 'How the medication should be taken',
            'dispenseRequest': 'Medication supply authorization'
        }
    }
}

CARIN_BB_RESOURCES = {
    'Coverage': {
        'description': 'Insurance or medical plan or a payment agreement',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business Identifier for the coverage',
            'status': 'active | cancelled | draft | entered-in-error',
            'type': 'Classification of coverage',
            'subscriber': 'Reference to the subscriber',
            'subscriberId': 'ID assigned to the subscriber',
            'beneficiary': 'Reference to the patient',
            'relationship': 'Beneficiary relationship to the subscriber',
            'period': 'Coverage start and end dates',
            'payor': 'Reference to the insurer'
        }
    },
    'ExplanationOfBenefit': {
        'description': 'Explanation of Benefit (EOB), remittance, and claims-related information',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business Identifier',
            'status': 'active | cancelled | draft | entered-in-error',
            'type': 'Category of service or product',
            'patient': 'Reference to the patient',
            'billablePeriod': 'Relevant time frame for the claim',
            'created': 'Response creation date',
            'provider': 'Reference to the care provider',
            'payee': 'Recipient of benefits payable',
            'insurance': 'Patient insurance information',
            'total': 'Adjudication totals',
            'payment': 'Payment details'
        }
    },
    'Organization': {
        'description': 'A formally or informally recognized grouping of people or organizations',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business Identifiers',
            'active': 'Whether the organization is still active',
            'type': 'Kind of organization',
            'name': 'Name used for the organization',
            'telecom': 'Contact details for the organization',
            'address': 'Official address of the organization'
        }
    },
    'Practitioner': {
        'description': 'A person who is directly or indirectly involved in the provisioning of healthcare',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business Identifiers',
            'active': 'Whether this practitioner is active',
            'name': 'The name(s) associated with the practitioner',
            'telecom': 'Contact details for the practitioner',
            'address': 'Address(es) of the practitioner',
            'gender': 'male | female | other | unknown',
            'qualification': 'Certification, licenses, or training'
        }
    }
}

def get_fhir_resources(standard, version=""):
    """
    Get FHIR resource definitions based on the selected standard and version.
    
    Args:
        standard: The FHIR standard to use (US Core or CARIN BB)
        version: The version of the implementation guide (optional)
    
    Returns:
        dict containing resource definitions
    """
    resources = {}
    
    if "US Core" in standard:
        # Start with the base resources
        resources = US_CORE_RESOURCES.copy()
        
        # Try to enrich with Implementation Guide profiles
        try:
            with st.spinner("Enhancing with US Core Implementation Guide..."):
                # Fetch and enrich with US Core Implementation Guide
                ig_profiles = fetch_us_core_profiles()
                
                # Enrich our base resources with IG-specific details
                for resource_name, resource_data in ig_profiles.items():
                    # If resource exists, merge the fields
                    if resource_name in resources:
                        if "fields" in resource_data:
                            resources[resource_name]["fields"].update(resource_data["fields"])
                        if "description" in resource_data:
                            resources[resource_name]["description"] = resource_data["description"]
                    else:
                        # If it's a new resource, add it
                        resources[resource_name] = resource_data
        except Exception as e:
            st.warning(f"Could not enhance with US Core Implementation Guide: {str(e)}")
            
    elif "CARIN BB" in standard:
        # Start with the base resources
        resources = CARIN_BB_RESOURCES.copy()
        
        # Try to enrich with Implementation Guide profiles
        try:
            with st.spinner("Enhancing with CARIN BB Implementation Guide..."):
                # Fetch and enrich with CARIN BB Implementation Guide
                ig_profiles = fetch_carin_bb_profiles()
                
                # Enrich our base resources with IG-specific details
                for resource_name, resource_data in ig_profiles.items():
                    # If resource exists, merge the fields
                    if resource_name in resources:
                        if "fields" in resource_data:
                            resources[resource_name]["fields"].update(resource_data["fields"])
                        if "description" in resource_data:
                            resources[resource_name]["description"] = resource_data["description"]
                    else:
                        # If it's a new resource, add it
                        resources[resource_name] = resource_data
        except Exception as e:
            st.warning(f"Could not enhance with CARIN BB Implementation Guide: {str(e)}")
            
    else:
        return {}
        
    return resources

def suggest_mappings(df, standard, version=""):
    """
    Suggest mappings from the dataframe columns to FHIR resources.
    
    Args:
        df: pandas DataFrame containing the data
        standard: The FHIR standard to use (US Core or CARIN BB)
        version: The version of the implementation guide (optional)
    
    Returns:
        dict containing suggested mappings and confidence scores
    """
    resources = get_fhir_resources(standard, version)
    mappings = {}
    
    # Function to calculate similarity score between column name and FHIR field
    def calculate_similarity(column_name, fhir_field, resource_name):
        column_name = column_name.lower()
        fhir_field = fhir_field.lower()
        resource_name = resource_name.lower()
        
        # Extract the entity prefix from the column name (e.g., "patient_id" -> "patient")
        column_prefix = column_name.split('_')[0] if '_' in column_name else ""
        
        # Check if the column is explicitly associated with a resource by prefix
        resource_match = False
        
        # Define mappings between common column prefixes and FHIR resources
        resource_prefixes = {
            'patient': ['patient'],
            'practitioner': ['practitioner', 'doctor', 'provider'],
            'observation': ['observation', 'vital', 'lab', 'test'],
            'condition': ['condition', 'diagnosis', 'problem'],
            'medication': ['medication', 'med', 'drug'],
            'encounter': ['encounter', 'visit', 'admission'],
            'procedure': ['procedure', 'surgery', 'treatment'],
            'coverage': ['coverage', 'insurance', 'plan'],
            'claim': ['claim', 'bill', 'invoice'],
            'organization': ['organization', 'org', 'facility', 'hospital']
        }
        
        # Check if column prefix matches resource
        for res, prefixes in resource_prefixes.items():
            if column_prefix in prefixes and res in resource_name:
                resource_match = True
                break
            
        # Direct match - strongest case
        if column_name == fhir_field:
            # If this is a direct match and the resource also matches the column prefix, this is ideal
            return 1.0 + (0.2 if resource_match else 0.0)
        
        # Penalize mismatched resources (e.g., patient_id mapping to Practitioner.id)
        if column_prefix and column_prefix in resource_prefixes:
            for matching_resource in resource_prefixes.keys():
                if column_prefix in resource_prefixes[matching_resource] and matching_resource not in resource_name.lower():
                    # This column has a prefix that suggests a different resource - apply penalty
                    penalty = -0.5
                    return penalty
        
        # Contains match
        if column_name in fhir_field or fhir_field in column_name:
            base_score = 0.8
            # Boost if the resource matches
            if resource_match:
                base_score += 0.15
            return base_score
        
        # If the column has an entity prefix but doesn't match this resource, lower the score
        if column_prefix and not resource_match and column_prefix in sum(resource_prefixes.values(), []):
            return 0.1  # Very low base score for mismatched resources
        
        # Check for common prefixes/suffixes and abbreviations
        column_parts = re.split(r'[_\s\-]', column_name)
        fhir_parts = re.split(r'[_\s\-]', fhir_field)
        
        # Check for parts match
        common_parts = set(column_parts).intersection(set(fhir_parts))
        if common_parts:
            base_score = 0.5 + (0.3 * (len(common_parts) / max(len(column_parts), len(fhir_parts))))
            # Boost if the resource matches
            if resource_match:
                base_score += 0.1
            return base_score
        
        # Low confidence for potential matches
        for col_part in column_parts:
            for fhir_part in fhir_parts:
                if (col_part in fhir_part or fhir_part in col_part) and len(col_part) > 2 and len(fhir_part) > 2:
                    return 0.4 + (0.1 if resource_match else 0.0)
        
        return 0.0  # No obvious connection
    
    # Define commonly expected data patterns for different FHIR fields
    data_patterns = {
        'birthDate': lambda s: pd.api.types.is_datetime64_any_dtype(s) or (isinstance(s, pd.Series) and s.astype(str).str.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$').any()),
        'gender': lambda s: (isinstance(s, pd.Series) and s.astype(str).str.lower().isin(['male', 'female', 'm', 'f', 'other', 'unknown']).any()),
        'telecom': lambda s: (isinstance(s, pd.Series) and (s.astype(str).str.contains(r'@').any() or s.astype(str).str.contains(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}').any())),
        'address': lambda s: (isinstance(s, pd.Series) and s.astype(str).str.contains(r'\d+\s+\w+\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd)', case=False).any()),
        'identifier': lambda s: s.nunique() > 0.8 * len(df) if len(df) > 10 else False
    }
    
    # Pre-filter columns that explicitly mention entities
    resource_column_map = {}
    
    # Map columns to likely resources based on their name
    for column in df.columns:
        column_lower = column.lower()
        prefix = column_lower.split('_')[0] if '_' in column_lower else column_lower
        
        # Check if column has a clear entity prefix and map it to the appropriate resource
        if prefix == 'patient':
            if 'Patient' not in resource_column_map:
                resource_column_map['Patient'] = []
            resource_column_map['Patient'].append(column)
        elif prefix in ['practitioner', 'doctor', 'provider']:
            if 'Practitioner' not in resource_column_map:
                resource_column_map['Practitioner'] = []
            resource_column_map['Practitioner'].append(column)
        elif prefix in ['medication', 'med', 'drug']:
            if 'Medication' not in resource_column_map:
                resource_column_map['Medication'] = []
            resource_column_map['Medication'].append(column)
        elif prefix in ['condition', 'diagnosis', 'problem']:
            if 'Condition' not in resource_column_map:
                resource_column_map['Condition'] = []
            resource_column_map['Condition'].append(column)
        elif prefix in ['encounter', 'visit']:
            if 'Encounter' not in resource_column_map:
                resource_column_map['Encounter'] = []
            resource_column_map['Encounter'].append(column)
        elif prefix in ['vital', 'observation', 'lab', 'test']:
            if 'Observation' not in resource_column_map:
                resource_column_map['Observation'] = []
            resource_column_map['Observation'].append(column)
        else:
            # For columns without clear prefix, consider them for all resources
            for resource_name in resources.keys():
                if resource_name not in resource_column_map:
                    resource_column_map[resource_name] = []
                resource_column_map[resource_name].append(column)

    # Process all columns, with smart mapping
    for resource_name, resource in resources.items():
        # Get columns to consider for this resource
        columns_to_process = resource_column_map.get(resource_name, [])
        if not columns_to_process:
            continue
            
        for column in columns_to_process:
            best_field = None
            best_score = 0.0
            
            for field, description in resource['fields'].items():
                # Calculate similarity with resource context considered
                similarity = calculate_similarity(column, field, resource_name)
                
                # Skip if negative similarity (indicating a resource mismatch)
                if similarity < 0:
                    continue
                    
                # Check for data pattern matches to boost confidence
                if field in data_patterns and data_patterns[field](df[column]):
                    similarity += 0.3
                
                # Check for data type compatibility
                if field in ['birthDate', 'effectiveDateTime', 'performedDateTime'] and pd.api.types.is_datetime64_any_dtype(df[column]):
                    similarity += 0.2
                
                if similarity > best_score:
                    best_score = similarity
                    best_field = field
            
            if best_score > 0.3 and best_field:  # Only include matches with reasonable confidence
                if resource_name not in mappings:
                    mappings[resource_name] = {}
                
                # Don't overwrite an existing mapping if it has a higher confidence
                if best_field in mappings[resource_name]:
                    existing_mapping = mappings[resource_name][best_field]
                    if existing_mapping['confidence'] >= best_score:
                        continue
                
                mappings[resource_name][best_field] = {
                    'column': column,
                    'confidence': round(best_score, 2)
                }
    
    return mappings

def generate_fhir_structure(mappings, standard, version=""):
    """
    Generate a FHIR resource structure based on the mappings.
    
    Args:
        mappings: Dict containing the mappings from columns to FHIR fields
        standard: The FHIR standard used
        version: The version of the implementation guide (optional)
    
    Returns:
        dict containing the FHIR resource structure
    """
    fhir_structure = {}
    
    for resource_name, fields in mappings.items():
        fhir_structure[resource_name] = {
            'resourceType': resource_name,
            'fields': fields
        }
    
    return fhir_structure

def generate_python_mapping_code(mappings, standard, df, version=""):
    """
    Generate Python code for mapping data to FHIR format.
    
    Args:
        mappings: Dict containing the mappings from columns to FHIR fields
        standard: The FHIR standard used
        df: The original dataframe
        version: The version of the implementation guide (optional)
    
    Returns:
        str containing the Python code
    """
    code = """
import pandas as pd
import json
from datetime import datetime

def transform_data_to_fhir(data_df):
    \"\"\"
    Transform source data to FHIR resources based on the defined mappings.
    
    Args:
        data_df: pandas DataFrame containing the source data
    
    Returns:
        dict containing FHIR resources
    \"\"\"
    fhir_resources = {}
    
"""
    
    # Generate code for each resource type
    for resource_name, fields in mappings.items():
        code += f"    # Create {resource_name} resources\n"
        code += f"    {resource_name.lower()}_resources = []\n"
        code += f"    \n"
        code += f"    # Process each row in the DataFrame\n"
        code += f"    for index, row in data_df.iterrows():\n"
        code += f"        resource = {{\n"
        code += f"            'resourceType': '{resource_name}',\n"
        
        # Add fields mapping
        for fhir_field, mapping_info in fields.items():
            column = mapping_info['column']
            
            # Handle different field types appropriately
            if "Date" in fhir_field or "Time" in fhir_field:
                code += f"            '{fhir_field}': format_date(row['{column}']),\n"
            elif fhir_field == "identifier":
                code += f"            '{fhir_field}': [{{'system': 'https://example.org/identifiers', 'value': str(row['{column}'])}}],\n"
            elif fhir_field == "name":
                code += f"            '{fhir_field}': [{{'text': str(row['{column}'])}}],\n"
            elif fhir_field == "telecom":
                code += f"            '{fhir_field}': [get_telecom_contact(row['{column}'])],\n"
            elif fhir_field == "address":
                code += f"            '{fhir_field}': [{{'text': str(row['{column}'])}}],\n"
            elif fhir_field == "gender":
                code += f"            '{fhir_field}': map_gender(row['{column}']),\n"
            elif "Code" in fhir_field or fhir_field == "code":
                code += f"            '{fhir_field}': {{'coding': [{{'code': str(row['{column}']), 'system': 'http://example.org/coding'}}]}},\n"
            else:
                code += f"            '{fhir_field}': str(row['{column}']),\n"
        
        code += f"        }}\n"
        code += f"        {resource_name.lower()}_resources.append(resource)\n"
        code += f"    \n"
        code += f"    fhir_resources['{resource_name}'] = {resource_name.lower()}_resources\n"
        code += f"    \n"
    
    # Add helper functions
    code += """
    return fhir_resources

def format_date(date_value):
    """
    code += """
    Format a date value to FHIR date format (YYYY-MM-DD).
    
    Args:
        date_value: The date value to format
    
    Returns:
        str containing the formatted date
    """
    code += """
    if pd.isna(date_value):
        return None
    
    try:
        if isinstance(date_value, str):
            # Try to parse the string as a date
            date_obj = pd.to_datetime(date_value)
            return date_obj.strftime('%Y-%m-%d')
        elif isinstance(date_value, (pd.Timestamp, datetime)):
            return date_value.strftime('%Y-%m-%d')
        else:
            return str(date_value)
    except:
        return str(date_value)

def map_gender(gender_value):
    """
    code += """
    Map gender values to FHIR-compliant values.
    
    Args:
        gender_value: The gender value to map
    
    Returns:
        str containing mapped gender value
    """
    code += """
    if pd.isna(gender_value):
        return 'unknown'
    
    gender_str = str(gender_value).lower().strip()
    
    if gender_str in ['m', 'male']:
        return 'male'
    elif gender_str in ['f', 'female']:
        return 'female'
    elif gender_str in ['o', 'other']:
        return 'other'
    else:
        return 'unknown'

def get_telecom_contact(contact_value):
    """
    code += """
    Format a contact value to FHIR telecom format.
    
    Args:
        contact_value: The contact value to format
    
    Returns:
        dict containing the formatted telecom contact
    """
    code += """
    if pd.isna(contact_value):
        return None
    
    contact_str = str(contact_value).strip()
    
    # Determine if it's an email or phone
    if '@' in contact_str:
        return {
            'system': 'email',
            'value': contact_str
        }
    elif any(c.isdigit() for c in contact_str):
        return {
            'system': 'phone',
            'value': contact_str
        }
    else:
        return {
            'system': 'other',
            'value': contact_str
        }

def save_fhir_resources(fhir_resources, output_file):
    """
    code += """
    Save FHIR resources to a JSON file.
    
    Args:
        fhir_resources: Dict containing FHIR resources
        output_file: Path to the output file
    """
    code += """
    with open(output_file, 'w') as f:
        json.dump(fhir_resources, f, indent=2)

# Example usage
# df = pd.read_csv('your_data_file.csv')
# fhir_data = transform_data_to_fhir(df)
# save_fhir_resources(fhir_data, 'fhir_output.json')
"""
    
    return code
