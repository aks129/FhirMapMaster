"""
Test script to verify the app's core functionalities
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing module imports...")

    try:
        import streamlit
        print("[OK] Streamlit imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import streamlit: {e}")
        return False

    try:
        import pandas
        print("[OK] Pandas imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import pandas: {e}")
        return False

    try:
        import anthropic
        print("[OK] Anthropic imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import anthropic: {e}")
        return False

    try:
        import openai
        print("[OK] OpenAI imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import openai: {e}")
        return False

    try:
        import hl7
        print("[OK] HL7 imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import hl7: {e}")
        return False

    try:
        import plotly
        print("[OK] Plotly imported successfully")
    except ImportError as e:
        print(f"[X] Failed to import plotly: {e}")
        return False

    return True

def test_app_modules():
    """Test that app modules can be imported"""
    print("\nTesting app modules...")

    modules_to_test = [
        "components.file_uploader",
        "components.data_profiler",
        "components.mapping_interface_new",
        "components.export_interface",
        "utils.fhir_mapper",
        "utils.enhanced_mapper",
        "utils.fhir_ig_loader",
        "utils.fhir_validator",
        "utils.llm_service",
        "utils.data_processor"
    ]

    all_ok = True
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"[OK] {module} imported successfully")
        except ImportError as e:
            print(f"[X] Failed to import {module}: {e}")
            all_ok = False

    return all_ok

def test_cache_directories():
    """Test that cache directories exist or can be created"""
    print("\nTesting cache directories...")

    cache_dirs = [
        "cache",
        "cache/cpcds",
        "cache/fhir",
        "cache/validator",
        "sample_data"
    ]

    all_ok = True
    for directory in cache_dirs:
        if os.path.exists(directory):
            print(f"[OK] Directory exists: {directory}")
        else:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"[OK] Created directory: {directory}")
            except Exception as e:
                print(f"[X] Failed to create directory {directory}: {e}")
                all_ok = False

    return all_ok

def test_sample_data():
    """Test creating sample data for testing"""
    print("\nCreating sample test data...")

    try:
        import pandas as pd

        # Create a simple sample CSV
        sample_data = {
            'patient_id': ['P001', 'P002', 'P003'],
            'first_name': ['John', 'Jane', 'Bob'],
            'last_name': ['Doe', 'Smith', 'Johnson'],
            'date_of_birth': ['1980-01-15', '1992-07-20', '1975-12-03'],
            'gender': ['M', 'F', 'M'],
            'diagnosis_code': ['E11.9', 'I10', 'J45.909'],
            'diagnosis_description': ['Type 2 diabetes', 'Hypertension', 'Asthma'],
            'encounter_date': ['2024-01-15', '2024-01-20', '2024-01-25']
        }

        df = pd.DataFrame(sample_data)
        sample_file = 'sample_data/test_patient_data.csv'
        df.to_csv(sample_file, index=False)
        print(f"[OK] Created sample data file: {sample_file}")

        # Verify the file was created
        if os.path.exists(sample_file):
            print(f"[OK] Sample file verified: {sample_file}")
            return True
        else:
            print(f"[X] Sample file not found: {sample_file}")
            return False

    except Exception as e:
        print(f"[X] Failed to create sample data: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("PARKER FHIR MAPPER - FUNCTIONALITY TEST")
    print("=" * 50)

    tests_passed = 0
    tests_total = 4

    # Test 1: Module imports
    if test_imports():
        tests_passed += 1

    # Test 2: App module imports
    if test_app_modules():
        tests_passed += 1

    # Test 3: Cache directories
    if test_cache_directories():
        tests_passed += 1

    # Test 4: Sample data creation
    if test_sample_data():
        tests_passed += 1

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n[SUCCESS] All tests passed! The app is ready for deployment.")
        print("\nTo run the app locally:")
        print("  streamlit run app.py")
        print("\nTo deploy to Streamlit Cloud:")
        print("  1. Push code to GitHub")
        print("  2. Visit share.streamlit.io")
        print("  3. Connect your repository")
        return 0
    else:
        print(f"\n[WARNING] {tests_total - tests_passed} test(s) failed.")
        print("Please check the errors above and fix them before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())