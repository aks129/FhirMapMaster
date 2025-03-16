import os
import anthropic
from anthropic import Anthropic
import streamlit as st
import pandas as pd
import json

def initialize_anthropic_client():
    """
    Initialize the Anthropic client with API key.
    
    Returns:
        Anthropic client instance or None if initialization fails
    """
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not anthropic_key:
        st.warning("ANTHROPIC_API_KEY environment variable is not set. LLM-assisted mapping will not be available.")
        return None
    
    try:
        # Initialize the client
        client = Anthropic(api_key=anthropic_key)
        return client
    except Exception as e:
        st.error(f"Error initializing Anthropic client: {str(e)}")
        return None

def analyze_unmapped_column(client, column_name, sample_values, fhir_standard, ig_version=""):
    """
    Analyze an unmapped column using Anthropic Claude to suggest a FHIR mapping.
    Enhanced with CPCDS mapping knowledge for CARIN BB claims data.
    
    Args:
        client: Anthropic client instance
        column_name: Name of the column to analyze
        sample_values: Sample values from the column
        fhir_standard: FHIR standard being used (US Core or CARIN BB)
        ig_version: The version of the implementation guide (optional)
    
    Returns:
        dict containing the suggested mapping and explanation
    """
    if client is None:
        return {
            "suggested_resource": None,
            "suggested_field": None,
            "confidence": 0,
            "explanation": "Anthropic API key is not available."
        }
    
    # Apply direct mapping logic first for CARIN BB claims data
    if fhir_standard == "CARIN BB":
        # Try to directly map based on CPCDS patterns before using the LLM
        try:
            # Import the CPCDS mapping module
            from utils.cpcds_mapping import ensure_cpcds_mappings_loaded
            
            # Get the CPCDS mappings
            mappings = ensure_cpcds_mappings_loaded()
            
            # Normalize column name for matching
            col_lower = column_name.lower().replace(" ", "_").replace("-", "_")
            
            # Check if this column has a known mapping
            if col_lower in mappings["column_to_resource"]:
                resource = mappings["column_to_resource"][col_lower]
                field = mappings["column_to_field"].get(col_lower, "id")  # Default to id if field mapping not found
                
                # Determine if this is a high-confidence match
                is_high_confidence = any(term in col_lower for term in ["id", "identifier", "claim", "patient", "service"])
                confidence = 0.95 if is_high_confidence else 0.8
                
                return {
                    "suggested_resource": resource,
                    "suggested_field": field,
                    "confidence": confidence,
                    "explanation": f"Direct match with CPCDS mapping pattern. The column '{column_name}' maps to {resource}.{field} according to CARIN BB CPCDS mapping standards."
                }
            
            # Check for common pattern variations
            if "claim" in col_lower and "id" in col_lower:
                return {
                    "suggested_resource": "ExplanationOfBenefit",
                    "suggested_field": "identifier",
                    "confidence": 0.9,
                    "explanation": f"Column '{column_name}' matches the pattern for claim identifiers, which map to ExplanationOfBenefit.identifier in CARIN BB."
                }
            
            if ("member" in col_lower or "patient" in col_lower) and "id" in col_lower:
                return {
                    "suggested_resource": "Patient",
                    "suggested_field": "identifier",
                    "confidence": 0.9,
                    "explanation": f"Column '{column_name}' matches the pattern for patient identifiers, which map to Patient.identifier in CARIN BB."
                }
            
            # Add more pattern recognition as needed
            
        except Exception as e:
            print(f"Error in CPCDS direct mapping: {str(e)}")
            # Continue to LLM-based approach if direct mapping fails
    
    # Import resources to get available resources and fields
    from utils.fhir_mapper import get_fhir_resources
    
    # Get the FHIR resources for this standard and version
    resources = get_fhir_resources(fhir_standard, ig_version)
    
    # Format sample values for the prompt
    sample_str = str(sample_values[:10])
    
    # Create a structured representation of the available resources and fields
    resource_info = {}
    for resource_name, resource_data in resources.items():
        if 'fields' in resource_data:
            resource_info[resource_name] = {
                'description': resource_data.get('description', f'{resource_name} resource'),
                'fields': resource_data['fields']
            }
    
    # Get claims data mapping knowledge if this is CARIN BB
    claims_guidance = ""
    if fhir_standard == "CARIN BB":
        # Import the claims mapping module
        try:
            from utils.cpcds_mapping import get_claims_mapping_prompt_enhancement
            claims_guidance = """
## CARIN BB Claims Data Mapping Guidelines

When mapping healthcare claims data, follow these patterns from the CARIN BB Implementation Guide:

### ExplanationOfBenefit Resource
- **claim_id**, **claim_number**, **claimid** → ExplanationOfBenefit.identifier
- **service_date**, **date_of_service**, **dos** → ExplanationOfBenefit.billablePeriod.start
- **paid_amount**, **payment_amount** → ExplanationOfBenefit.item.adjudication.amount
- **diagnosis_code**, **diag_code**, **dx1** → ExplanationOfBenefit.diagnosis.diagnosisCodeableConcept
- **procedure_code**, **proc_code**, **cpt_code** → ExplanationOfBenefit.item.productOrService
- **ndc_code**, **ndc** → ExplanationOfBenefit.item.productOrService (for pharmacy claims)
- **revenue_code**, **rev_code** → ExplanationOfBenefit.item.revenue (for institutional claims)

### Patient Resource
- **patient_id**, **patientid**, **member_id** → Patient.identifier
- **patient_first_name** → Patient.name.given
- **patient_last_name** → Patient.name.family

### Coverage Resource
- **payer_id**, **insurer_id** → Coverage.payor.identifier
- **payer_name** → Coverage.payor.display
- **group_number** → Coverage.group
"""
            # Get enhanced guidance from our comprehensive mapping knowledge base
            enhancement = get_claims_mapping_prompt_enhancement()
            if enhancement and len(enhancement) > 100:  # Sanity check that we got real enhancement
                claims_guidance = enhancement
        except Exception as e:
            print(f"Error getting claims mapping prompt enhancement: {str(e)}")
    
    # Create the prompt with enhanced FHIR knowledge and CPCDS guidance
    prompt = f"""
You are Parker, an expert in healthcare data mapping specializing in FHIR HL7 standards and particularly the {fhir_standard} Implementation Guide.

I have a column in my healthcare dataset that needs mapping to FHIR:

Column name: {column_name}
Sample values: {sample_str}

{claims_guidance}

Here are the available FHIR resources and fields in the {fhir_standard} Implementation Guide:
{json.dumps(resource_info, indent=2)}

Based on the column name and sample values, suggest the most appropriate FHIR resource and field from the above list that this data should map to.

Format your response as a JSON object with these fields:
- suggested_resource: The name of the FHIR resource (e.g., "Patient", "Observation")
- suggested_field: The specific field within that resource
- confidence: A number between 0 and 1 indicating your confidence in this mapping (be conservative - only use 0.8+ for very clear matches)
- explanation: A brief explanation of your reasoning

Response:
"""
    
    try:
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.0,
            response_format={"type": "json_object"},  # Request JSON format directly
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the JSON response
        result = json.loads(response.content[0].text)
        
        # Validate the result
        if "suggested_resource" not in result:
            result["suggested_resource"] = None
        if "suggested_field" not in result:
            result["suggested_field"] = None
        if "confidence" not in result:
            result["confidence"] = 0
        if "explanation" not in result:
            result["explanation"] = "No explanation provided."
        
        return result
    
    except Exception as e:
        return {
            "suggested_resource": None,
            "suggested_field": None,
            "confidence": 0,
            "explanation": f"Error getting LLM suggestion: {str(e)}"
        }

