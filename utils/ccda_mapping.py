import re
import json
import pandas as pd
import streamlit as st

# Define C-CDA document structure and sections
CCDA_SECTIONS = {
    "Header": {
        "description": "Clinical Document Header",
        "fields": {
            "recordTarget": {"name": "Record Target", "description": "The patient the document is about"},
            "patientRole/id": {"name": "Patient ID", "description": "Patient identifier"},
            "patientRole/addr": {"name": "Patient Address", "description": "Patient address information"},
            "patientRole/telecom": {"name": "Patient Telecom", "description": "Patient contact information"},
            "patientRole/patient/name": {"name": "Patient Name", "description": "Patient's full name"},
            "patientRole/patient/administrativeGenderCode": {"name": "Gender", "description": "Patient's gender"},
            "patientRole/patient/birthTime": {"name": "Birth Time", "description": "Patient's date of birth"},
            "patientRole/patient/raceCode": {"name": "Race", "description": "Patient's race"},
            "patientRole/patient/ethnicGroupCode": {"name": "Ethnicity", "description": "Patient's ethnicity"},
            "patientRole/patient/languageCommunication": {"name": "Language", "description": "Patient's language"},
            "author/time": {"name": "Author Time", "description": "When the document was authored"},
            "author/assignedAuthor/id": {"name": "Author ID", "description": "Identifier of document author"},
            "author/assignedAuthor/assignedPerson/name": {"name": "Author Name", "description": "Name of document author"},
            "custodian/assignedCustodian/representedCustodianOrganization/name": {"name": "Custodian Organization", "description": "Organization maintaining the document"}
        }
    },
    "Problems": {
        "description": "Problem List Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.5.1",
        "fields": {
            "problem/effectiveTime/low": {"name": "Problem Onset", "description": "When the problem started"},
            "problem/effectiveTime/high": {"name": "Problem Resolved", "description": "When the problem was resolved"},
            "problem/value": {"name": "Problem Code", "description": "Problem code (e.g., ICD-10)"},
            "problem/code/translation": {"name": "Problem Code Translation", "description": "Alternative coding for problem"},
            "problem/text": {"name": "Problem Text", "description": "Textual description of problem"},
            "problem/statusCode": {"name": "Problem Status", "description": "Status of the problem (active, resolved, etc.)"}
        }
    },
    "Medications": {
        "description": "Medications Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.1.1",
        "fields": {
            "medication/effectiveTime/low": {"name": "Medication Start", "description": "When medication was started"},
            "medication/effectiveTime/high": {"name": "Medication End", "description": "When medication was stopped"},
            "medication/manufacturedProduct/manufacturedMaterial/code": {"name": "Medication Code", "description": "Code identifying the medication"},
            "medication/manufacturedProduct/manufacturedMaterial/name": {"name": "Medication Name", "description": "Name of the medication"},
            "medication/doseQuantity": {"name": "Dose Quantity", "description": "Amount of medication per dose"},
            "medication/rateQuantity": {"name": "Rate Quantity", "description": "Rate of medication administration"},
            "medication/routeCode": {"name": "Route", "description": "Route of administration"},
            "medication/statusCode": {"name": "Medication Status", "description": "Status of the medication (active, completed, etc.)"}
        }
    },
    "Allergies": {
        "description": "Allergies Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.6.1",
        "fields": {
            "allergy/effectiveTime/low": {"name": "Allergy Onset", "description": "When the allergy was first observed"},
            "allergy/participant/participantRole/playingEntity/code": {"name": "Allergen Code", "description": "Code identifying the allergen"},
            "allergy/participant/participantRole/playingEntity/name": {"name": "Allergen Name", "description": "Name of the allergen"},
            "allergy/code": {"name": "Allergy Type", "description": "Type of allergy (drug, food, etc.)"},
            "allergy/statusCode": {"name": "Allergy Status", "description": "Status of the allergy (active, resolved, etc.)"},
            "allergy/entryRelationship/observation/value": {"name": "Reaction", "description": "Reaction to the allergen"}
        }
    },
    "Results": {
        "description": "Results Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.3.1",
        "fields": {
            "result/effectiveTime": {"name": "Result Time", "description": "When the observation was made"},
            "result/code": {"name": "Result Code", "description": "Code identifying the observation"},
            "result/text": {"name": "Result Name", "description": "Name of the observation"},
            "result/value": {"name": "Result Value", "description": "Value of the observation"},
            "result/interpretationCode": {"name": "Result Interpretation", "description": "Interpretation of the result (high, low, normal)"},
            "result/referenceRange": {"name": "Reference Range", "description": "Reference range for the result"}
        }
    },
    "Procedures": {
        "description": "Procedures Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.7.1",
        "fields": {
            "procedure/effectiveTime": {"name": "Procedure Time", "description": "When the procedure was performed"},
            "procedure/code": {"name": "Procedure Code", "description": "Code identifying the procedure"},
            "procedure/text": {"name": "Procedure Name", "description": "Name of the procedure"},
            "procedure/statusCode": {"name": "Procedure Status", "description": "Status of the procedure (completed, aborted, etc.)"},
            "procedure/targetSiteCode": {"name": "Procedure Target Site", "description": "Anatomical site of the procedure"}
        }
    },
    "Encounters": {
        "description": "Encounters Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.22.1",
        "fields": {
            "encounter/effectiveTime/low": {"name": "Encounter Start", "description": "When the encounter started"},
            "encounter/effectiveTime/high": {"name": "Encounter End", "description": "When the encounter ended"},
            "encounter/code": {"name": "Encounter Type", "description": "Type of encounter"},
            "encounter/text": {"name": "Encounter Description", "description": "Description of the encounter"},
            "encounter/performer/assignedEntity/id": {"name": "Provider ID", "description": "ID of the provider for this encounter"},
            "encounter/performer/assignedEntity/assignedPerson/name": {"name": "Provider Name", "description": "Name of the provider"}
        }
    },
    "VitalSigns": {
        "description": "Vital Signs Section",
        "templateId": "2.16.840.1.113883.10.20.22.2.4.1",
        "fields": {
            "vitalSign/effectiveTime": {"name": "Vital Sign Time", "description": "When the vital sign was recorded"},
            "vitalSign/code": {"name": "Vital Sign Code", "description": "Code identifying the vital sign"},
            "vitalSign/text": {"name": "Vital Sign Name", "description": "Name of the vital sign"},
            "vitalSign/value": {"name": "Vital Sign Value", "description": "Value of the vital sign"},
            "vitalSign/interpretationCode": {"name": "Vital Sign Interpretation", "description": "Interpretation of the vital sign"}
        }
    }
}

