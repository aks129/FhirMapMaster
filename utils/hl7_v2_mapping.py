import re
import json
import pandas as pd
import streamlit as st

# Define HL7 v2 segment structure for common segments
HL7_V2_SEGMENTS = {
    # Patient Information
    "PID": {
        "description": "Patient Identification",
        "fields": {
            "PID-3": {"name": "Patient Identifier List", "description": "Patient's unique identifiers"},
            "PID-5": {"name": "Patient Name", "description": "Patient's full name"},
            "PID-7": {"name": "Date/Time of Birth", "description": "Patient's date of birth"},
            "PID-8": {"name": "Administrative Sex", "description": "Patient's gender/sex"},
            "PID-11": {"name": "Patient Address", "description": "Patient's address information"},
            "PID-13": {"name": "Phone Number - Home", "description": "Patient's home phone number"},
            "PID-18": {"name": "Patient Account Number", "description": "Patient's account number in system"}
        }
    },
    # Visit Information
    "PV1": {
        "description": "Patient Visit",
        "fields": {
            "PV1-2": {"name": "Patient Class", "description": "Patient's class (e.g., inpatient, outpatient)"},
            "PV1-3": {"name": "Assigned Patient Location", "description": "Patient's location in facility"},
            "PV1-7": {"name": "Attending Doctor", "description": "ID of doctor responsible for patient"},
            "PV1-8": {"name": "Referring Doctor", "description": "ID of referring doctor"},
            "PV1-10": {"name": "Hospital Service", "description": "Service patient is assigned to"},
            "PV1-19": {"name": "Visit Number", "description": "Visit/encounter identifier"},
            "PV1-44": {"name": "Admit Date/Time", "description": "Date and time of admission"}
        }
    },
    # Order Information
    "ORC": {
        "description": "Common Order",
        "fields": {
            "ORC-1": {"name": "Order Control", "description": "Order control code (e.g., NW for new order)"},
            "ORC-2": {"name": "Placer Order Number", "description": "Order number assigned by placer"},
            "ORC-3": {"name": "Filler Order Number", "description": "Order number assigned by filler"},
            "ORC-9": {"name": "Date/Time of Transaction", "description": "When transaction occurred"},
            "ORC-12": {"name": "Ordering Provider", "description": "Provider who ordered the service"}
        }
    },
    # Observation/Result Information
    "OBX": {
        "description": "Observation/Result",
        "fields": {
            "OBX-2": {"name": "Value Type", "description": "Type of data in the observation (e.g., NM, ST)"},
            "OBX-3": {"name": "Observation Identifier", "description": "Identifies the observation/test performed"},
            "OBX-5": {"name": "Observation Value", "description": "Value of the observation/result"},
            "OBX-6": {"name": "Units", "description": "Units for the observation value"},
            "OBX-7": {"name": "References Range", "description": "Normal or reference range"},
            "OBX-8": {"name": "Abnormal Flags", "description": "Indicates if result is normal, high, low, etc."},
            "OBX-14": {"name": "Date/Time of the Observation", "description": "When observation was made"}
        }
    },
    # Diagnosis Information
    "DG1": {
        "description": "Diagnosis",
        "fields": {
            "DG1-3": {"name": "Diagnosis Code", "description": "Diagnosis code (e.g., ICD-10)"},
            "DG1-4": {"name": "Diagnosis Description", "description": "Description of the diagnosis"},
            "DG1-6": {"name": "Diagnosis Type", "description": "Type of diagnosis (e.g., admitting, final)"},
            "DG1-19": {"name": "Diagnosis Date/Time", "description": "When diagnosis was made"}
        }
    },
    # Allergy Information
    "AL1": {
        "description": "Patient Allergy Information",
        "fields": {
            "AL1-2": {"name": "Allergen Type Code", "description": "Type of allergen (e.g., drug, food)"},
            "AL1-3": {"name": "Allergen Code/Mnemonic/Description", "description": "Specific allergen"},
            "AL1-4": {"name": "Allergy Severity Code", "description": "Severity of allergic reaction"},
            "AL1-5": {"name": "Allergy Reaction Code", "description": "Type of allergic reaction"}
        }
    },
    # Insurance Information
    "IN1": {
        "description": "Insurance",
        "fields": {
            "IN1-2": {"name": "Insurance Plan ID", "description": "Identifier for the insurance plan"},
            "IN1-3": {"name": "Insurance Company ID", "description": "Identifier for the insurance company"},
            "IN1-4": {"name": "Insurance Company Name", "description": "Name of the insurance company"},
            "IN1-16": {"name": "Name of Insured", "description": "Name of the insured person"},
            "IN1-18": {"name": "Insured's Date of Birth", "description": "DOB of the insured person"},
            "IN1-19": {"name": "Insured's Address", "description": "Address of the insured person"},
            "IN1-49": {"name": "Insurance Type Code", "description": "Type of insurance (e.g., primary, secondary)"}
        }
    }
}

