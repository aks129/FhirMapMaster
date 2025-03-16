"""
Claims Data Mapping Knowledge Base

This module contains comprehensive mappings for claims data to FHIR resources,
with special focus on CARIN BB Implementation Guide.
"""

# Comprehensive mapping of common claims data fields to FHIR resources and fields
CLAIMS_DATA_MAPPINGS = {
    # Claims identification
    "claim_id": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claimid": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claim_number": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claimnumber": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claim_no": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claimno": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "eob_id": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claim_control_number": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "insurance_claim_number": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "clm_id": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "clm_num": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claim_identifier": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "claim": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    "clm": {"resource": "ExplanationOfBenefit", "field": "identifier"},
    
    # Patient/Member information
    "patient_id": {"resource": "Patient", "field": "identifier"},
    "patientid": {"resource": "Patient", "field": "identifier"},
    "member_id": {"resource": "Patient", "field": "identifier"},
    "memberid": {"resource": "Patient", "field": "identifier"},
    "pat_id": {"resource": "Patient", "field": "identifier"},
    "mbr_id": {"resource": "Patient", "field": "identifier"},
    "person_id": {"resource": "Patient", "field": "identifier"},
    "patient_number": {"resource": "Patient", "field": "identifier"},
    "pt_id": {"resource": "Patient", "field": "identifier"},
    "ptid": {"resource": "Patient", "field": "identifier"},
    "subscriber_id": {"resource": "Patient", "field": "identifier"},
    "subscriber_identifier": {"resource": "Patient", "field": "identifier"},
    "patient_first_name": {"resource": "Patient", "field": "name.given"},
    "patient_last_name": {"resource": "Patient", "field": "name.family"},
    "patient_fname": {"resource": "Patient", "field": "name.given"},
    "patient_lname": {"resource": "Patient", "field": "name.family"},
    "fname": {"resource": "Patient", "field": "name.given"},
    "lname": {"resource": "Patient", "field": "name.family"},
    "first_name": {"resource": "Patient", "field": "name.given"},
    "last_name": {"resource": "Patient", "field": "name.family"},
    "patient_dob": {"resource": "Patient", "field": "birthDate"},
    "patient_birth_date": {"resource": "Patient", "field": "birthDate"},
    "birth_date": {"resource": "Patient", "field": "birthDate"},
    "birthdate": {"resource": "Patient", "field": "birthDate"},
    "dob": {"resource": "Patient", "field": "birthDate"},
    "date_of_birth": {"resource": "Patient", "field": "birthDate"},
    "patient_gender": {"resource": "Patient", "field": "gender"},
    "patient_sex": {"resource": "Patient", "field": "gender"},
    "gender": {"resource": "Patient", "field": "gender"},
    "sex": {"resource": "Patient", "field": "gender"},
    "patient_address": {"resource": "Patient", "field": "address"},
    "patient_zip": {"resource": "Patient", "field": "address.postalCode"},
    "patient_state": {"resource": "Patient", "field": "address.state"},
    "patient_city": {"resource": "Patient", "field": "address.city"},
    "zip": {"resource": "Patient", "field": "address.postalCode"},
    "zip_code": {"resource": "Patient", "field": "address.postalCode"},
    "zipcode": {"resource": "Patient", "field": "address.postalCode"},
    "postal_code": {"resource": "Patient", "field": "address.postalCode"},
    "state": {"resource": "Patient", "field": "address.state"},
    "city": {"resource": "Patient", "field": "address.city"},
    "address": {"resource": "Patient", "field": "address"},
    "address_line_1": {"resource": "Patient", "field": "address.line"},
    "addr_line1": {"resource": "Patient", "field": "address.line"},
    
    # Provider information
    "provider_id": {"resource": "Practitioner", "field": "identifier"},
    "providerid": {"resource": "Practitioner", "field": "identifier"},
    "provider_npi": {"resource": "Practitioner", "field": "identifier"},
    "provider_number": {"resource": "Practitioner", "field": "identifier"},
    "npi": {"resource": "Practitioner", "field": "identifier"},
    "rendering_provider_id": {"resource": "Practitioner", "field": "identifier"},
    "performing_provider_id": {"resource": "Practitioner", "field": "identifier"},
    "provider_name": {"resource": "Practitioner", "field": "name"},
    "provider_first_name": {"resource": "Practitioner", "field": "name.given"},
    "provider_last_name": {"resource": "Practitioner", "field": "name.family"},
    "provider_type": {"resource": "Practitioner", "field": "qualification.code"},
    "provider_specialty": {"resource": "Practitioner", "field": "qualification.code"},
    "provider_taxonomy": {"resource": "Practitioner", "field": "qualification.code"},
    
    # Organization information
    "facility_id": {"resource": "Organization", "field": "identifier"},
    "facility_name": {"resource": "Organization", "field": "name"},
    "billing_provider_id": {"resource": "Organization", "field": "identifier"},
    "billing_provider_name": {"resource": "Organization", "field": "name"},
    "hospital_id": {"resource": "Organization", "field": "identifier"},
    "hospital_name": {"resource": "Organization", "field": "name"},
    "facility_npi": {"resource": "Organization", "field": "identifier"},
    "organization_id": {"resource": "Organization", "field": "identifier"},
    "organization_name": {"resource": "Organization", "field": "name"},
    
    # Service information
    "service_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "date_of_service": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "dos": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "svc_dt": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "svcdt": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "service_dt": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "srvc_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "service_from_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "from_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "service_from": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.start"},
    "service_to_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.end"},
    "to_date": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.end"},
    "service_to": {"resource": "ExplanationOfBenefit", "field": "billablePeriod.end"},
    "service_line_number": {"resource": "ExplanationOfBenefit", "field": "item.sequence"},
    "line_number": {"resource": "ExplanationOfBenefit", "field": "item.sequence"},
    "line_no": {"resource": "ExplanationOfBenefit", "field": "item.sequence"},
    
    # Diagnosis information
    "diagnosis_code": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept"},
    "diag_code": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept"},
    "diagnosis_type": {"resource": "ExplanationOfBenefit", "field": "diagnosis.type"},
    "diagnosis_1": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept"},
    "dx1": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept"},
    "primary_diagnosis": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept"},
    "diagnosis_description": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept.text"},
    "diag_desc": {"resource": "ExplanationOfBenefit", "field": "diagnosis.diagnosisCodeableConcept.text"},
    
    # Procedure information
    "procedure_code": {"resource": "ExplanationOfBenefit", "field": "procedure.procedureCodeableConcept"},
    "proc_code": {"resource": "ExplanationOfBenefit", "field": "procedure.procedureCodeableConcept"},
    "hcpcs_code": {"resource": "ExplanationOfBenefit", "field": "item.productOrService"},
    "cpt_code": {"resource": "ExplanationOfBenefit", "field": "item.productOrService"},
    "service_code": {"resource": "ExplanationOfBenefit", "field": "item.productOrService"},
    "procedure_description": {"resource": "ExplanationOfBenefit", "field": "procedure.procedureCodeableConcept.text"},
    "proc_desc": {"resource": "ExplanationOfBenefit", "field": "procedure.procedureCodeableConcept.text"},
    
    # Billing codes
    "revenue_code": {"resource": "ExplanationOfBenefit", "field": "item.revenue"},
    "rev_code": {"resource": "ExplanationOfBenefit", "field": "item.revenue"},
    "ndc_code": {"resource": "ExplanationOfBenefit", "field": "item.productOrService"},
    "ndc": {"resource": "ExplanationOfBenefit", "field": "item.productOrService"},
    "place_of_service": {"resource": "ExplanationOfBenefit", "field": "facility.type"},
    "pos": {"resource": "ExplanationOfBenefit", "field": "facility.type"},
    "pos_code": {"resource": "ExplanationOfBenefit", "field": "facility.type"},
    "type_of_service": {"resource": "ExplanationOfBenefit", "field": "type"},
    "tos": {"resource": "ExplanationOfBenefit", "field": "type"},
    
    # Financial information
    "billed_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "charged_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "submitted_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "allowed_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "allowed_amt": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "payment_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "paid_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "paid_amt": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "copay_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "coinsurance_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "deductible_amount": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "patient_responsibility": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    "member_liability": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.amount"},
    
    # Dates
    "claim_date": {"resource": "ExplanationOfBenefit", "field": "created"},
    "date_received": {"resource": "ExplanationOfBenefit", "field": "created"},
    "payment_date": {"resource": "ExplanationOfBenefit", "field": "payment.date"},
    "paid_date": {"resource": "ExplanationOfBenefit", "field": "payment.date"},
    "adjudication_date": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.date"},
    "process_date": {"resource": "ExplanationOfBenefit", "field": "item.adjudication.date"},
    
    # Claim status
    "claim_status": {"resource": "ExplanationOfBenefit", "field": "status"},
    "status": {"resource": "ExplanationOfBenefit", "field": "status"},
    "claim_type": {"resource": "ExplanationOfBenefit", "field": "type"},
    "claim_subtype": {"resource": "ExplanationOfBenefit", "field": "subType"},
    
    # Coverage information
    "group_number": {"resource": "Coverage", "field": "group"},
    "group_name": {"resource": "Coverage", "field": "groupDisplay"},
    "plan_id": {"resource": "Coverage", "field": "identifier"},
    "plan_name": {"resource": "Coverage", "field": "class.name"},
    "insurance_type": {"resource": "Coverage", "field": "type"},
    "coverage_type": {"resource": "Coverage", "field": "type"},
    "payer_id": {"resource": "Coverage", "field": "payor.identifier"},
    "payer_name": {"resource": "Coverage", "field": "payor.display"},
    "insurer_id": {"resource": "Coverage", "field": "payor.identifier"},
    "insurer_name": {"resource": "Coverage", "field": "payor.display"},
    "payer": {"resource": "Coverage", "field": "payor"},
    "coverage_id": {"resource": "Coverage", "field": "identifier"},
    
    # Additional fields
    "admission_date": {"resource": "ExplanationOfBenefit", "field": "careTeam.period.start"},
    "discharge_date": {"resource": "ExplanationOfBenefit", "field": "careTeam.period.end"},
    "drg_code": {"resource": "ExplanationOfBenefit", "field": "diagnosis.packageCode"},
    "bill_type": {"resource": "ExplanationOfBenefit", "field": "form.code"},
    "quantity": {"resource": "ExplanationOfBenefit", "field": "item.quantity"},
    "units": {"resource": "ExplanationOfBenefit", "field": "item.quantity"},
    "days_supply": {"resource": "ExplanationOfBenefit", "field": "item.quantity"},
    "modifier": {"resource": "ExplanationOfBenefit", "field": "item.modifier"},
    "modifiers": {"resource": "ExplanationOfBenefit", "field": "item.modifier"},
    "service_modifier": {"resource": "ExplanationOfBenefit", "field": "item.modifier"},
}

