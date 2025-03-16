"""
FHIR Datatypes Module

This module provides Python classes for FHIR complex datatypes like HumanName, Address, etc.
These classes help with proper conversion from source data to FHIR structured types.
"""

from typing import Dict, List, Any, Optional, Union
import re


class FHIRDatatype:
    """Base class for all FHIR datatypes."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        raise NotImplementedError("Subclasses must implement to_dict()")


class HumanName(FHIRDatatype):
    """
    FHIR HumanName datatype.
    
    Structure:
    {
      "use" : "<code>",     // usual | official | temp | nickname | anonymous | old | maiden
      "text" : "<string>",  // Text representation of the full name
      "family" : "<string>",
      "given" : ["<string>"],
      "prefix" : ["<string>"],
      "suffix" : ["<string>"],
      "period" : { Period }
    }
    """
    
    def __init__(self, 
                family: Optional[str] = None,
                given: Optional[Union[str, List[str]]] = None,
                prefix: Optional[Union[str, List[str]]] = None,
                suffix: Optional[Union[str, List[str]]] = None,
                text: Optional[str] = None,
                use: Optional[str] = None):
        """
        Initialize a HumanName.
        
        Args:
            family: Family name (often called 'Surname')
            given: Given names (including middle names)
            prefix: Parts that come before the name
            suffix: Parts that come after the name
            text: Text representation of the full name
            use: Purpose of this name
        """
        self.family = family
        
        # Handle given names as a list
        if isinstance(given, str):
            # Split on spaces but keep quoted parts together
            self.given = [g.strip() for g in given.split()]
        else:
            self.given = given or []
            
        # Handle prefix as a list
        if isinstance(prefix, str):
            self.prefix = [prefix]
        else:
            self.prefix = prefix or []
            
        # Handle suffix as a list
        if isinstance(suffix, str):
            self.suffix = [suffix]
        else:
            self.suffix = suffix or []
            
        self.text = text
        self.use = use
        
    @classmethod
    def from_parts(cls, 
                  first_name: Optional[str] = None,
                  middle_name: Optional[str] = None,
                  last_name: Optional[str] = None,
                  prefix: Optional[str] = None,
                  suffix: Optional[str] = None,
                  use: Optional[str] = None) -> 'HumanName':
        """
        Create a HumanName from standard name parts.
        
        Args:
            first_name: Person's first name
            middle_name: Person's middle name
            last_name: Person's last name (family name)
            prefix: Title or prefixes (Dr, Mrs, etc)
            suffix: Suffixes (Jr, Sr, etc)
            use: Purpose of this name
            
        Returns:
            HumanName instance
        """
        given = []
        if first_name:
            given.append(first_name)
        if middle_name:
            given.append(middle_name)
            
        # Construct the text representation
        text_parts = []
        if prefix:
            text_parts.append(prefix)
        if first_name:
            text_parts.append(first_name)
        if middle_name:
            text_parts.append(middle_name)
        if last_name:
            text_parts.append(last_name)
        if suffix:
            text_parts.append(suffix)
            
        text = " ".join(text_parts) if text_parts else None
        
        return cls(
            family=last_name,
            given=given,
            prefix=[prefix] if prefix else None,
            suffix=[suffix] if suffix else None,
            text=text,
            use=use
        )
    
    @classmethod
    def from_full_name(cls, full_name: str, use: Optional[str] = None) -> 'HumanName':
        """
        Create a HumanName from a full name string.
        Attempts to parse the components based on common patterns.
        
        Args:
            full_name: Full name string
            use: Purpose of this name (usually 'official')
            
        Returns:
            HumanName instance
        """
        if not full_name:
            return cls(use=use)
            
        # Store original text
        text = full_name.strip()
        
        # Extract common prefixes first
        prefix_pattern = r'^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Rev\.)\s+'
        prefix_match = re.match(prefix_pattern, text, re.IGNORECASE)
        prefix = None
        if prefix_match:
            prefix = prefix_match.group(1)
            text = text[len(prefix_match.group(0)):]
            
        # Extract common suffixes
        suffix_pattern = r'\s+(Jr\.|Sr\.|I|II|III|IV|V|MD|PhD|Esq\.)$'
        suffix_match = re.search(suffix_pattern, text, re.IGNORECASE)
        suffix = None
        if suffix_match:
            suffix = suffix_match.group(1)
            text = text[:text.rfind(suffix_match.group(0))]
            
        # Split remaining text
        parts = text.strip().split()
        
        if len(parts) == 1:
            # Just one part, assume it's the first name
            return cls(
                given=[parts[0]],
                prefix=[prefix] if prefix else None,
                suffix=[suffix] if suffix else None,
                text=full_name,
                use=use
            )
        elif len(parts) == 2:
            # Likely first and last name
            return cls(
                family=parts[1],
                given=[parts[0]],
                prefix=[prefix] if prefix else None,
                suffix=[suffix] if suffix else None,
                text=full_name,
                use=use
            )
        else:
            # Multiple parts - assume last part is family name and others are given names
            family = parts[-1]
            given = parts[:-1]
            
            return cls(
                family=family,
                given=given,
                prefix=[prefix] if prefix else None,
                suffix=[suffix] if suffix else None,
                text=full_name,
                use=use
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        result = {}
        
        if self.family:
            result['family'] = self.family
            
        if self.given:
            result['given'] = self.given
            
        if self.prefix:
            result['prefix'] = self.prefix
            
        if self.suffix:
            result['suffix'] = self.suffix
            
        if self.text:
            result['text'] = self.text
            
        if self.use:
            result['use'] = self.use
            
        return result


class Address(FHIRDatatype):
    """
    FHIR Address datatype.
    
    Structure:
    {
      "use" : "<code>",          // home | work | temp | old | billing
      "type" : "<code>",         // postal | physical | both
      "text" : "<string>",       // Text representation of the address
      "line" : ["<string>"],     // Street name, number, direction & P.O. Box etc.
      "city" : "<string>",       // Name of city, town etc.
      "district" : "<string>",   // District name (aka county)
      "state" : "<string>",      // Sub-unit of country (abbreviations ok)
      "postalCode" : "<string>", // Postal code for area
      "country" : "<string>",    // Country (e.g. can be ISO 3166 2 or 3 letter code)
      "period" : { Period }      // Time period when address was/is in use
    }
    """
    
    def __init__(self,
                line: Optional[Union[str, List[str]]] = None,
                city: Optional[str] = None,
                district: Optional[str] = None,
                state: Optional[str] = None,
                postalCode: Optional[str] = None,
                country: Optional[str] = None,
                text: Optional[str] = None,
                use: Optional[str] = None,
                type: Optional[str] = None):
        """
        Initialize an Address.
        
        Args:
            line: Street name, number, direction & P.O. Box etc.
            city: Name of city, town etc.
            district: District name (aka county)
            state: Sub-unit of country (abbreviations ok)
            postalCode: Postal code for area
            country: Country (e.g. can be ISO 3166 2 or 3 letter code)
            text: Text representation of the address
            use: Purpose of this address
            type: postal | physical | both
        """
        # Handle address lines as a list
        if isinstance(line, str):
            self.line = [line]
        else:
            self.line = line or []
            
        self.city = city
        self.district = district
        self.state = state
        self.postalCode = postalCode
        self.country = country
        self.text = text
        self.use = use
        self.type = type
        
    @classmethod
    def from_parts(cls,
                  street_address: Optional[Union[str, List[str]]] = None,
                  city: Optional[str] = None,
                  state: Optional[str] = None,
                  postal_code: Optional[str] = None,
                  country: Optional[str] = None,
                  use: Optional[str] = None) -> 'Address':
        """
        Create an Address from standard address parts.
        
        Args:
            street_address: Street address, can be a string or list of lines
            city: City
            state: State or province
            postal_code: ZIP or postal code
            country: Country
            use: Purpose of this address (home, work, etc.)
            
        Returns:
            Address instance
        """
        # Handle street address as a string or list
        lines = []
        if isinstance(street_address, str):
            # Split on newlines
            lines = [line.strip() for line in street_address.split('\n')]
        elif street_address:
            lines = street_address
            
        # Construct the text representation
        text_parts = []
        if lines:
            text_parts.extend(lines)
        if city and state:
            text_parts.append(f"{city}, {state}")
        elif city:
            text_parts.append(city)
        elif state:
            text_parts.append(state)
            
        if postal_code:
            if text_parts:
                text_parts[-1] = f"{text_parts[-1]} {postal_code}"
            else:
                text_parts.append(postal_code)
                
        if country:
            text_parts.append(country)
            
        text = "\n".join(text_parts) if text_parts else None
        
        return cls(
            line=lines,
            city=city,
            state=state,
            postalCode=postal_code,
            country=country,
            text=text,
            use=use
        )
    
    @classmethod
    def from_single_string(cls, address_text: str, use: Optional[str] = None) -> 'Address':
        """
        Create an Address from a single address string.
        Attempts to parse the components based on common patterns.
        
        Args:
            address_text: Full address string
            use: Purpose of this address (home, work, etc.)
            
        Returns:
            Address instance
        """
        if not address_text:
            return cls(use=use)
            
        # Store original text
        text = address_text.strip()
        
        # Try to parse address components
        # This is a simple approach and may not work for all address formats
        lines = [line.strip() for line in text.split('\n')]
        
        if len(lines) == 1:
            # Try to parse from a comma-separated format
            parts = [p.strip() for p in lines[0].split(',')]
            
            if len(parts) >= 3:
                # Assume format: "street, city, state postal_code"
                street = parts[0]
                city = parts[1]
                
                # Try to extract state and postal code
                state_zip = parts[2].split()
                state = state_zip[0] if state_zip else None
                postal_code = state_zip[1] if len(state_zip) > 1 else None
                
                # Country might be in the last part
                country = parts[3] if len(parts) > 3 else None
                
                return cls(
                    line=[street],
                    city=city,
                    state=state,
                    postalCode=postal_code,
                    country=country,
                    text=text,
                    use=use
                )
            else:
                # Just use as a single line
                return cls(
                    line=[lines[0]],
                    text=text,
                    use=use
                )
        else:
            # Multiple lines - try to parse
            line_parts = []
            city = None
            state = None
            postal_code = None
            country = None
            
            # Assume last line contains city, state, zip
            if len(lines) >= 2:
                csz_parts = lines[-1].split(',')
                
                if len(csz_parts) >= 2:
                    city = csz_parts[0].strip()
                    state_zip = csz_parts[1].strip().split()
                    
                    if state_zip:
                        state = state_zip[0]
                        if len(state_zip) > 1:
                            postal_code = state_zip[1]
                            
                # Check if there might be a country line
                if len(lines) >= 3:
                    country = lines[-1]
                    # Use lines except the last two
                    line_parts = lines[:-2]
                else:
                    # Use lines except the last one
                    line_parts = lines[:-1]
            else:
                line_parts = lines
                
            return cls(
                line=line_parts,
                city=city,
                state=state,
                postalCode=postal_code,
                country=country,
                text=text,
                use=use
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        result = {}
        
        if self.line:
            result['line'] = self.line
            
        if self.city:
            result['city'] = self.city
            
        if self.district:
            result['district'] = self.district
            
        if self.state:
            result['state'] = self.state
            
        if self.postalCode:
            result['postalCode'] = self.postalCode
            
        if self.country:
            result['country'] = self.country
            
        if self.text:
            result['text'] = self.text
            
        if self.use:
            result['use'] = self.use
            
        if self.type:
            result['type'] = self.type
            
        return result


class ContactPoint(FHIRDatatype):
    """
    FHIR ContactPoint datatype.
    
    Structure:
    {
      "system" : "<code>",      // phone | fax | email | pager | url | sms | other
      "value" : "<string>",
      "use" : "<code>",         // home | work | temp | old | mobile
      "rank" : "<positiveInt>", // Specify preferred order of use (1 = highest)
      "period" : { Period }     // Time period when the contact point was/is in use
    }
    """
    
    def __init__(self,
                value: Optional[str] = None,
                system: Optional[str] = None,
                use: Optional[str] = None,
                rank: Optional[int] = None):
        """
        Initialize a ContactPoint.
        
        Args:
            value: The contact value (e.g., phone number, email address)
            system: The type of contact system (phone, email, etc.)
            use: Purpose of this contact point (home, work, etc.)
            rank: Preference order for this contact point
        """
        self.value = value
        self.system = system
        self.use = use
        self.rank = rank
        
    @classmethod
    def from_value(cls, value: str) -> 'ContactPoint':
        """
        Create a ContactPoint inferring the system from the value format.
        
        Args:
            value: Contact value (phone number, email, etc.)
            
        Returns:
            ContactPoint instance
        """
        if not value:
            return cls()
            
        # Try to determine system
        if '@' in value:
            return cls(value=value, system='email')
        elif value.startswith('http') or value.startswith('www'):
            return cls(value=value, system='url')
        elif re.match(r'^\+?[\d\-\(\)\s]+$', value):
            # Looks like a phone number
            return cls(value=value, system='phone')
        else:
            return cls(value=value)
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        result = {}
        
        if self.value:
            result['value'] = self.value
            
        if self.system:
            result['system'] = self.system
            
        if self.use:
            result['use'] = self.use
            
        if self.rank is not None:
            result['rank'] = self.rank
            
        return result


class Identifier(FHIRDatatype):
    """
    FHIR Identifier datatype.
    
    Structure:
    {
      "use" : "<code>",            // usual | official | temp | secondary | old (If known)
      "type" : { CodeableConcept },// Description of identifier
      "system" : "<uri>",          // The namespace for the identifier value
      "value" : "<string>",        // The value that is unique
      "period" : { Period },       // Time period when id is/was valid for use
      "assigner" : { Reference }   // Organization that issued id (may be just text)
    }
    """
    
    def __init__(self,
                value: Optional[str] = None,
                system: Optional[str] = None,
                use: Optional[str] = None):
        """
        Initialize an Identifier.
        
        Args:
            value: The identifier value
            system: The identifier system (URI or namespace)
            use: Purpose of this identifier
        """
        self.value = value
        self.system = system
        self.use = use
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        result = {}
        
        if self.value:
            result['value'] = self.value
            
        if self.system:
            result['system'] = self.system
            
        if self.use:
            result['use'] = self.use
            
        return result


class CodeableConcept(FHIRDatatype):
    """
    FHIR CodeableConcept datatype.
    
    Structure:
    {
      "coding" : [{ Coding }],
      "text" : "<string>"
    }
    """
    
    def __init__(self,
                coding: Optional[List[Dict[str, str]]] = None,
                text: Optional[str] = None):
        """
        Initialize a CodeableConcept.
        
        Args:
            coding: List of codings
            text: Plain text representation
        """
        self.coding = coding or []
        self.text = text
        
    @classmethod
    def from_code(cls, code: str, system: Optional[str] = None, display: Optional[str] = None) -> 'CodeableConcept':
        """
        Create a CodeableConcept from a single code.
        
        Args:
            code: The code value
            system: The code system
            display: The display text
            
        Returns:
            CodeableConcept instance
        """
        coding = [{
            'code': code
        }]
        
        if system:
            coding[0]['system'] = system
            
        if display:
            coding[0]['display'] = display
            
        return cls(coding=coding, text=display)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR JSON representation."""
        result = {}
        
        if self.coding:
            result['coding'] = self.coding
            
        if self.text:
            result['text'] = self.text
            
        return result


# Note: More datatypes could be added as needed:
# - Quantity
# - Period
# - Range
# - Attachment
# - Reference
# etc.