def get_hl7_v2_structure():
    """
    Get the HL7 v2 segment and field structure.
    
    Returns:
        dict: HL7 v2 segments and fields
    """
    return HL7_V2_SEGMENTS

def suggest_hl7_v2_mappings(df):
    """
    Suggest mappings from DataFrame columns to HL7 v2 fields.
    
    Args:
        df: DataFrame containing the data to map
    
    Returns:
        dict: Suggested mappings between columns and HL7 v2 fields
    """
    mappings = {}
    
    # Function to calculate similarity between column name and HL7 field
    def calculate_similarity(column_name, segment, field_id, field_info):
        column_lower = column_name.lower()
        field_name_lower = field_info['name'].lower()
        field_desc_lower = field_info['description'].lower()
        
        # Direct match with field name
        if field_name_lower in column_lower or column_lower in field_name_lower:
            return 0.8
        
        # Check for specific patterns
        if 'patient' in column_lower and 'patient' in field_name_lower:
            return 0.7
        if 'date' in column_lower and 'date' in field_name_lower:
            return 0.6
        if 'id' in column_lower and ('identifier' in field_name_lower or 'number' in field_name_lower):
            return 0.6
        if 'name' in column_lower and 'name' in field_name_lower:
            return 0.7
        if 'address' in column_lower and 'address' in field_name_lower:
            return 0.7
        if 'phone' in column_lower and 'phone' in field_name_lower:
            return 0.7
        if 'gender' in column_lower and 'sex' in field_name_lower:
            return 0.7
        if 'birth' in column_lower and 'birth' in field_name_lower:
            return 0.7
        if 'provider' in column_lower and 'provider' in field_name_lower:
            return 0.7
        if 'diagnosis' in column_lower and 'diagnosis' in field_name_lower:
            return 0.7
        if 'insurance' in column_lower and 'insurance' in field_name_lower:
            return 0.7
        
        # Match against description
        if any(word in field_desc_lower for word in column_lower.split('_')):
            return 0.5
        
        # Low match
        return 0.1
    
    # Check each column against HL7 v2 fields
    for column in df.columns:
        best_field = None
        best_segment = None
        best_field_id = None
        best_score = 0.3  # Minimum threshold
        
        for segment, segment_info in HL7_V2_SEGMENTS.items():
            for field_id, field_info in segment_info['fields'].items():
                similarity = calculate_similarity(column, segment, field_id, field_info)
                
                if similarity > best_score:
                    best_score = similarity
                    best_segment = segment
                    best_field_id = field_id
                    best_field = field_info['name']
        
        if best_field is not None:
            if best_segment not in mappings:
                mappings[best_segment] = {}
            
            mappings[best_segment][best_field_id] = {
                'column': column,
                'confidence': best_score,
                'field_name': best_field
            }
    
    return mappings

