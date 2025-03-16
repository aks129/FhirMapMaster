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

def analyze_unmapped_column(client, column_name, sample_values, fhir_standard):
    """
    Analyze an unmapped column using Anthropic Claude to suggest a FHIR mapping.
    
    Args:
        client: Anthropic client instance
        column_name: Name of the column to analyze
        sample_values: Sample values from the column
        fhir_standard: FHIR standard being used (US Core or CARIN BB)
    
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
    
    # Format sample values for the prompt
    sample_str = str(sample_values[:10])
    
    # Create the prompt
    prompt = f"""
You are a healthcare data expert specializing in FHIR HL7 data models. You're helping map healthcare data to the {fhir_standard} implementation guide.

I have a column in my healthcare dataset that needs mapping to FHIR:

Column name: {column_name}
Sample values: {sample_str}

Based on the column name and sample values, suggest the most appropriate FHIR resource and field from the {fhir_standard} implementation guide that this data should map to.

Format your response as a JSON object with these fields:
- suggested_resource: The name of the FHIR resource (e.g., "Patient", "Observation")
- suggested_field: The specific field within that resource
- confidence: A number between 0 and 1 indicating your confidence in this mapping
- explanation: A brief explanation of your reasoning

Response:
"""
    
    try:
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the JSON response
        response_text = response.content[0].text
        
        # Find and extract the JSON portion
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return result
        else:
            # If JSON parsing fails, try to extract key information
            return {
                "suggested_resource": None,
                "suggested_field": None,
                "confidence": 0,
                "explanation": "Could not parse LLM response into the expected format."
            }
    
    except Exception as e:
        return {
            "suggested_resource": None,
            "suggested_field": None,
            "confidence": 0,
            "explanation": f"Error getting LLM suggestion: {str(e)}"
        }

def get_multiple_mapping_suggestions(client, unmapped_columns, df, fhir_standard):
    """
    Get mapping suggestions for multiple unmapped columns.
    
    Args:
        client: Anthropic client instance
        unmapped_columns: List of column names that need mapping
        df: pandas DataFrame containing the data
        fhir_standard: FHIR standard being used (US Core or CARIN BB)
    
    Returns:
        dict containing suggestions for each column
    """
    suggestions = {}
    
    for column in unmapped_columns:
        # Get sample values (non-null)
        sample_values = df[column].dropna().unique().tolist()
        
        # Get suggestion for this column
        suggestion = analyze_unmapped_column(client, column, sample_values, fhir_standard)
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
    
    # Create the prompt with more detailed context
    prompt = f"""
You are a healthcare data expert specializing in FHIR HL7 data models. You're helping with a complex data mapping scenario for the {fhir_standard} implementation guide.

Here's the mapping situation:
{json.dumps(mapping_data, indent=2)}

Please analyze this mapping situation and provide:
1. A detailed assessment of the current mapping approach
2. Any potential issues or inconsistencies you see
3. Specific recommendations to improve the mapping
4. Alternative mapping approaches if applicable

Focus on healthcare data best practices and FHIR compliance.
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