def get_multiple_mapping_suggestions(client, unmapped_columns, df, fhir_standard, ig_version=""):
    """
    Get mapping suggestions for multiple unmapped columns.
    
    Args:
        client: Anthropic client instance
        unmapped_columns: List of column names that need mapping
        df: pandas DataFrame containing the data
        fhir_standard: FHIR standard being used (US Core or CARIN BB)
        ig_version: The version of the implementation guide (optional)
    
    Returns:
        dict containing suggestions for each column
    """
    suggestions = {}
    
    for column in unmapped_columns:
        # Get sample values (non-null)
        sample_values = df[column].dropna().unique().tolist()
        
        # Get suggestion for this column
        suggestion = analyze_unmapped_column(client, column, sample_values, fhir_standard, ig_version)
        suggestions[column] = suggestion
    
    return suggestions

def analyze_complex_mapping(client, mapping_data, fhir_standard):
    """
    Analyze a complex mapping situation using Anthropic Claude.
    
    Args:
        client: Anthropic client instance
        mapping_data: Dict containing mapping information and context
        fhir_standard: FHIR standard being used (US Core or CARIN BB)
    
    Returns:
        str containing the LLM's analysis and recommendations
    """
    if client is None:
        return "Anthropic API key is not available."
    
    # Import resources to get available resources and fields
    from utils.fhir_mapper import get_fhir_resources
    
    # Get the FHIR resources for this standard and version
    resources = get_fhir_resources(fhir_standard, "")
    
    # Create a structured representation of the available resources and fields
    resource_info = {}
    for resource_name, resource_data in resources.items():
        if 'fields' in resource_data:
            resource_info[resource_name] = {
                'description': resource_data.get('description', f'{resource_name} resource'),
                'fields': resource_data['fields']
            }
    
    # Create the prompt with enhanced FHIR knowledge
    prompt = f"""
You are a healthcare data expert specializing in FHIR HL7 data models. You're helping with a complex data mapping scenario for the {fhir_standard} implementation guide.

Here's the mapping situation:
{json.dumps(mapping_data, indent=2)}

Here are the available FHIR resources and fields in the {fhir_standard} Implementation Guide:
{json.dumps(resource_info, indent=2)}

Please analyze this mapping situation and provide:
1. A detailed assessment of the current mapping approach against the Implementation Guide definitions
2. Any potential issues or inconsistencies you see
3. Specific recommendations to improve the mapping
4. Alternative mapping approaches if applicable

Focus on healthcare data best practices and FHIR compliance according to the official Implementation Guide.
"""
    
    try:
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    except Exception as e:
        return f"Error getting LLM analysis: {str(e)}"