def get_ccda_structure():
    """
    Get the C-CDA document structure with sections and fields.
    
    Returns:
        dict: C-CDA sections and fields
    """
    return CCDA_SECTIONS

def suggest_ccda_mappings(df):
    """
    Suggest mappings from DataFrame columns to C-CDA elements.
    
    Args:
        df: DataFrame containing the data to map
    
    Returns:
        dict: Suggested mappings between columns and C-CDA elements
    """
    mappings = {}
    
    # Function to calculate similarity between column name and C-CDA element
    def calculate_similarity(column_name, section, field_path, field_info):
        column_lower = column_name.lower()
        field_name_lower = field_info['name'].lower()
        field_desc_lower = field_info['description'].lower()
        
        # Direct match with field name
        if field_name_lower in column_lower or column_lower in field_name_lower:
            return 0.8
        
        # Match specific patterns common in healthcare data
        if 'patient' in column_lower and 'patient' in field_name_lower:
            return 0.7
        if 'birth' in column_lower and 'birth' in field_name_lower:
            return 0.7
        if 'gender' in column_lower and 'gender' in field_name_lower:
            return 0.7
        if 'address' in column_lower and 'address' in field_name_lower:
            return 0.7
        if 'name' in column_lower and 'name' in field_name_lower:
            return 0.7
        if 'id' in column_lower and 'id' in field_name_lower:
            return 0.6
        if 'code' in column_lower and 'code' in field_name_lower:
            return 0.6
        if 'time' in column_lower and ('time' in field_name_lower or 'date' in field_name_lower):
            return 0.6
        if 'provider' in column_lower and 'provider' in field_name_lower:
            return 0.7
        
        # Match by section specific terms
        if section.lower() == 'problems' and ('problem' in column_lower or 'diagnosis' in column_lower or 'condition' in column_lower):
            return 0.7
        if section.lower() == 'medications' and ('medication' in column_lower or 'med' in column_lower or 'drug' in column_lower):
            return 0.7
        if section.lower() == 'allergies' and ('allergy' in column_lower or 'allergic' in column_lower):
            return 0.7
        if section.lower() == 'results' and ('result' in column_lower or 'lab' in column_lower or 'test' in column_lower):
            return 0.7
        if section.lower() == 'procedures' and ('procedure' in column_lower or 'surgery' in column_lower):
            return 0.7
        if section.lower() == 'encounters' and ('encounter' in column_lower or 'visit' in column_lower):
            return 0.7
        if section.lower() == 'vitalsigns' and ('vital' in column_lower or 'bp' in column_lower or 'heart rate' in column_lower):
            return 0.7
        
        # Match against description
        if any(word in field_desc_lower for word in column_lower.split('_')):
            return 0.5
        
        # Low match
        return 0.1
    
    # Check each column against C-CDA fields
    for column in df.columns:
        best_section = None
        best_field_path = None
        best_field_name = None
        best_score = 0.3  # Minimum threshold
        
        for section, section_info in CCDA_SECTIONS.items():
            for field_path, field_info in section_info['fields'].items():
                similarity = calculate_similarity(column, section, field_path, field_info)
                
                if similarity > best_score:
                    best_score = similarity
                    best_section = section
                    best_field_path = field_path
                    best_field_name = field_info['name']
        
        if best_section is not None:
            if best_section not in mappings:
                mappings[best_section] = {}
            
            mappings[best_section][best_field_path] = {
                'column': column,
                'confidence': best_score,
                'field_name': best_field_name
            }
    
    return mappings

