#!/usr/bin/env python3
"""
Bank Reports Analyzer
Analyzes the collected SEC filing data for insights.
"""

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Set up output directories
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_DIR = os.path.join(DATA_DIR, "db")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")

os.makedirs(ANALYSIS_DIR, exist_ok=True)

# Database path
DB_PATH = os.path.join(DB_DIR, "bank_reports.db")

def load_report_data():
    """Load report data from database into a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT r.cik, b.name, b.ticker, b.country, r.accession_number, 
           r.form_type, r.filing_date, r.title, r.report_url, 
           r.downloaded, r.local_path
    FROM reports r
    JOIN banks b ON r.cik = b.cik
    ORDER BY r.filing_date DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} reports from database")
    
    # Convert filing date to datetime
    df['filing_date'] = pd.to_datetime(df['filing_date'], errors='coerce')
    
    return df

def analyze_form_types(df):
    """Analyze distribution of SEC form types by bank."""
    # Group by CIK and form type, count occurrences
    form_counts = df.groupby(['cik', 'name', 'form_type']).size().reset_index(name='count')
    
    # Pivot table for easier visualization
    pivot_df = form_counts.pivot_table(index=['cik', 'name'], columns='form_type', values='count', fill_value=0)
    
    # Add a total column
    pivot_df['Total'] = pivot_df.sum(axis=1)
    
    # Sort by total filings
    pivot_df = pivot_df.sort_values('Total', ascending=False)
    
    # Save to CSV
    output_file = os.path.join(ANALYSIS_DIR, "form_type_distribution.csv")
    pivot_df.to_csv(output_file)
    
    print(f"Form type distribution saved to {output_file}")
    
    return pivot_df

def visualize_form_distribution(df):
    """Create a bar chart of form type distribution."""
    form_counts = df['form_type'].value_counts().sort_values(ascending=False)
    
    plt.figure(figsize=(12, 6))
    form_counts.plot(kind='bar', color='skyblue')
    plt.title('SEC Filing Form Type Distribution')
    plt.xlabel('Form Type')
    plt.ylabel('Number of Filings')
    plt.tight_layout()
    
    # Save figure
    output_file = os.path.join(ANALYSIS_DIR, "form_distribution.png")
    plt.savefig(output_file, dpi=300)
    
    print(f"Form distribution chart saved to {output_file}")
    
    return form_counts

def analyze_filings_by_year(df):
    """Analyze filing distribution by year."""
    # Extract year from filing date
    df['year'] = df['filing_date'].dt.year
    
    # Group by year and count
    year_counts = df.groupby('year').size().sort_index()
    
    # Create line chart
    plt.figure(figsize=(12, 6))
    year_counts.plot(kind='line', marker='o', color='green')
    plt.title('SEC Filings by Year')
    plt.xlabel('Year')
    plt.ylabel('Number of Filings')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Save figure
    output_file = os.path.join(ANALYSIS_DIR, "filings_by_year.png")
    plt.savefig(output_file, dpi=300)
    
    print(f"Filings by year chart saved to {output_file}")
    
    return year_counts

def generate_summary_report(df, form_pivot, year_counts):
    """Generate a summary report of the analysis."""
    total_filings = len(df)
    unique_companies = df['name'].nunique()
    earliest_filing = df['filing_date'].min()
    latest_filing = df['filing_date'].max()
    most_common_form = df['form_type'].value_counts().idxmax()
    
    # Create summary report
    report = f"""
    SEC FILING ANALYSIS SUMMARY
    ==============================
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    OVERVIEW:
    - Total Filings: {total_filings}
    - Companies Analyzed: {unique_companies}
    - Date Range: {earliest_filing.strftime('%Y-%m-%d')} to {latest_filing.strftime('%Y-%m-%d')}
    - Most Common Form Type: {most_common_form}
    
    TOP FORM TYPES:
    {df['form_type'].value_counts().head(5).to_string()}
    
    FILINGS BY COMPANY:
    {df.groupby('name').size().sort_values(ascending=False).to_string()}
    
    """
    
    # Save report
    output_file = os.path.join(ANALYSIS_DIR, "analysis_summary.txt")
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"Summary report saved to {output_file}")
    
    return report

def main():
    """Main function to analyze bank reports."""
    print("Starting Bank Report Analysis...")
    
    # Load data
    df = load_report_data()
    
    # Analyze form types
    form_pivot = analyze_form_types(df)
    
    # Visualize form distribution
    form_counts = visualize_form_distribution(df)
    
    # Analyze filings by year
    year_counts = analyze_filings_by_year(df)
    
    # Generate summary report
    generate_summary_report(df, form_pivot, year_counts)
    
    print("Bank Report Analysis completed successfully.")

if __name__ == "__main__":
    main() 