# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Parker is a FHIR mapping tool that transforms healthcare data from various formats (CSV, HL7 v2, C-CDA, JSON, XML) into FHIR R4B resources. It's a Streamlit-based web application with AI-assisted mapping capabilities using OpenAI and Anthropic LLMs.

## Commands

### Development Setup
```bash
# Install dependencies (using pyproject.toml)
pip install -e .
# OR install specific packages
pip install streamlit pandas anthropic openai hl7 openpyxl plotly trafilatura twilio xlrd

# Run the application
streamlit run app.py --server.port 5000

# Run the test script
python test_cpcds_parser.py
```

### Key Development Commands
- Run app: `streamlit run app.py`
- Test CPCDS parser: `python test_cpcds_parser.py`
- Default port: 5000 (configured in `.streamlit/config.toml`)

## Architecture

### Core Application Flow
1. **File Upload** (`components/file_uploader.py`) - Accepts CSV, Excel, HL7 v2, C-CDA files
2. **Data Profiling** (`components/data_profiler.py`) - Analyzes uploaded data structure
3. **Resource Selection** (`components/resource_selector.py`) - User selects target FHIR resources
4. **Mapping Interface** (`components/mapping_interface_new.py`) - Interactive mapping with AI suggestions
5. **Export** (`components/export_interface.py`) - Generates FHIR bundles/resources

### Key Modules

#### Utils Layer
- `fhir_mapper.py` - Core FHIR resource definitions and mapping logic
- `enhanced_mapper.py` - Pattern-based automated mapping with field transformations
- `fhir_ig_loader.py` - Loads Implementation Guide profiles (US Core, CARIN BB)
- `fhir_validator.py` - Validates generated FHIR resources
- `llm_service.py` - AI mapping suggestions via OpenAI/Anthropic
- `data_processor.py` - Handles different input formats
- `hl7_v2_mapping.py` - HL7 v2 message parsing and mapping
- `ccda_mapping.py` - C-CDA document parsing and mapping
- `cpcds_mapping.py` - CPCDS (Claims data) specific mappings
- `fhir_datatypes.py` - FHIR datatype classes (HumanName, Address, etc.)

#### Session State Management
The app uses Streamlit session state extensively to maintain:
- `uploaded_file` - Current file being processed
- `df` - Parsed dataframe
- `mappings` - User-defined field mappings
- `fhir_standard` - Selected IG (US Core, CARIN BB)
- `llm_suggestions` - AI-generated mapping suggestions

### Data Flow
1. Files uploaded → parsed into pandas DataFrame
2. User selects target FHIR resources and IG version
3. System suggests mappings using pattern matching + LLM
4. User reviews/adjusts mappings via UI
5. Mappings applied to generate FHIR resources
6. Resources validated against selected IG
7. Export as FHIR Bundle or individual resources

## Important Implementation Details

### FHIR Standards Support
- Primary: FHIR R4B
- Implementation Guides:
  - US Core (6.1.0, 7.0.0)
  - CARIN Blue Button (1.0.0, 2.0.0)
  - Custom IGs via StructureDefinition upload

### Mapping Engine
- Uses `enhanced_mapper.py` for field transformations
- Supports multiple mapping types: direct, transform, regex, concat, split, lookup, date_format, template
- FHIR datatype handling via custom classes in `fhir_datatypes.py`

### LLM Integration
- Requires API keys for OpenAI or Anthropic (set via UI)
- Used for intelligent field mapping suggestions
- Fallback to pattern-based matching if LLM unavailable

### Cache Directories
Required directories (auto-created by app):
- `cache/` - General cache
- `cache/cpcds/` - CPCDS mapping files
- `cache/fhir/` - FHIR profiles cache
- `cache/validator/` - Validation cache
- `sample_data/` - Example data files

## Development Notes

- The application is experimental and should NOT be used with PHI data
- Main entry point is `app.py` which orchestrates the Streamlit UI
- Component modules in `components/` handle individual UI sections
- Utility modules in `utils/` provide core functionality
- No formal test suite currently - only `test_cpcds_parser.py` for testing CPCDS mappings
- Uses Streamlit's built-in server configuration (`.streamlit/config.toml`)

## Common Tasks

### Adding New Input Format Support
1. Create parser in `utils/` (e.g., `new_format_mapping.py`)
2. Update `data_processor.py` to recognize format
3. Add UI support in `file_uploader.py`

### Adding New FHIR Resource Support
1. Update resource definitions in `fhir_mapper.py`
2. Add to IG profiles in `fhir_ig_loader.py`
3. Update mapping interface to handle new resource fields

### Modifying Mapping Logic
1. Core logic in `enhanced_mapper.py`
2. Field transformation functions in `FieldMapper` class
3. Pattern matching rules in `PatternBasedMappingSuggester`