def generate_ccda_template_code(mappings):
    """
    Generate code for creating a C-CDA document from mapped data.
    
    Args:
        mappings: Dictionary containing mappings between columns and C-CDA elements
    
    Returns:
        str: Python code for C-CDA document generation
    """
    code = """
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

def transform_data_to_ccda(data_df):
    \"\"\"
    Transform source data to C-CDA XML documents.
    
    Args:
        data_df: pandas DataFrame containing the source data
    
    Returns:
        list: C-CDA XML documents for each patient in the DataFrame
    \"\"\"
    # Group data by patient
    patient_groups = data_df.groupby('patient_id') if 'patient_id' in data_df.columns else [('single_patient', data_df)]
    
    ccda_documents = []
    
    for patient_id, patient_data in patient_groups:
        # Create CDA root element
        root = ET.Element('ClinicalDocument')
        root.set('xmlns', 'urn:hl7-org:v3')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        
        # Add type ID
        type_id = ET.SubElement(root, 'typeId')
        type_id.set('root', '2.16.840.1.113883.1.3')
        type_id.set('extension', 'POCD_HD000040')
        
        # Add document template ID for CCD
        template_id = ET.SubElement(root, 'templateId')
        template_id.set('root', '2.16.840.1.113883.10.20.22.1.2')  # CCD template
        template_id.set('extension', '2015-08-01')
        
        # Add document ID
        id_elem = ET.SubElement(root, 'id')
        id_elem.set('root', str(uuid.uuid4()))
        
        # Add document code
        code_elem = ET.SubElement(root, 'code')
        code_elem.set('code', '34133-9')
        code_elem.set('displayName', 'Summarization of Episode Note')
        code_elem.set('codeSystem', '2.16.840.1.113883.6.1')
        code_elem.set('codeSystemName', 'LOINC')
        
        # Add document title
        title = ET.SubElement(root, 'title')
        title.text = 'Continuity of Care Document'
        
        # Add effective time (document creation time)
        effective_time = ET.SubElement(root, 'effectiveTime')
        effective_time.set('value', datetime.now().strftime('%Y%m%d%H%M%S'))
        
        # Add confidentiality code
        conf_code = ET.SubElement(root, 'confidentialityCode')
        conf_code.set('code', 'N')
        conf_code.set('displayName', 'Normal')
        conf_code.set('codeSystem', '2.16.840.1.113883.5.25')
        conf_code.set('codeSystemName', 'Confidentiality')
        
        # Add language code
        language_code = ET.SubElement(root, 'languageCode')
        language_code.set('code', 'en-US')
        
        # Get a sample row for patient-level information
        sample_row = patient_data.iloc[0] if len(patient_data) > 0 else None
        
        if sample_row is not None:
"""
    
    # Add patient information based on mappings
    if 'Header' in mappings:
        code += "            # Add patient information\n"
        code += "            record_target = ET.SubElement(root, 'recordTarget')\n"
        code += "            patient_role = ET.SubElement(record_target, 'patientRole')\n"
        
        for field_path, mapping in mappings['Header'].items():
            column = mapping['column']
            field_name = mapping['field_name']
            
            if 'patientRole/id' in field_path:
                code += f"""
            # Map {field_name}
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                id_elem = ET.SubElement(patient_role, 'id')
                id_elem.set('root', '2.16.840.1.113883.4.1')  # OID for SSN
                id_elem.set('extension', str(sample_row['{column}']))
"""
            elif 'patientRole/addr' in field_path:
                code += f"""
            # Map {field_name}
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                addr = ET.SubElement(patient_role, 'addr')
                addr.set('use', 'HP')  # Home permanent
                addr_parts = str(sample_row['{column}']).split(',')
                if len(addr_parts) >= 1:
                    streetAddressLine = ET.SubElement(addr, 'streetAddressLine')
                    streetAddressLine.text = addr_parts[0].strip()
                if len(addr_parts) >= 2:
                    city = ET.SubElement(addr, 'city')
                    city.text = addr_parts[1].strip()
                if len(addr_parts) >= 3:
                    state = ET.SubElement(addr, 'state')
                    state.text = addr_parts[2].strip()
                if len(addr_parts) >= 4:
                    postalCode = ET.SubElement(addr, 'postalCode')
                    postalCode.text = addr_parts[3].strip()
"""
            elif 'patientRole/telecom' in field_path:
                code += f"""
            # Map {field_name}
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                telecom = ET.SubElement(patient_role, 'telecom')
                telecom_value = str(sample_row['{column}'])
                if '@' in telecom_value:
                    telecom.set('value', f'mailto:{{telecom_value}}')
                else:
                    telecom.set('value', f'tel:{{telecom_value}}')
"""
            elif 'patientRole/patient/name' in field_path:
                code += f"""
            # Map {field_name}
            patient = ET.SubElement(patient_role, 'patient')
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                name = ET.SubElement(patient, 'name')
                name_parts = str(sample_row['{column}']).split()
                if len(name_parts) >= 2:
                    given = ET.SubElement(name, 'given')
                    given.text = name_parts[0]
                    family = ET.SubElement(name, 'family')
                    family.text = name_parts[-1]
                else:
                    given = ET.SubElement(name, 'given')
                    given.text = str(sample_row['{column}'])
"""
            elif 'patientRole/patient/administrativeGenderCode' in field_path:
                code += f"""
            # Map {field_name}
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                gender_code = ET.SubElement(patient, 'administrativeGenderCode')
                gender_value = str(sample_row['{column}']).lower()
                if gender_value in ['m', 'male']:
                    gender_code.set('code', 'M')
                    gender_code.set('displayName', 'Male')
                elif gender_value in ['f', 'female']:
                    gender_code.set('code', 'F')
                    gender_code.set('displayName', 'Female')
                else:
                    gender_code.set('code', 'UN')
                    gender_code.set('displayName', 'Undifferentiated')
                gender_code.set('codeSystem', '2.16.840.1.113883.5.1')
                gender_code.set('codeSystemName', 'HL7 AdministrativeGender')
"""
            elif 'patientRole/patient/birthTime' in field_path:
                code += f"""
            # Map {field_name}
            if '{column}' in sample_row and not pd.isna(sample_row['{column}']):
                birth_time = ET.SubElement(patient, 'birthTime')
                try:
                    birth_date = pd.to_datetime(sample_row['{column}'])
                    birth_time.set('value', birth_date.strftime('%Y%m%d'))
                except:
                    birth_time.set('value', str(sample_row['{column}']))
"""
    
    # Add code for author information
    code += """
        # Add author information
        author = ET.SubElement(root, 'author')
        author_time = ET.SubElement(author, 'time')
        author_time.set('value', datetime.now().strftime('%Y%m%d%H%M%S'))
        assigned_author = ET.SubElement(author, 'assignedAuthor')
        author_id = ET.SubElement(assigned_author, 'id')
        author_id.set('root', str(uuid.uuid4()))
"""
    
    # Add custodian information
    code += """
        # Add custodian information
        custodian = ET.SubElement(root, 'custodian')
        assigned_custodian = ET.SubElement(custodian, 'assignedCustodian')
        represented_custodian_org = ET.SubElement(assigned_custodian, 'representedCustodianOrganization')
        custodian_id = ET.SubElement(represented_custodian_org, 'id')
        custodian_id.set('root', str(uuid.uuid4()))
        custodian_name = ET.SubElement(represented_custodian_org, 'name')
        custodian_name.text = 'Parker FHIR Mapper'
"""
    
    # Add document body and sections
    code += """
        # Add document body
        component = ET.SubElement(root, 'component')
        structured_body = ET.SubElement(component, 'structuredBody')
"""
    
    # Add code for each section in mappings
    for section, fields in mappings.items():
        # Skip the header section as it's handled differently
        if section == 'Header':
            continue
            
        code += f"""
        # Add {section} section
        section_component = ET.SubElement(structured_body, 'component')
        section_elem = ET.SubElement(section_component, 'section')
        
        # Add section template ID
        if '{section}' in CCDA_SECTIONS and 'templateId' in CCDA_SECTIONS['{section}']:
            template_id = ET.SubElement(section_elem, 'templateId')
            template_id.set('root', CCDA_SECTIONS['{section}']['templateId'])
        
        # Add section code
        section_code = ET.SubElement(section_elem, 'code')
        section_code.set('code', get_section_code('{section}'))
        section_code.set('displayName', CCDA_SECTIONS['{section}']['description'])
        section_code.set('codeSystem', '2.16.840.1.113883.6.1')
        section_code.set('codeSystemName', 'LOINC')
        
        # Add section title
        section_title = ET.SubElement(section_elem, 'title')
        section_title.text = CCDA_SECTIONS['{section}']['description']
        
        # Add section text
        section_text = ET.SubElement(section_elem, 'text')
        text_table = ET.SubElement(section_text, 'table')
        text_thead = ET.SubElement(text_table, 'thead')
        text_thead_row = ET.SubElement(text_thead, 'tr')
        
        # Add header columns
        for field_path, mapping in mappings['{section}'].items():
            field_name_th = ET.SubElement(text_thead_row, 'th')
            field_name_th.text = mapping['field_name']
        
        # Add section entries
        section_entry = ET.SubElement(section_elem, 'entry')
"""
        
        # Add specific code for different section types
        if section == 'Problems':
            code += """
        # Process each problem in the patient data
        for idx, row in patient_data.iterrows():
            # Create problem act
            act = ET.SubElement(section_entry, 'act')
            act.set('classCode', 'ACT')
            act.set('moodCode', 'EVN')
            
            # Add template ID for problem act
            template_id = ET.SubElement(act, 'templateId')
            template_id.set('root', '2.16.840.1.113883.10.20.22.4.3')
            template_id.set('extension', '2015-08-01')
            
            # Add act code
            act_code = ET.SubElement(act, 'code')
            act_code.set('code', '11450-4')
            act_code.set('displayName', 'Problem')
            act_code.set('codeSystem', '2.16.840.1.113883.6.1')
            act_code.set('codeSystemName', 'LOINC')
            
            # Add status code
            status_code = ET.SubElement(act, 'statusCode')
            status_code.set('code', 'active')
            
            # Add entry relationship with problem observation
            entry_rel = ET.SubElement(act, 'entryRelationship')
            entry_rel.set('typeCode', 'SUBJ')
            
            # Create observation element for the problem
            obs = ET.SubElement(entry_rel, 'observation')
            obs.set('classCode', 'OBS')
            obs.set('moodCode', 'EVN')
            
"""
            # Add mapping code for problem fields
            for field_path, mapping in fields.items():
                column = mapping['column']
                if 'problem/value' in field_path:
                    code += f"""
            # Map Problem Code
            if '{column}' in row and not pd.isna(row['{column}']):
                value = ET.SubElement(obs, 'value')
                value.set('xsi:type', 'CD')
                value.set('code', str(row['{column}']))
                value.set('displayName', get_problem_display_name(str(row['{column}'])))
                value.set('codeSystem', '2.16.840.1.113883.6.90')  # ICD-10-CM
                value.set('codeSystemName', 'ICD-10-CM')
"""
                elif 'problem/effectiveTime/low' in field_path:
                    code += f"""
            # Map Problem Onset
            effective_time = ET.SubElement(obs, 'effectiveTime')
            if '{column}' in row and not pd.isna(row['{column}']):
                low = ET.SubElement(effective_time, 'low')
                try:
                    onset_date = pd.to_datetime(row['{column}'])
                    low.set('value', onset_date.strftime('%Y%m%d'))
                except:
                    low.set('value', str(row['{column}']))
"""
                elif 'problem/statusCode' in field_path:
                    code += f"""
            # Map Problem Status
            if '{column}' in row and not pd.isna(row['{column}']):
                status_code = ET.SubElement(obs, 'statusCode')
                status_value = str(row['{column}']).lower()
                if 'active' in status_value:
                    status_code.set('code', 'active')
                elif 'resolved' in status_value:
                    status_code.set('code', 'completed')
                else:
                    status_code.set('code', 'active')
"""
    
    # Add helper functions
    code += """
        # Convert the XML document to a string
        from xml.dom import minidom
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        ccda_documents.append(xml_str)
    
    return ccda_documents

def get_section_code(section_name):
    \"\"\"
    Get LOINC code for a C-CDA section.
    
    Args:
        section_name: Name of the section
    
    Returns:
        str: LOINC code for the section
    \"\"\"
    section_codes = {
        'Problems': '11450-4',
        'Medications': '10160-0',
        'Allergies': '48765-2',
        'Results': '30954-2',
        'Procedures': '47519-4',
        'Encounters': '46240-8',
        'VitalSigns': '8716-3'
    }
    
    return section_codes.get(section_name, '55107-7')  # Default to Document Section

def get_problem_display_name(code):
    \"\"\"
    Get display name for a problem code.
    In a real-world scenario, this would use a terminology service.
    
    Args:
        code: Problem code
    
    Returns:
        str: Display name for the code
    \"\"\"
    # This is a simplified version. In a real implementation,
    # you would connect to a terminology service or use a
    # comprehensive mapping.
    return f"Problem: {code}"

def save_ccda_documents(documents, file_path):
    \"\"\"
    Save C-CDA documents to a file.
    
    Args:
        documents: List of C-CDA document strings
        file_path: Path to save the documents
    \"\"\"
    with open(file_path, 'w') as f:
        for i, doc in enumerate(documents):
            f.write(f"--- C-CDA Document {i+1} ---\\n")
            f.write(doc)
            f.write("\\n\\n")

# Example usage
# if __name__ == "__main__":
#     df = pd.read_csv('your_data_file.csv')
#     ccda_documents = transform_data_to_ccda(df)
#     save_ccda_documents(ccda_documents, 'ccda_output.xml')
"""
    
    return code