# Common variants for claims data column names
# This helps match columns that are named slightly differently
COLUMN_VARIATIONS = {
    # Different naming conventions
    "id": ["id", "identifier", "number"],
    "claim": ["claim", "clm", "eob"],
    "patient": ["patient", "pat", "patnt", "member", "mbr", "beneficiary", "subscriber"],
    "provider": ["provider", "prov", "provdr", "doctor", "physician", "rendering", "attending"],
    "service": ["service", "svc", "serv"],
    "amount": ["amount", "amt", "dollars", "$", "total", "payment", "charge", "charged"],
    "date": ["date", "dt", "day", "time"],
    "diagnosis": ["diagnosis", "diag", "dx", "icd", "icd10", "icd9"],
    "procedure": ["procedure", "proc", "px", "cpt", "hcpcs"],
    
    # Common separators
    "separators": ["_", "", "-", ".", " "],
    
    # Order variations
    "order_pairs": [
        ["claim", "id"],
        ["patient", "id"],
        ["member", "id"],
        ["provider", "id"],
        ["service", "date"],
        ["date", "service"]
    ]
}

def generate_common_claims_column_variations():
    """
    Generate common variations of claims data column names to enhance matching.
    
    Returns:
        dict: Mapping of column variations to standardized column names
    """
    variations = {}
    
    # Generate variations based on common naming conventions
    for column, mapping in CLAIMS_DATA_MAPPINGS.items():
        base_parts = column.split('_')
        
        # Generate variations with different separators
        for separator in COLUMN_VARIATIONS["separators"]:
            variation = separator.join(base_parts)
            if variation != column:
                variations[variation] = {"column": column, "mapping": mapping}
        
        # Generate shortened variations
        if len(base_parts) >= 2:
            # First letter of all parts except last + full last part
            shortened = ''.join([p[0] for p in base_parts[:-1]]) + base_parts[-1]
            variations[shortened] = {"column": column, "mapping": mapping}
            
            # First letter of all parts
            acronym = ''.join([p[0] for p in base_parts])
            variations[acronym] = {"column": column, "mapping": mapping}
    
    # Add common patterns for claim_id variations
    for claim_term in COLUMN_VARIATIONS["claim"]:
        for id_term in COLUMN_VARIATIONS["id"]:
            # Try different separator combinations
            for separator in COLUMN_VARIATIONS["separators"]:
                variation = f"{claim_term}{separator}{id_term}"
                variations[variation] = {
                    "column": "claim_id", 
                    "mapping": CLAIMS_DATA_MAPPINGS["claim_id"]
                }
                
                # Also try reverse order
                variation = f"{id_term}{separator}{claim_term}"
                variations[variation] = {
                    "column": "claim_id", 
                    "mapping": CLAIMS_DATA_MAPPINGS["claim_id"]
                }
    
    # Add common patterns for patient_id variations
    for patient_term in COLUMN_VARIATIONS["patient"]:
        for id_term in COLUMN_VARIATIONS["id"]:
            # Try different separator combinations
            for separator in COLUMN_VARIATIONS["separators"]:
                variation = f"{patient_term}{separator}{id_term}"
                variations[variation] = {
                    "column": "patient_id", 
                    "mapping": CLAIMS_DATA_MAPPINGS["patient_id"]
                }
                
                # Also try reverse order
                variation = f"{id_term}{separator}{patient_term}"
                variations[variation] = {
                    "column": "patient_id", 
                    "mapping": CLAIMS_DATA_MAPPINGS["patient_id"]
                }
    
    return variations

