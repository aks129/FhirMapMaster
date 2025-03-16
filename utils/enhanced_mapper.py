"""
Enhanced Data Mapper for Healthcare Data Transformations

This module implements pattern-based automated mapping capabilities for healthcare data,
drawing inspiration from the SparkAutoMapper project while being tailored for our application.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Any, Union, Optional, Tuple, Callable
from utils.fhir_datatypes import (
    HumanName, Address, ContactPoint, Identifier, CodeableConcept, FHIRDatatype
)

# Define mapper types
class FieldMapperTypes:
    """Types of field mapping operations that can be performed."""
    DIRECT = "direct"
    TRANSFORM = "transform"
    COMPLEX = "complex"
    LITERAL = "literal"
    REGEX = "regex"
    CONCAT = "concat"
    SPLIT = "split"
    LOOKUP = "lookup"
    DATE_FORMAT = "date_format"
    CASE_TRANSFORM = "case_transform"
    CODE_LOOKUP = "code_lookup"
    TEMPLATE = "template"
    FHIR_DATATYPE = "fhir_datatype"

class CaseTransformTypes:
    """Types of case transformations."""
    UPPER = "upper"
    LOWER = "lower"
    TITLE = "title"
    SNAKE = "snake_case"
    CAMEL = "camelCase"
    KEBAB = "kebab-case"

class FieldMapper:
    """
    Field mapper class for defining mapping operations.
    This is inspired by SparkAutoMapper's approach but simplified for our use case.
    """
    def __init__(self, 
                 source_field: Optional[str] = None,
                 mapping_type: str = FieldMapperTypes.DIRECT,
                 transform_function: Optional[Callable] = None,
                 parameters: Optional[Dict[str, Any]] = None,
                 literal_value: Any = None):
        self.source_field = source_field
        self.mapping_type = mapping_type
        self.transform_function = transform_function
        self.parameters = parameters or {}
        self.literal_value = literal_value
    
    def transform(self, source_data: Dict[str, Any]) -> Any:
        """
        Apply the transformation based on mapping type.
        
        Args:
            source_data: Dictionary containing source data
            
        Returns:
            Transformed value
        """
        if self.mapping_type == FieldMapperTypes.DIRECT:
            return source_data.get(self.source_field)
        
        elif self.mapping_type == FieldMapperTypes.LITERAL:
            return self.literal_value
        
        elif self.mapping_type == FieldMapperTypes.TRANSFORM and self.transform_function:
            source_value = source_data.get(self.source_field)
            if source_value is not None:
                return self.transform_function(source_value)
            return None
        
        elif self.mapping_type == FieldMapperTypes.REGEX:
            source_value = source_data.get(self.source_field)
            if source_value is not None and isinstance(source_value, str):
                pattern = self.parameters.get('pattern', '')
                replacement = self.parameters.get('replacement', '')
                return re.sub(pattern, replacement, source_value)
            return None
        
        elif self.mapping_type == FieldMapperTypes.CONCAT:
            fields = self.parameters.get('fields', [])
            separator = self.parameters.get('separator', '')
            values = []
            for field in fields:
                if isinstance(field, FieldMapper):
                    value = field.transform(source_data)
                else:
                    value = source_data.get(field)
                if value is not None:
                    values.append(str(value))
            return separator.join(values)
        
        elif self.mapping_type == FieldMapperTypes.SPLIT:
            source_value = source_data.get(self.source_field)
            if source_value is not None and isinstance(source_value, str):
                separator = self.parameters.get('separator', '')
                index = self.parameters.get('index', 0)
                parts = source_value.split(separator)
                if 0 <= index < len(parts):
                    return parts[index]
            return None
        
        elif self.mapping_type == FieldMapperTypes.LOOKUP:
            source_value = source_data.get(self.source_field)
            if source_value is not None:
                lookup_table = self.parameters.get('lookup_table', {})
                default_value = self.parameters.get('default', None)
                return lookup_table.get(source_value, default_value)
            return None
        
        elif self.mapping_type == FieldMapperTypes.DATE_FORMAT:
            source_value = source_data.get(self.source_field)
            if source_value is not None:
                try:
                    input_format = self.parameters.get('input_format')
                    output_format = self.parameters.get('output_format', '%Y-%m-%d')
                    
                    # Convert to pandas datetime then format
                    if input_format:
                        dt = pd.to_datetime(source_value, format=input_format)
                    else:
                        dt = pd.to_datetime(source_value)
                    
                    return dt.strftime(output_format)
                except:
                    return None
            return None
        
        elif self.mapping_type == FieldMapperTypes.CASE_TRANSFORM:
            source_value = source_data.get(self.source_field)
            if source_value is not None and isinstance(source_value, str):
                transform_type = self.parameters.get('transform_type', CaseTransformTypes.UPPER)
                
                if transform_type == CaseTransformTypes.UPPER:
                    return source_value.upper()
                elif transform_type == CaseTransformTypes.LOWER:
                    return source_value.lower()
                elif transform_type == CaseTransformTypes.TITLE:
                    return source_value.title()
                elif transform_type == CaseTransformTypes.SNAKE:
                    # Convert spaces and other separators to underscores
                    return re.sub(r'[\s-]', '_', source_value).lower()
                elif transform_type == CaseTransformTypes.CAMEL:
                    # Convert to camelCase
                    words = re.split(r'[\s_-]', source_value)
                    return words[0].lower() + ''.join(word.title() for word in words[1:])
                elif transform_type == CaseTransformTypes.KEBAB:
                    # Convert to kebab-case
                    return re.sub(r'[\s_]', '-', source_value).lower()
            return None
        
        elif self.mapping_type == FieldMapperTypes.CODE_LOOKUP:
            source_value = source_data.get(self.source_field)
            if source_value is not None:
                code_system = self.parameters.get('code_system', '')
                value_set = self.parameters.get('value_set', {})
                
                # Special handling for healthcare code systems
                if code_system == 'SNOMED':
                    # SNOMED CT code lookup would go here
                    pass
                elif code_system == 'LOINC':
                    # LOINC code lookup would go here
                    pass
                elif code_system == 'ICD10':
                    # ICD-10 code lookup would go here
                    pass
                elif code_system == 'CPT':
                    # CPT code lookup would go here
                    pass
                
                # Default to simple value set lookup
                return value_set.get(source_value)
            return None
            
        elif self.mapping_type == FieldMapperTypes.TEMPLATE:
            template = self.parameters.get('template', '')
            values = {}
            
            # Get all field values needed for the template
            for field_name, field_mapper in self.parameters.get('fields', {}).items():
                if isinstance(field_mapper, FieldMapper):
                    values[field_name] = field_mapper.transform(source_data)
                else:
                    values[field_name] = source_data.get(field_mapper)
            
            # Apply template formatting
            try:
                return template.format(**values)
            except (KeyError, ValueError):
                return None
                
        elif self.mapping_type == FieldMapperTypes.FHIR_DATATYPE:
            datatype = self.parameters.get('datatype')
            if datatype == 'HumanName':
                # Get the field values for HumanName
                if 'full_name' in self.parameters:
                    # From a single full name field
                    full_name_field = self.parameters.get('full_name')
                    full_name = source_data.get(full_name_field)
                    if full_name:
                        return HumanName.from_full_name(full_name).to_dict()
                else:
                    # From individual name parts
                    given_field = self.parameters.get('given')
                    family_field = self.parameters.get('family')
                    prefix_field = self.parameters.get('prefix')
                    suffix_field = self.parameters.get('suffix')
                    
                    given = source_data.get(given_field) if given_field else None
                    family = source_data.get(family_field) if family_field else None
                    prefix = source_data.get(prefix_field) if prefix_field else None
                    suffix = source_data.get(suffix_field) if suffix_field else None
                    
                    if any([given, family, prefix, suffix]):
                        return HumanName.from_parts(
                            first_name=given,
                            last_name=family,
                            prefix=prefix,
                            suffix=suffix
                        ).to_dict()
                        
            elif datatype == 'Address':
                # Get the field values for Address
                if 'full_address' in self.parameters:
                    # From a single address field
                    full_address_field = self.parameters.get('full_address')
                    full_address = source_data.get(full_address_field)
                    if full_address:
                        return Address.from_single_string(full_address).to_dict()
                else:
                    # From individual address parts
                    line_field = self.parameters.get('line')
                    city_field = self.parameters.get('city')
                    state_field = self.parameters.get('state')
                    postal_code_field = self.parameters.get('postalCode')
                    country_field = self.parameters.get('country')
                    
                    line = source_data.get(line_field) if line_field else None
                    city = source_data.get(city_field) if city_field else None
                    state = source_data.get(state_field) if state_field else None
                    postal_code = source_data.get(postal_code_field) if postal_code_field else None
                    country = source_data.get(country_field) if country_field else None
                    
                    if any([line, city, state, postal_code, country]):
                        return Address.from_parts(
                            street_address=line,
                            city=city,
                            state=state,
                            postal_code=postal_code,
                            country=country
                        ).to_dict()
                        
            elif datatype == 'ContactPoint':
                # Get the field value for ContactPoint
                value_field = self.parameters.get('value')
                system_field = self.parameters.get('system')
                
                value = source_data.get(value_field) if value_field else None
                system = source_data.get(system_field) if system_field else None
                
                if value:
                    # If we have a system specified, use it, otherwise infer from value
                    if system:
                        return ContactPoint(value=value, system=system).to_dict()
                    else:
                        return ContactPoint.from_value(value).to_dict()
                        
            elif datatype == 'Identifier':
                # Get the field values for Identifier
                value_field = self.parameters.get('value')
                system_field = self.parameters.get('system')
                
                value = source_data.get(value_field) if value_field else None
                system = source_data.get(system_field) if system_field else None
                
                if value:
                    return Identifier(value=value, system=system).to_dict()
                    
            elif datatype == 'CodeableConcept':
                # Get the field values for CodeableConcept
                code_field = self.parameters.get('code')
                system_field = self.parameters.get('system')
                display_field = self.parameters.get('display')
                
                code = source_data.get(code_field) if code_field else None
                system = source_data.get(system_field) if system_field else None
                display = source_data.get(display_field) if display_field else None
                
                if code:
                    return CodeableConcept.from_code(
                        code=code,
                        system=system,
                        display=display
                    ).to_dict()
        
        return None


class ResourceMapper:
    """
    Maps source data to a target resource structure using field mappers.
    This is inspired by SparkAutoMapper's approach but simplified for our use case.
    """
    def __init__(self, resource_type: str, field_mappers: Dict[str, FieldMapper] = None):
        self.resource_type = resource_type
        self.field_mappers = field_mappers or {}
    
    def add_mapping(self, target_field: str, field_mapper: FieldMapper) -> None:
        """
        Add a field mapper for a target field.
        
        Args:
            target_field: The target field in the output resource
            field_mapper: The field mapper to use for this field
        """
        self.field_mappers[target_field] = field_mapper
    
    def transform(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform source data to the target resource structure.
        
        Args:
            source_data: Dictionary containing source data
            
        Returns:
            Dictionary containing the transformed data
        """
        result = {'resourceType': self.resource_type}
        
        for target_field, field_mapper in self.field_mappers.items():
            value = field_mapper.transform(source_data)
            
            if value is not None:
                # Handle nested fields (using dot notation)
                if '.' in target_field:
                    parts = target_field.split('.')
                    current = result
                    
                    # Create nested dictionaries for all but the last part
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Set the value at the deepest level
                    current[parts[-1]] = value
                else:
                    result[target_field] = value
        
        return result