def generate_ccda_sample(mappings, df, num_samples=1):
    """
    Generate a sample C-CDA document based on the mappings and actual data.
    
    Args:
        mappings: Dictionary containing mappings between columns and C-CDA elements
        df: DataFrame containing the data
        num_samples: Number of sample documents to generate
    
    Returns:
        str: Sample C-CDA document
    """
    import xml.etree.ElementTree as ET
    import uuid
    
    # Get a sample row from the DataFrame
    sample_row = df.head(1).iloc[0] if len(df) > 0 else None
    
    if sample_row is None:
        return "No data available to generate sample C-CDA document."
    
    # Create CDA root element
    root = ET.Element('ClinicalDocument')
    root.set('xmlns', 'urn:hl7-org:v3')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    
    # Add type ID
    type_id = ET.SubElement(root, 'typeId')
    type_id.set('root', '2.16.840.1.113883.1.3')
    type_id.set('extension', 'POCD_HD000040')
    
    # Add document ID
    id_elem = ET.SubElement(root, 'id')
    id_elem.set('root', str(uuid.uuid4()))
    
    # Add document code
    code_elem = ET.SubElement(root, 'code')
    code_elem.set('code', '34133-9')
    code_elem.set('displayName', 'Summarization of Episode Note')
    code_elem.set('codeSystem', '2.16.840.1.113883.6.1')
    code_elem.set('codeSystemName', 'LOINC')
    
    # Add document title
    title = ET.SubElement(root, 'title')
    title.text = 'Continuity of Care Document'
    
    # Add effective time
    effective_time = ET.SubElement(root, 'effectiveTime')
    effective_time.set('value', pd.Timestamp.now().strftime('%Y%m%d%H%M%S'))
    
    # Add patient information if mapped
    if 'Header' in mappings:
        record_target = ET.SubElement(root, 'recordTarget')
        patient_role = ET.SubElement(record_target, 'patientRole')
        
        # Map patient ID
        if any('patientRole/id' in field for field in mappings['Header']):
            for field, mapping in mappings['Header'].items():
                if 'patientRole/id' in field and mapping['column'] in sample_row:
                    id_elem = ET.SubElement(patient_role, 'id')
                    id_elem.set('root', '2.16.840.1.113883.4.1')
                    id_elem.set('extension', str(sample_row[mapping['column']]))
        
        # Create patient element
        patient = ET.SubElement(patient_role, 'patient')
        
        # Map patient name
        if any('patientRole/patient/name' in field for field in mappings['Header']):
            for field, mapping in mappings['Header'].items():
                if 'patientRole/patient/name' in field and mapping['column'] in sample_row:
                    name = ET.SubElement(patient, 'name')
                    name_parts = str(sample_row[mapping['column']]).split()
                    if len(name_parts) >= 2:
                        given = ET.SubElement(name, 'given')
                        given.text = name_parts[0]
                        family = ET.SubElement(name, 'family')
                        family.text = name_parts[-1]
                    else:
                        given = ET.SubElement(name, 'given')
                        given.text = str(sample_row[mapping['column']])
    
    # Create a simplified document body with one section as an example
    component = ET.SubElement(root, 'component')
    structured_body = ET.SubElement(component, 'structuredBody')
    
    # Add one example section
    for section_name in mappings:
        if section_name != 'Header':
            section_component = ET.SubElement(structured_body, 'component')
            section_elem = ET.SubElement(section_component, 'section')
            
            # Add section title
            section_title = ET.SubElement(section_elem, 'title')
            section_title.text = CCDA_SECTIONS[section_name]['description']
            
            # Add a sample entry
            for field, mapping in mappings[section_name].items():
                if mapping['column'] in sample_row:
                    entry = ET.SubElement(section_elem, 'entry')
                    observation = ET.SubElement(entry, 'observation')
                    observation.set('classCode', 'OBS')
                    observation.set('moodCode', 'EVN')
                    
                    # Add a code for the observation
                    code = ET.SubElement(observation, 'code')
                    code.set('code', '1234-5')
                    code.set('displayName', mapping['field_name'])
                    
                    # Add the value
                    value = ET.SubElement(observation, 'value')
                    value.set('xsi:type', 'ST')
                    value.text = str(sample_row[mapping['column']])
                    
                    # Only add one sample entry
                    break
            
            # Only add one sample section
            break
    
    # Convert to string and return
    from xml.dom import minidom
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    return xml_str