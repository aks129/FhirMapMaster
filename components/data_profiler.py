import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_processor import profile_data, detect_id_columns, detect_date_columns, suggest_data_quality_improvements

def render_data_profiler():
    """
    Render the data profiling component.
    """
    st.header("Step 2: Data Profiling")
    
    # Only continue if data exists in session state
    if st.session_state.df is not None:
        df = st.session_state.df
        
        # Generate data profile
        with st.spinner("Analyzing data..."):
            profile = profile_data(df)
            id_columns = detect_id_columns(df)
            date_columns = detect_date_columns(df)
            suggestions = suggest_data_quality_improvements(df, profile)
        
        # Data overview
        st.subheader("Data Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows", profile['row_count'])
        col2.metric("Total Columns", profile['column_count'])
        col3.metric("Potential ID Columns", len(id_columns))
        
        # Column details
        st.subheader("Column Details")
        
        # Create a tab for each column category and a tab for all columns
        tab_all, tab_id, tab_date, tab_other = st.tabs(["All Columns", "ID Columns", "Date Columns", "Other Columns"])
        
        with tab_all:
            show_column_details(df, profile, list(df.columns))
        
        with tab_id:
            if id_columns:
                show_column_details(df, profile, id_columns)
            else:
                st.info("No potential ID columns detected.")
        
        with tab_date:
            if date_columns:
                show_column_details(df, profile, date_columns)
            else:
                st.info("No potential date columns detected.")
        
        with tab_other:
            other_cols = [col for col in df.columns if col not in id_columns and col not in date_columns]
            if other_cols:
                show_column_details(df, profile, other_cols)
            else:
                st.info("No other columns available.")
        
        # Data quality suggestions
        st.subheader("Data Quality Suggestions")
        if suggestions:
            for suggestion in suggestions:
                st.info(suggestion)
        else:
            st.success("No data quality issues detected.")
        
        # Missing values visualization
        st.subheader("Missing Values")
        missing_data = pd.DataFrame({
            'Column': profile['column_stats'].keys(),
            'Missing Count': [stats['missing_count'] for stats in profile['column_stats'].values()],
            'Missing Percentage': [stats['missing_percentage'] for stats in profile['column_stats'].values()]
        })
        missing_data = missing_data.sort_values('Missing Percentage', ascending=False)
        
        if missing_data['Missing Count'].sum() > 0:
            fig = px.bar(
                missing_data,
                x='Column',
                y='Missing Percentage',
                color='Missing Percentage',
                title='Missing Values by Column',
                labels={'Missing Percentage': 'Missing Values (%)'},
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No missing values in the dataset.")
        
        # Data cardinality visualization
        st.subheader("Column Cardinality")
        cardinality_data = pd.DataFrame({
            'Column': profile['column_stats'].keys(),
            'Unique Count': [stats['unique_count'] for stats in profile['column_stats'].values()],
            'Unique Percentage': [stats['unique_percentage'] for stats in profile['column_stats'].values()]
        })
        cardinality_data = cardinality_data.sort_values('Unique Percentage', ascending=False)
        
        fig = px.bar(
            cardinality_data,
            x='Column',
            y='Unique Percentage',
            color='Unique Percentage',
            title='Unique Values by Column',
            labels={'Unique Percentage': 'Unique Values (%)'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Option to continue to mapping
        st.markdown("---")
        if st.button("Continue to Mapping"):
            st.session_state.mapping_step = True
            st.rerun()
    else:
        st.error("No data available. Please upload a file first.")
        if st.button("Go Back to File Upload"):
            st.session_state.uploaded_file = None
            st.rerun()

def show_column_details(df, profile, columns):
    """
    Display details for the specified columns.
    
    Args:
        df: pandas DataFrame
        profile: Data profile dictionary
        columns: List of column names to display details for
    """
    # Filter profile data for the selected columns
    filtered_stats = {col: profile['column_stats'][col] for col in columns if col in profile['column_stats']}
    
    # Create a table of column details
    details_list = []
    for col, stats in filtered_stats.items():
        detail = {
            "Column": col,
            "Data Type": stats['dtype'],
            "Missing Values": f"{stats['missing_count']} ({stats['missing_percentage']}%)",
            "Unique Values": f"{stats['unique_count']} ({stats['unique_percentage']}%)"
        }
        
        # Add numeric stats if available
        if 'min' in stats:
            detail["Min"] = stats['min']
            detail["Max"] = stats['max']
            detail["Mean"] = round(stats['mean'], 2) if stats['mean'] is not None else None
        
        # Add sample values for strings
        if 'sample_values' in stats:
            sample_str = ", ".join(str(v) for v in stats['sample_values'][:3])
            if len(stats['sample_values']) > 3:
                sample_str += "..."
            detail["Sample Values"] = sample_str
        
        details_list.append(detail)
    
    if details_list:
        st.dataframe(pd.DataFrame(details_list), use_container_width=True)
    else:
        st.info("No column details available.")