def create_resource_mapper_from_mappings(resource_type: str, 
                                        mappings: Dict[str, Dict[str, Any]]) -> ResourceMapper:
    """
    Create a ResourceMapper from a simplified mappings dictionary.
    
    Args:
        resource_type: The FHIR resource type
        mappings: Dictionary of field mappings
        
    Returns:
        ResourceMapper instance
    """
    resource_mapper = ResourceMapper(resource_type)
    
    for target_field, mapping_info in mappings.items():
        mapping_type = mapping_info.get('type', FieldMapperTypes.DIRECT)
        source_field = mapping_info.get('source_field')
        
        if mapping_type == FieldMapperTypes.DIRECT:
            mapper = FieldMapper(source_field=source_field)
        
        elif mapping_type == FieldMapperTypes.LITERAL:
            mapper = FieldMapper(mapping_type=FieldMapperTypes.LITERAL, 
                                literal_value=mapping_info.get('value'))
        
        elif mapping_type == FieldMapperTypes.TRANSFORM:
            transform_function = mapping_info.get('transform_function')
            if transform_function and callable(transform_function):
                mapper = FieldMapper(source_field=source_field,
                                    mapping_type=FieldMapperTypes.TRANSFORM,
                                    transform_function=transform_function)
            else:
                # Skip if no valid transformation function
                continue
        
        elif mapping_type == FieldMapperTypes.REGEX:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.REGEX,
                                parameters={
                                    'pattern': mapping_info.get('pattern', ''),
                                    'replacement': mapping_info.get('replacement', '')
                                })
        
        elif mapping_type == FieldMapperTypes.CONCAT:
            mapper = FieldMapper(mapping_type=FieldMapperTypes.CONCAT,
                                parameters={
                                    'fields': mapping_info.get('fields', []),
                                    'separator': mapping_info.get('separator', '')
                                })
        
        elif mapping_type == FieldMapperTypes.SPLIT:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.SPLIT,
                                parameters={
                                    'separator': mapping_info.get('separator', ''),
                                    'index': mapping_info.get('index', 0)
                                })
        
        elif mapping_type == FieldMapperTypes.LOOKUP:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.LOOKUP,
                                parameters={
                                    'lookup_table': mapping_info.get('lookup_table', {}),
                                    'default': mapping_info.get('default')
                                })
        
        elif mapping_type == FieldMapperTypes.DATE_FORMAT:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.DATE_FORMAT,
                                parameters={
                                    'input_format': mapping_info.get('input_format'),
                                    'output_format': mapping_info.get('output_format', '%Y-%m-%d')
                                })
        
        elif mapping_type == FieldMapperTypes.CASE_TRANSFORM:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.CASE_TRANSFORM,
                                parameters={
                                    'transform_type': mapping_info.get('transform_type', CaseTransformTypes.UPPER)
                                })
        
        elif mapping_type == FieldMapperTypes.CODE_LOOKUP:
            mapper = FieldMapper(source_field=source_field,
                                mapping_type=FieldMapperTypes.CODE_LOOKUP,
                                parameters={
                                    'code_system': mapping_info.get('code_system', ''),
                                    'value_set': mapping_info.get('value_set', {})
                                })
        
        elif mapping_type == FieldMapperTypes.TEMPLATE:
            mapper = FieldMapper(mapping_type=FieldMapperTypes.TEMPLATE,
                                parameters={
                                    'template': mapping_info.get('template', ''),
                                    'fields': mapping_info.get('fields', {})
                                })
        
        elif mapping_type == FieldMapperTypes.FHIR_DATATYPE:
            # Handle FHIR complex datatypes
            datatype = mapping_info.get('datatype')
            
            # Create parameters based on the datatype
            parameters = {'datatype': datatype}
            
            if datatype == 'HumanName':
                # Handle both full name and composite name part fields
                if 'full_name' in mapping_info:
                    parameters['full_name'] = mapping_info.get('full_name')
                else:
                    if 'given' in mapping_info:
                        parameters['given'] = mapping_info.get('given')
                    if 'family' in mapping_info:
                        parameters['family'] = mapping_info.get('family')
                    if 'prefix' in mapping_info:
                        parameters['prefix'] = mapping_info.get('prefix')
                    if 'suffix' in mapping_info:
                        parameters['suffix'] = mapping_info.get('suffix')
                        
            elif datatype == 'Address':
                # Handle both full address and composite address part fields
                if 'full_address' in mapping_info:
                    parameters['full_address'] = mapping_info.get('full_address')
                else:
                    if 'line' in mapping_info:
                        parameters['line'] = mapping_info.get('line')
                    if 'city' in mapping_info:
                        parameters['city'] = mapping_info.get('city')
                    if 'state' in mapping_info:
                        parameters['state'] = mapping_info.get('state')
                    if 'postalCode' in mapping_info:
                        parameters['postalCode'] = mapping_info.get('postalCode')
                    if 'country' in mapping_info:
                        parameters['country'] = mapping_info.get('country')
                        
            elif datatype == 'ContactPoint':
                if 'value' in mapping_info:
                    parameters['value'] = mapping_info.get('value')
                if 'system' in mapping_info:
                    parameters['system'] = mapping_info.get('system')
                    
            elif datatype == 'Identifier':
                if 'value' in mapping_info:
                    parameters['value'] = mapping_info.get('value')
                if 'system' in mapping_info:
                    parameters['system'] = mapping_info.get('system')
                    
            elif datatype == 'CodeableConcept':
                if 'code' in mapping_info:
                    parameters['code'] = mapping_info.get('code')
                if 'system' in mapping_info:
                    parameters['system'] = mapping_info.get('system')
                if 'display' in mapping_info:
                    parameters['display'] = mapping_info.get('display')
                    
            mapper = FieldMapper(mapping_type=FieldMapperTypes.FHIR_DATATYPE, parameters=parameters)
            
        else:
            # Skip unsupported mapping types
            continue
        
        resource_mapper.add_mapping(target_field, mapper)
    
    return resource_mapper