# Generate all the variations
COLUMN_VARIATION_MAPPINGS = generate_common_claims_column_variations()

def get_claims_mapping(column_name):
    """
    Get the FHIR mapping for a claims data column name.
    
    Args:
        column_name: The column name to look up
        
    Returns:
        dict or None: The mapping information if found, None otherwise
    """
    # Normalize the column name
    normalized = column_name.lower().replace(' ', '_').replace('-', '_')
    
    # Check direct mappings first
    if normalized in CLAIMS_DATA_MAPPINGS:
        mapping = CLAIMS_DATA_MAPPINGS[normalized]
        return {
            "column": normalized,
            "resource": mapping["resource"],
            "field": mapping["field"],
            "confidence": 0.95,  # High confidence for direct matches
            "match_type": "direct"
        }
    
    # Try removing common prefixes/suffixes and check again
    common_prefixes = ["clm_", "claim_", "pat_", "patient_"]
    common_suffixes = ["_code", "_id", "_date", "_amt", "_amount"]
    
    for prefix in common_prefixes:
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix):]
            if stripped in CLAIMS_DATA_MAPPINGS:
                mapping = CLAIMS_DATA_MAPPINGS[stripped]
                return {
                    "column": stripped,
                    "resource": mapping["resource"],
                    "field": mapping["field"],
                    "confidence": 0.85,  # Good confidence for prefix matches
                    "match_type": "prefix_match"
                }
    
    for suffix in common_suffixes:
        if normalized.endswith(suffix):
            stripped = normalized[:-len(suffix)]
            if stripped in CLAIMS_DATA_MAPPINGS:
                mapping = CLAIMS_DATA_MAPPINGS[stripped]
                return {
                    "column": stripped,
                    "resource": mapping["resource"],
                    "field": mapping["field"],
                    "confidence": 0.85,  # Good confidence for suffix matches
                    "match_type": "suffix_match"
                }
    
    # Check variations
    if normalized in COLUMN_VARIATION_MAPPINGS:
        variation = COLUMN_VARIATION_MAPPINGS[normalized]
        mapping = variation["mapping"]
        return {
            "column": variation["column"],
            "resource": mapping["resource"],
            "field": mapping["field"],
            "confidence": 0.8,  # Good confidence for variation matches
            "match_type": "variation_match"
        }
    
    # Check for partial matches
    for key, mapping in CLAIMS_DATA_MAPPINGS.items():
        # If column contains a known key as a substring
        if key in normalized and len(key) > 3:  # Avoid short substrings
            return {
                "column": key,
                "resource": mapping["resource"],
                "field": mapping["field"],
                "confidence": 0.65,  # Moderate confidence for partial matches
                "match_type": "partial_match"
            }
    
    # Check for the presence of certain keywords to make educated guesses
    if "claim" in normalized:
        return {
            "column": "claim_id",
            "resource": "ExplanationOfBenefit",
            "field": "identifier",
            "confidence": 0.6,  # Lower confidence for keyword matches
            "match_type": "keyword_match"
        }
    elif "patient" in normalized or "member" in normalized:
        return {
            "column": "patient_id",
            "resource": "Patient",
            "field": "identifier",
            "confidence": 0.6,
            "match_type": "keyword_match"
        }
    elif "provider" in normalized or "npi" in normalized:
        return {
            "column": "provider_id",
            "resource": "Practitioner",
            "field": "identifier",
            "confidence": 0.6,
            "match_type": "keyword_match"
        }
    elif "service" in normalized and "date" in normalized:
        return {
            "column": "service_date",
            "resource": "ExplanationOfBenefit",
            "field": "billablePeriod.start",
            "confidence": 0.6,
            "match_type": "keyword_match"
        }
    elif "amount" in normalized or "payment" in normalized or "paid" in normalized:
        return {
            "column": "paid_amount",
            "resource": "ExplanationOfBenefit",
            "field": "item.adjudication.amount",
            "confidence": 0.5,
            "match_type": "keyword_match"
        }
    
    # No match found
    return None