def generate_hl7_v2_code(mappings):
    """
    Generate Python code to transform data to HL7 v2 format.
    
    Args:
        mappings: Dictionary containing mappings between columns and HL7 v2 fields
    
    Returns:
        str: Python code for HL7 v2 transformation
    """
    code = """
import pandas as pd
import hl7
from datetime import datetime

def transform_data_to_hl7_v2(data_df):
    \"\"\"
    Transform source data to HL7 v2 messages.
    
    Args:
        data_df: pandas DataFrame containing the source data
    
    Returns:
        list: HL7 v2 messages for each row in the DataFrame
    \"\"\"
    hl7_messages = []
    
    for idx, row in data_df.iterrows():
        # Create MSH segment (Message Header)
        msh = ['MSH', '|', '^~\\&', 'SENDING_APP', 'SENDING_FACILITY', 
               'RECEIVING_APP', 'RECEIVING_FACILITY', 
               get_formatted_datetime(), '', 'ADT^A01', f'MSG{idx}', 'P', '2.5']
        
        # Create segments based on mappings
"""
    
    # Add code for each mapped segment
    for segment, fields in mappings.items():
        code += f"\n        # Create {segment} segment - {HL7_V2_SEGMENTS[segment]['description']}\n"
        code += f"        {segment.lower()} = ['{segment}']\n"
        
        # For each field, add the corresponding mapping code
        max_field_index = max([int(field_id.split('-')[1]) for field_id in fields.keys()])
        
        code += f"        # Pad segment with empty fields up to max field index ({max_field_index})\n"
        code += f"        {segment.lower()}.extend([''] * {max_field_index})\n\n"
        
        # Now set the specific fields that we have mappings for
        for field_id, mapping in fields.items():
            field_index = int(field_id.split('-')[1])
            column = mapping['column']
            field_name = mapping['field_name']
            
            code += f"        # Map {field_name}\n"
            code += f"        if '{column}' in row and not pd.isna(row['{column}']):\n"
            code += f"            {segment.lower()}[{field_index}] = str(row['{column}'])\n\n"
        
        # Add segment to the message
        code += f"        # Add {segment} segment to message\n"
        code += f"        message_segments.append({segment.lower()})\n\n"
    
    # Add helper code for message construction
    code += """
        # Construct the complete HL7 message
        message = hl7.Message('\\r'.join(['|'.join(seg) for seg in message_segments]))
        hl7_messages.append(str(message))
    
    return hl7_messages

def get_formatted_datetime():
    \"\"\"
    Get current datetime in HL7 format.
    
    Returns:
        str: Formatted datetime string
    \"\"\"
    return datetime.now().strftime('%Y%m%d%H%M%S')

def save_hl7_v2_messages(messages, file_path):
    \"\"\"
    Save HL7 v2 messages to a file.
    
    Args:
        messages: List of HL7 v2 message strings
        file_path: Path to save the messages
    \"\"\"
    with open(file_path, 'w') as f:
        for message in messages:
            f.write(message + '\\n\\n')

# Example usage
# if __name__ == "__main__":
#     df = pd.read_csv('your_data_file.csv')
#     hl7_messages = transform_data_to_hl7_v2(df)
#     save_hl7_v2_messages(hl7_messages, 'hl7_output.txt')
"""
    
    return code

def generate_hl7_v2_samples(mappings, df, num_samples=2):
    """
    Generate sample HL7 v2 messages based on the mappings and actual data.
    
    Args:
        mappings: Dictionary containing mappings between columns and HL7 v2 fields
        df: DataFrame containing the data
        num_samples: Number of sample messages to generate
    
    Returns:
        list: Sample HL7 v2 messages
    """
    samples = []
    
    # Get a subset of rows to generate samples
    sample_rows = df.head(min(num_samples, len(df)))
    
    for idx, row in sample_rows.iterrows():
        # Create message segments
        message_segments = []
        
        # Create MSH segment (Message Header)
        msh = ['MSH', '|', '^~\\&', 'SENDING_APP', 'SENDING_FACILITY', 
               'RECEIVING_APP', 'RECEIVING_FACILITY', 
               pd.Timestamp.now().strftime('%Y%m%d%H%M%S'), 
               '', 'ADT^A01', f'MSG{idx}', 'P', '2.5']
        message_segments.append(msh)
        
        # Create segments based on mappings
        for segment, fields in mappings.items():
            segment_data = [segment]
            
            # Determine max field index in this segment
            max_field_index = max([int(field_id.split('-')[1]) for field_id in fields.keys()])
            
            # Pad with empty fields
            segment_data.extend([''] * max_field_index)
            
            # Fill in mapped fields
            for field_id, mapping in fields.items():
                field_index = int(field_id.split('-')[1])
                column = mapping['column']
                
                if column in row and not pd.isna(row[column]):
                    segment_data[field_index] = str(row[column])
            
            message_segments.append(segment_data)
        
        # Construct complete message
        message = '\r'.join(['|'.join(str(field) for field in seg) for seg in message_segments])
        samples.append(message)
    
    return samples