def convert_finalized_mappings_to_resource_mappers(finalized_mappings: Dict[str, Dict[str, Dict[str, Any]]],
                                                 df: pd.DataFrame) -> Dict[str, ResourceMapper]:
    """
    Convert finalized mappings to ResourceMapper instances.
    
    Args:
        finalized_mappings: Dictionary of finalized mappings
        df: The source DataFrame
        
    Returns:
        Dictionary of ResourceMapper instances
    """
    resource_mappers = {}
    
    for resource_type, fields in finalized_mappings.items():
        mappings = {}
        
        for field, mapping_info in fields.items():
            source_column = mapping_info['column']
            
            # Create a simple direct mapping for each field
            mappings[field] = {
                'type': FieldMapperTypes.DIRECT,
                'source_field': source_column
            }
            
            # Add type-specific transformations based on column data type
            if source_column in df.columns:
                # Check if this is a date column
                if pd.api.types.is_datetime64_any_dtype(df[source_column]):
                    mappings[field] = {
                        'type': FieldMapperTypes.DATE_FORMAT,
                        'source_field': source_column,
                        'input_format': None,  # Auto-detect
                        'output_format': '%Y-%m-%d'
                    }
                
                # Handle FHIR complex datatypes based on field path
                # Patient.name --> HumanName
                elif field == 'name' and resource_type == 'Patient':
                    # Use a full name field if only one column, otherwise try to find name parts
                    mappings[field] = {
                        'type': FieldMapperTypes.FHIR_DATATYPE,
                        'datatype': 'HumanName',
                        'full_name': source_column
                    }
                
                # Patient.address --> Address
                elif field == 'address' and resource_type == 'Patient':
                    mappings[field] = {
                        'type': FieldMapperTypes.FHIR_DATATYPE,
                        'datatype': 'Address',
                        'full_address': source_column
                    }
                
                # Patient.telecom --> ContactPoint
                elif field == 'telecom' and resource_type == 'Patient':
                    # Detect if this is a phone or email
                    if any(phone_term in source_column.lower() for phone_term in ['phone', 'tel', 'mobile', 'cell']):
                        mappings[field] = {
                            'type': FieldMapperTypes.FHIR_DATATYPE,
                            'datatype': 'ContactPoint',
                            'value': source_column,
                            'system': 'phone'
                        }
                    elif any(email_term in source_column.lower() for email_term in ['email', 'mail']):
                        mappings[field] = {
                            'type': FieldMapperTypes.FHIR_DATATYPE,
                            'datatype': 'ContactPoint',
                            'value': source_column,
                            'system': 'email'
                        }
                    else:
                        mappings[field] = {
                            'type': FieldMapperTypes.FHIR_DATATYPE,
                            'datatype': 'ContactPoint',
                            'value': source_column
                        }
                
                # Patient.identifier --> Identifier
                elif field == 'identifier' and resource_type == 'Patient':
                    mappings[field] = {
                        'type': FieldMapperTypes.FHIR_DATATYPE,
                        'datatype': 'Identifier',
                        'value': source_column
                    }
                
                # Condition.code, Observation.code, etc. --> CodeableConcept
                elif field == 'code' and resource_type in ['Condition', 'Observation', 'Procedure', 'Medication']:
                    mappings[field] = {
                        'type': FieldMapperTypes.FHIR_DATATYPE,
                        'datatype': 'CodeableConcept',
                        'code': source_column
                    }
                
                # Add more type-specific transformations as needed
            
        # Create a ResourceMapper from these mappings
        resource_mappers[resource_type] = create_resource_mapper_from_mappings(
            resource_type, mappings
        )
    
    return resource_mappers