def get_claims_mapping_knowledge_base():
    """
    Get a knowledge base of claims data mappings to use for LLM context.
    
    Returns:
        str: A formatted string explaining common claims data mappings
    """
    knowledge = """
# Claims Data to FHIR Mapping Knowledge Base

## Common Claims Data Mappings

### ExplanationOfBenefit Resource
- **claim_id**, **claim_number**, **claimid** → ExplanationOfBenefit.identifier
- **service_date**, **date_of_service**, **dos** → ExplanationOfBenefit.billablePeriod.start
- **paid_amount**, **payment_amount** → ExplanationOfBenefit.item.adjudication.amount
- **diagnosis_code**, **diag_code**, **dx1** → ExplanationOfBenefit.diagnosis.diagnosisCodeableConcept
- **procedure_code**, **proc_code**, **cpt_code** → ExplanationOfBenefit.item.productOrService
- **ndc_code**, **ndc** → ExplanationOfBenefit.item.productOrService (for pharmacy claims)
- **revenue_code**, **rev_code** → ExplanationOfBenefit.item.revenue (for institutional claims)
- **place_of_service**, **pos_code** → ExplanationOfBenefit.facility.type
- **claim_status** → ExplanationOfBenefit.status
- **adjudication_date**, **process_date** → ExplanationOfBenefit.item.adjudication.date
- **service_line_number**, **line_number** → ExplanationOfBenefit.item.sequence

### Patient Resource
- **patient_id**, **patientid**, **member_id** → Patient.identifier
- **patient_first_name** → Patient.name.given
- **patient_last_name** → Patient.name.family
- **patient_dob**, **patient_birth_date** → Patient.birthDate
- **patient_gender**, **patient_sex** → Patient.gender
- **patient_address** → Patient.address
- **patient_zip** → Patient.address.postalCode

### Practitioner Resource
- **provider_id**, **provider_npi**, **npi** → Practitioner.identifier
- **provider_name** → Practitioner.name
- **provider_type**, **provider_specialty** → Practitioner.qualification.code

### Organization Resource
- **facility_id**, **facility_name** → Organization.identifier, Organization.name
- **billing_provider_id** → Organization.identifier
- **hospital_id**, **hospital_name** → Organization.identifier, Organization.name

### Coverage Resource
- **group_number**, **group_name** → Coverage.group, Coverage.groupDisplay
- **plan_id**, **plan_name** → Coverage.identifier, Coverage.class.name
- **payer_id**, **insurer_id** → Coverage.payor.identifier
- **payer_name**, **insurer_name** → Coverage.payor.display
- **coverage_type**, **insurance_type** → Coverage.type
"""
    return knowledge