import pandas as pd
import numpy as np
import streamlit as st
import json
from io import StringIO
import csv

def load_data(uploaded_file):
    """
    Load data from various file formats into a pandas DataFrame.
    
    Args:
        uploaded_file: The file uploaded by the user
    
    Returns:
        pandas DataFrame containing the loaded data
    """
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_extension == 'csv':
            df = pd.read_csv(uploaded_file)
        elif file_extension == 'xlsx' or file_extension == 'xls':
            try:
                # First attempt with default engine
                df = pd.read_excel(uploaded_file)
            except Exception as excel_err:
                try:
                    # Try with openpyxl engine if default fails
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                except Exception as openpyxl_err:
                    try:
                        # Last attempt with xlrd engine
                        df = pd.read_excel(uploaded_file, engine='xlrd')
                    except Exception as xlrd_err:
                        raise ValueError(f"Failed to read Excel file. Please ensure it's not corrupted. Error: {str(excel_err)}")
        elif file_extension == 'json':
            # Handle both JSON lines and regular JSON
            try:
                df = pd.read_json(uploaded_file)
            except ValueError:
                # Try as JSON lines
                df = pd.read_json(uploaded_file, lines=True)
        elif file_extension == 'txt':
            # Try to infer the format for text files
            # First try as CSV
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            except:
                # If that fails, try as fixed width
                try:
                    df = pd.read_fwf(uploaded_file)
                except:
                    raise ValueError("Could not parse text file format.")
        elif file_extension == 'xml':
            # For XML, we'll use pandas.read_xml if it's available (pandas >= 1.3.0)
            if hasattr(pd, 'read_xml'):
                df = pd.read_xml(uploaded_file)
            else:
                raise ValueError("XML parsing requires pandas >= 1.3.0")
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def profile_data(df):
    """
    Generate profiling statistics for the DataFrame.
    
    Args:
        df: pandas DataFrame to profile
    
    Returns:
        dict containing profiling statistics
    """
    if df is None or df.empty:
        return None
    
    profile = {}
    
    # Basic statistics
    profile['row_count'] = len(df)
    profile['column_count'] = len(df.columns)
    
    # Column-level statistics
    column_stats = {}
    for column in df.columns:
        col_stats = {}
        
        # Data type
        col_stats['dtype'] = str(df[column].dtype)
        
        # Missing values
        missing_count = df[column].isna().sum()
        col_stats['missing_count'] = int(missing_count)
        col_stats['missing_percentage'] = round((missing_count / len(df)) * 100, 2)
        
        # Unique values
        unique_count = df[column].nunique()
        col_stats['unique_count'] = int(unique_count)
        col_stats['unique_percentage'] = round((unique_count / len(df)) * 100, 2)
        
        # For numeric columns
        if np.issubdtype(df[column].dtype, np.number):
            col_stats['min'] = float(df[column].min()) if not pd.isna(df[column].min()) else None
            col_stats['max'] = float(df[column].max()) if not pd.isna(df[column].max()) else None
            col_stats['mean'] = float(df[column].mean()) if not pd.isna(df[column].mean()) else None
            col_stats['median'] = float(df[column].median()) if not pd.isna(df[column].median()) else None
            col_stats['std'] = float(df[column].std()) if not pd.isna(df[column].std()) else None
        
        # For string/object columns
        elif df[column].dtype == 'object':
            # Sample values (first 5 non-null)
            sample_values = df[column].dropna().unique()[:5].tolist()
            col_stats['sample_values'] = [str(val) for val in sample_values]
            
            # Check for potential date fields
            date_score = 0
            non_null_values = df[column].dropna()
            
            if len(non_null_values) > 0:
                # Check if values contain date-like patterns
                sample = non_null_values.iloc[0]
                if isinstance(sample, str):
                    if "/" in sample or "-" in sample:
                        date_score += 0.5
                    if any(m in sample.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                        date_score += 0.5
                
                # Try parsing as date
                try:
                    pd.to_datetime(non_null_values.iloc[:100], errors='raise')
                    date_score += 1
                except:
                    pass
            
            col_stats['potential_date_field'] = date_score > 0.5
        
        column_stats[column] = col_stats
    
    profile['column_stats'] = column_stats
    
    return profile

def detect_id_columns(df):
    """
    Identify columns that likely contain identifier information.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        list of column names that are likely identifiers
    """
    id_columns = []
    
    for column in df.columns:
        # Check if column name contains 'id' or 'key'
        if 'id' in column.lower() or 'key' in column.lower() or 'guid' in column.lower() or 'uuid' in column.lower():
            id_columns.append(column)
            continue
        
        # Check if column has high cardinality (many unique values)
        if df[column].nunique() > 0.8 * len(df) and len(df) > 10:
            id_columns.append(column)
    
    return id_columns

def detect_date_columns(df):
    """
    Identify columns that likely contain date information.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        list of column names that are likely dates
    """
    date_columns = []
    
    for column in df.columns:
        # Check if already a datetime
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            date_columns.append(column)
            continue
            
        # Check column name for date indicators
        if any(date_term in column.lower() for date_term in ['date', 'time', 'day', 'year', 'month', 'dob', 'birth']):
            # Try to convert to datetime
            try:
                # Only try with a sample to avoid performance issues
                sample = df[column].dropna().head(100)
                if len(sample) > 0:
                    pd.to_datetime(sample, errors='raise')
                    date_columns.append(column)
            except:
                pass
    
    return date_columns

def suggest_data_quality_improvements(df, profile):
    """
    Suggest potential data quality improvements based on profiling.
    
    Args:
        df: pandas DataFrame
        profile: data profile dictionary
        
    Returns:
        list of suggestions
    """
    suggestions = []
    
    # Check for missing values
    columns_with_missing = [col for col, stats in profile['column_stats'].items() 
                           if stats['missing_count'] > 0]
    
    if columns_with_missing:
        missing_counts = {col: profile['column_stats'][col]['missing_count'] 
                         for col in columns_with_missing}
        high_missing = [col for col, count in missing_counts.items() 
                       if count / profile['row_count'] > 0.2]
        
        if high_missing:
            suggestions.append(f"High missing values (>20%) in columns: {', '.join(high_missing)}")
    
    # Check for potential ID columns
    id_columns = detect_id_columns(df)
    if id_columns:
        suggestions.append(f"Potential ID columns detected: {', '.join(id_columns)}")
    
    # Check for potential date columns
    date_columns = detect_date_columns(df)
    if date_columns:
        suggestions.append(f"Potential date columns detected: {', '.join(date_columns)}")
    
    # Check for potential duplicates
    if len(df) != len(df.drop_duplicates()):
        suggestions.append(f"Dataset contains {len(df) - len(df.drop_duplicates())} duplicate rows")
    
    return suggestions