def apply_resource_mappers(resource_mappers: Dict[str, ResourceMapper], 
                         df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply resource mappers to transform data.
    
    Args:
        resource_mappers: Dictionary of ResourceMapper instances
        df: The source DataFrame
        
    Returns:
        Dictionary of transformed resources
    """
    result = {}
    
    # Convert DataFrame to list of dictionaries
    records = df.to_dict('records')
    
    # Apply each resource mapper to each row
    for resource_type, mapper in resource_mappers.items():
        result[resource_type] = []
        
        for record in records:
            transformed = mapper.transform(record)
            result[resource_type].append(transformed)
    
    return result


def generate_enhanced_mapping_code(finalized_mappings: Dict[str, Dict[str, Dict[str, Any]]],
                               df: pd.DataFrame,
                               fhir_standard: str) -> str:
    """
    Generate Python code using enhanced mapper approach.
    
    Args:
        finalized_mappings: Dictionary of finalized mappings
        df: The source DataFrame
        fhir_standard: The FHIR standard being used
        
    Returns:
        String containing the Python code
    """
    code_lines = [
        "import pandas as pd",
        "import json",
        "from typing import Dict, List, Any, Optional",
        "from datetime import datetime",
        "",
        "# Enhanced pattern-based mapping code",
        f"# Generated for {fhir_standard} standard",
        ""
    ]
    
    # Add code for each resource type
    for resource_type, fields in finalized_mappings.items():
        code_lines.append(f"def map_to_{resource_type.lower()}(row):")
        code_lines.append(f"    \"\"\"Map a data row to a {resource_type} resource.\"\"\"")
        code_lines.append(f"    resource = {{'resourceType': '{resource_type}'}}")
        
        # Add code for each field
        for field, mapping_info in fields.items():
            source_column = mapping_info['column']
            
            # Check if field has nested path
            if "." in field:
                path_parts = field.split(".")
                
                # Generate code to create nested dictionaries
                path_code = []
                current_path = "resource"
                
                for i, part in enumerate(path_parts[:-1]):
                    path_code.append(f"    if '{part}' not in {current_path}:")
                    path_code.append(f"        {current_path}['{part}'] = {{}}")
                    current_path += f"['{part}']"
                
                # Now add the final field
                last_part = path_parts[-1]
                
                # Check column data type for appropriate conversion
                if source_column in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[source_column]) or 'date' in source_column.lower():
                        path_code.append(f"    if pd.notna(row['{source_column}']):")
                        path_code.append(f"        # Convert date format")
                        path_code.append(f"        try:")
                        path_code.append(f"            date_value = pd.to_datetime(row['{source_column}'])")
                        path_code.append(f"            {current_path}['{last_part}'] = date_value.strftime('%Y-%m-%d')")
                        path_code.append(f"        except:")
                        path_code.append(f"            {current_path}['{last_part}'] = row['{source_column}']")
                    elif pd.api.types.is_numeric_dtype(df[source_column]):
                        path_code.append(f"    if pd.notna(row['{source_column}']):")
                        path_code.append(f"        {current_path}['{last_part}'] = float(row['{source_column}'])")
                    else:
                        path_code.append(f"    if pd.notna(row['{source_column}']):")
                        path_code.append(f"        {current_path}['{last_part}'] = row['{source_column}']")
                else:
                    # Default string handling if column not in DataFrame
                    path_code.append(f"    if '{source_column}' in row and pd.notna(row['{source_column}']):")
                    path_code.append(f"        {current_path}['{last_part}'] = row['{source_column}']")
                
                code_lines.extend(path_code)
            
            else:
                # Simple field mapping
                if source_column in df.columns:
                    # Add type-specific handling
                    if pd.api.types.is_datetime64_any_dtype(df[source_column]) or 'date' in source_column.lower():
                        code_lines.append(f"    if pd.notna(row['{source_column}']):")
                        code_lines.append(f"        # Convert date format")
                        code_lines.append(f"        try:")
                        code_lines.append(f"            date_value = pd.to_datetime(row['{source_column}'])")
                        code_lines.append(f"            resource['{field}'] = date_value.strftime('%Y-%m-%d')")
                        code_lines.append(f"        except:")
                        code_lines.append(f"            resource['{field}'] = row['{source_column}']")
                    elif pd.api.types.is_numeric_dtype(df[source_column]):
                        code_lines.append(f"    if pd.notna(row['{source_column}']):")
                        code_lines.append(f"        resource['{field}'] = float(row['{source_column}'])")
                    else:
                        code_lines.append(f"    if pd.notna(row['{source_column}']):")
                        code_lines.append(f"        resource['{field}'] = row['{source_column}']")
                else:
                    # Default string handling
                    code_lines.append(f"    if '{source_column}' in row and pd.notna(row['{source_column}']):")
                    code_lines.append(f"        resource['{field}'] = row['{source_column}']")
        
        code_lines.append("    return resource")
        code_lines.append("")
    
    # Add main processing function
    code_lines.append("def transform_data(df):")
    code_lines.append("    \"\"\"Transform the DataFrame to FHIR resources.\"\"\"")
    code_lines.append("    result = {}")
    
    for resource_type in finalized_mappings.keys():
        code_lines.append(f"    ")
        code_lines.append(f"    # Transform to {resource_type} resources")
        code_lines.append(f"    {resource_type.lower()}_resources = []")
        code_lines.append(f"    for _, row in df.iterrows():")
        code_lines.append(f"        resource = map_to_{resource_type.lower()}(row)")
        code_lines.append(f"        {resource_type.lower()}_resources.append(resource)")
        code_lines.append(f"    result['{resource_type}'] = {resource_type.lower()}_resources")
    
    code_lines.append("    ")
    code_lines.append("    return result")
    code_lines.append("")
    
    # Add usage example
    code_lines.append("# Example usage:")
    code_lines.append("# import pandas as pd")
    code_lines.append("# df = pd.read_csv('your_data.csv')")
    code_lines.append("# fhir_resources = transform_data(df)")
    code_lines.append("# print(json.dumps(fhir_resources, indent=2))")
    
    return "\n".join(code_lines)


def discover_field_patterns(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Discover field patterns in the DataFrame to suggest transformations.
    
    Args:
        df: The source DataFrame
        
    Returns:
        Dictionary of column patterns and potential transformations
    """
    patterns = {}
    
    for column in df.columns:
        column_info = {
            "data_type": str(df[column].dtype),
            "transformations": []
        }
        
        # Skip columns with all NaN values
        if df[column].isna().all():
            patterns[column] = column_info
            continue
        
        # Check for date patterns
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            column_info["transformations"].append({
                "type": FieldMapperTypes.DATE_FORMAT,
                "confidence": 0.9
            })
        elif "date" in column.lower() or "time" in column.lower() or "dt" in column.lower():
            # Try to parse as date
            try:
                sample = df[column].dropna().iloc[0]
                pd.to_datetime(sample)
                column_info["transformations"].append({
                    "type": FieldMapperTypes.DATE_FORMAT,
                    "confidence": 0.8
                })
            except:
                pass
        
        # Check for code patterns
        if any(code_system in column.lower() for code_system in ["icd", "cpt", "loinc", "snomed", "rxnorm", "ndc"]):
            column_info["transformations"].append({
                "type": FieldMapperTypes.CODE_LOOKUP,
                "confidence": 0.8,
                "suggested_code_system": next((cs for cs in ["icd", "cpt", "loinc", "snomed", "rxnorm", "ndc"] 
                                              if cs in column.lower()), None)
            })
        
        # Check for ID patterns
        if "id" in column.lower() or column.lower().endswith("id") or "identifier" in column.lower():
            column_info["transformations"].append({
                "type": "identifier",
                "confidence": 0.7
            })
        
        # Check for concatenated values
        sample_values = df[column].dropna().astype(str).head(10).tolist()
        separators = [" ", ",", "-", "_", "|", "/"]
        for sep in separators:
            if any(sep in str(val) for val in sample_values):
                column_info["transformations"].append({
                    "type": FieldMapperTypes.SPLIT,
                    "confidence": 0.6,
                    "separator": sep
                })
                break
        
        patterns[column] = column_info
    
    return patterns