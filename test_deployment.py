#!/usr/bin/env python3
"""
Simple deployment test to verify all imports work
Run this to test if the app will deploy successfully to Streamlit Cloud
"""

import sys

def test_basic_imports():
    """Test basic required imports"""
    try:
        import streamlit as st
        print("streamlit imported successfully")
    except ImportError as e:
        print(f"FAIL streamlit import failed: {e}")
        return False

    try:
        import pandas as pd
        print("SUCCESS pandas imported successfully")
    except ImportError as e:
        print(f"FAIL pandas import failed: {e}")
        return False

    try:
        import numpy as np
        print("SUCCESS numpy imported successfully")
    except ImportError as e:
        print("WARN numpy import failed but not critical")

    return True

def test_app_imports():
    """Test main app imports"""
    try:
        from components.file_uploader import render_file_uploader
        print("SUCCESS file_uploader component imported")
    except ImportError as e:
        print(f"FAIL file_uploader import failed: {e}")
        return False

    try:
        from components.data_profiler import render_data_profiler
        print("SUCCESS data_profiler component imported")
    except ImportError as e:
        print(f"FAIL data_profiler import failed: {e}")
        return False

    try:
        from utils.llm_service import initialize_anthropic_client
        print("SUCCESS llm_service imported")
    except ImportError as e:
        print(f"WARN llm_service import failed: {e} (may work in deployment)")

    return True

def test_optional_imports():
    """Test optional imports that should fail gracefully"""
    optional_packages = [
        'anthropic',
        'openai',
        'duckdb',
        'hl7',
        'trafilatura',
        'plotly'
    ]

    for package in optional_packages:
        try:
            __import__(package)
            print(f"SUCCESS {package} available")
        except ImportError:
            print(f"WARN {package} not available (optional)")

if __name__ == "__main__":
    print("Testing Streamlit Cloud deployment compatibility...")
    print("=" * 50)

    success = test_basic_imports()
    if not success:
        print("FAIL Basic imports failed - deployment will fail")
        sys.exit(1)

    success = test_app_imports()
    if not success:
        print("FAIL App imports failed - deployment will fail")
        sys.exit(1)

    test_optional_imports()

    print("=" * 50)
    print("SUCCESS Deployment test completed - basic functionality should work")