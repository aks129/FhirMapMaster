import streamlit as st
import json
from utils.fhir_mapping_language import generate_fml_structure_map, generate_cql_accessors, generate_liquid_templates

def render_fml_viewer(mappings, df, fhir_standard):
    """
    Render a detailed view of the FHIR Mapping Language artifacts.
    
    Args:
        mappings: Dict containing the finalized mappings
        df: The DataFrame containing the data
        fhir_standard: The FHIR standard being used
    """
    st.markdown("""
    ## 🕸️ FHIR Mapping Language Artifacts
    
    Parker has generated the following FHIR Mapping Language (FML) artifacts for your mapping.
    These artifacts follow the official HL7 FHIR mapping specifications.
    """)
    
    # Generate FML artifacts
    source_structure_name = "SourceData"
    structure_map = generate_fml_structure_map(mappings, df, source_structure_name, fhir_standard)
    cql_accessors = generate_cql_accessors(mappings, source_structure_name, fhir_standard)
    liquid_templates = generate_liquid_templates(mappings, fhir_standard)
    
    # Create tabs for different artifacts
    tabs = st.tabs([
        "Structure Map", 
        "CQL Accessors", 
        "Liquid Templates", 
        "About FML"
    ])
    
    # Structure Map tab
    with tabs[0]:
        st.markdown("""
        ### Structure Map
        
        The Structure Map is the core FHIR artifact for defining mappings. It uses FHIR's mapping language
        to express transformations from your source data to FHIR resources.
        """)
        st.code(structure_map, language="text")
        
        with st.expander("📚 How to use the Structure Map"):
            st.markdown("""
            **Using the Structure Map with a FHIR Server:**
            
            1. Convert this Structure Map to JSON format
            2. POST it to a FHIR server's StructureMap endpoint
            3. Use the `$transform` operation to apply the mapping to your data
            
            **Example with the HAPI FHIR server:**
            
            ```bash
            # Save the mapping as structuremap.json
            curl -X POST -H "Content-Type: application/json" \\
              -d @structuremap.json \\
              http://hapi.fhir.org/baseR4/StructureMap
              
            # Apply the mapping to your data
            curl -X POST -H "Content-Type: application/json" \\
              -d @your_data.json \\
              "http://hapi.fhir.org/baseR4/StructureMap/source-data-to-fhir/$transform"
            ```
            """)
    
    # CQL Accessors tab
    with tabs[1]:
        st.markdown("""
        ### Clinical Quality Language (CQL) Accessors
        
        CQL is a domain-specific language for expressing clinical quality concepts in a human-readable format.
        These CQL accessors provide functions to retrieve data from your mapped FHIR resources.
        """)
        st.code(cql_accessors, language="text")
        
        with st.expander("📚 How to use CQL Accessors"):
            st.markdown("""
            **Using CQL with a FHIR-based Quality Measure Execution Engine:**
            
            1. Save this CQL to a file
            2. Upload it to a CQL execution engine such as CQL-to-ELM translator
            3. Execute the CQL against your FHIR data
            
            **Example with CQL Execution Library:**
            
            ```javascript
            const cqlEngine = require('cql-execution');
            const elmTranslator = require('cql-elm-translator');
            
            // Translate CQL to ELM
            const elm = elmTranslator.translate(cqlContent);
            
            // Execute against your FHIR data
            const executor = new cqlEngine.Executor(elm);
            const results = executor.exec(patientSource);
            ```
            """)
    
    # Liquid Templates tab
    with tabs[2]:
        st.markdown("""
        ### Liquid Templates
        
        Liquid templates offer a simple syntax for transforming your data into FHIR JSON.
        These templates can be used with template engines that support Liquid syntax.
        """)
        
        # Create sub-tabs for each resource's Liquid template
        resource_tabs = st.tabs(list(liquid_templates.keys()))
        
        for i, resource_name in enumerate(liquid_templates.keys()):
            with resource_tabs[i]:
                st.markdown(f"#### {resource_name} Template")
                st.code(liquid_templates[resource_name], language="json")
        
        with st.expander("📚 How to use Liquid Templates"):
            st.markdown("""
            **Using Liquid Templates with a Template Engine:**
            
            1. Save these templates to files
            2. Process your source data through a Liquid template engine
            
            **Example with JavaScript Liquid Engine:**
            
            ```javascript
            const Liquid = require('liquidjs');
            const engine = new Liquid();
            
            // Load template
            const template = engine.parse(templateContent);
            
            // Process your data through the template
            const result = await engine.render(template, yourData);
            ```
            """)
    
    # About FML tab
    with tabs[3]:
        st.markdown("""
        ### About FHIR Mapping Language
        
        The FHIR Mapping Language is a standards-based approach for defining transformations
        between different data formats and FHIR resources. It's officially defined by HL7 as part
        of the FHIR specification.
        
        **Key Benefits:**
        
        - **Standards-based:** Following official HL7 FHIR specifications
        - **Interoperable:** Compatible with FHIR servers and mapping engines
        - **Executable:** Can be directly used for transformations
        - **Declarative:** Focused on what to map, not how to implement it
        
        **Official Resources:**
        
        - [FHIR Mapping Language Documentation](https://www.hl7.org/fhir/mapping-language.html)
        - [FHIR Structure Map Resource](https://www.hl7.org/fhir/structuremap.html)
        - [FHIR Implementation Guide for Mapping](https://www.hl7.org/fhir/mapping-tutorial.html)
        
        **Tools for Working with FHIR Mappings:**
        
        - [FHIR Mapper](https://github.com/ahdis/fhir-mapper) - Open source mapping engine
        - [Vonk FHIR Server](https://fire.ly/products/vonk/) - Commercial FHIR server with mapping support
        - [HAPI FHIR](https://hapifhir.io/) - Open source Java implementation of FHIR with mapping capabilities
        """)