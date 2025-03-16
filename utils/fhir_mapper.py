import pandas as pd
import numpy as np
import streamlit as st
import json
import re

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
    'MedicationStatement': {
        'description': 'A record of a medication that is being consumed by a patient',
        'fields': {
            'id': 'Logical id of this artifact',
            'identifier': 'Business identifier',
            'status': 'active | completed | entered-in-error | intended | stopped | on-hold | unknown | not-taken',
            'medication': 'What medication was taken',
            'subject': 'Reference to the patient',
            'effectiveDateTime': 'The date/time or interval when the medication was taken',
            'effectivePeriod': 'The date/time or interval when the medication was taken',
            'dateAsserted': 'When the statement was asserted?',
            'dosage': 'Details of how medication was taken'
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

def get_fhir_resources(standard):
    """
    Get FHIR resource definitions based on the selected standard.
    
    Args:
        standard: The FHIR standard to use (US Core or CARIN BB)
    
    Returns:
        dict containing resource definitions
    """
    if "US Core" in standard:
        return US_CORE_RESOURCES
    elif "CARIN BB" in standard:
        return CARIN_BB_RESOURCES
    else:
        return {}

def suggest_mappings(df, standard):
    """
    Suggest mappings from the dataframe columns to FHIR resources.
    
    Args:
        df: pandas DataFrame containing the data
        standard: The FHIR standard to use (US Core or CARIN BB)
    
    Returns:
        dict containing suggested mappings and confidence scores
    """
    resources = get_fhir_resources(standard)
    mappings = {}
    
    # Function to calculate similarity score between column name and FHIR field
    def calculate_similarity(column_name, fhir_field):
        column_name = column_name.lower()
        fhir_field = fhir_field.lower()
        
        # Direct match
        if column_name == fhir_field:
            return 1.0
        
        # Contains match
        if column_name in fhir_field or fhir_field in column_name:
            return 0.8
        
        # Check for common prefixes/suffixes and abbreviations
        column_parts = re.split(r'[_\s\-]', column_name)
        fhir_parts = re.split(r'[_\s\-]', fhir_field)
        
        # Check for parts match
        common_parts = set(column_parts).intersection(set(fhir_parts))
        if common_parts:
            return 0.5 + (0.3 * (len(common_parts) / max(len(column_parts), len(fhir_parts))))
        
        # Low confidence for potential matches
        for col_part in column_parts:
            for fhir_part in fhir_parts:
                if (col_part in fhir_part or fhir_part in col_part) and len(col_part) > 2 and len(fhir_part) > 2:
                    return 0.4
        
        return 0.0  # No obvious connection
    
    # Define commonly expected data patterns for different FHIR fields
    data_patterns = {
        'birthDate': lambda s: pd.api.types.is_datetime64_any_dtype(s) or (isinstance(s, pd.Series) and s.astype(str).str.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$').any()),
        'gender': lambda s: (isinstance(s, pd.Series) and s.astype(str).str.lower().isin(['male', 'female', 'm', 'f', 'other', 'unknown']).any()),
        'telecom': lambda s: (isinstance(s, pd.Series) and (s.astype(str).str.contains(r'@').any() or s.astype(str).str.contains(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}').any())),
        'address': lambda s: (isinstance(s, pd.Series) and s.astype(str).str.contains(r'\d+\s+\w+\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd)', case=False).any()),
        'identifier': lambda s: df[s].nunique() > 0.8 * len(df) if len(df) > 10 else False
    }

    for column in df.columns:
        best_resource = None
        best_field = None
        best_score = 0.0
        
        for resource_name, resource in resources.items():
            for field, description in resource['fields'].items():
                # Calculate basic name similarity
                similarity = calculate_similarity(column, field)
                
                # Check for data pattern matches to boost confidence
                if field in data_patterns and data_patterns[field](df[column]):
                    similarity += 0.3
                
                # Check for data type compatibility
                if field in ['birthDate', 'effectiveDateTime', 'performedDateTime'] and pd.api.types.is_datetime64_any_dtype(df[column]):
                    similarity += 0.2
                
                if similarity > best_score:
                    best_score = similarity
                    best_resource = resource_name
                    best_field = field
        
        if best_score > 0.3:  # Only include matches with reasonable confidence
            if best_resource not in mappings:
                mappings[best_resource] = {}
            
            mappings[best_resource][best_field] = {
                'column': column,
                'confidence': round(best_score, 2)
            }
    
    return mappings

def generate_fhir_structure(mappings, standard):
    """
    Generate a FHIR resource structure based on the mappings.
    
    Args:
        mappings: Dict containing the mappings from columns to FHIR fields
        standard: The FHIR standard used
    
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

def generate_python_mapping_code(mappings, standard, df):
    """
    Generate Python code for mapping data to FHIR format.
    
    Args:
        mappings: Dict containing the mappings from columns to FHIR fields
        standard: The FHIR standard used
        df: The original dataframe
    
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
