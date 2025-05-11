#!/usr/bin/env python3
"""
Verify Bank Data
Script to verify and summarize the bank reports database contents
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime
import sys

# Find the database file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_COLLECTOR_DIR = os.path.join(SCRIPT_DIR, "news_collector")
DB_PATH = os.path.join(NEWS_COLLECTOR_DIR, "data", "db", "bank_reports.db")

# Check if database exists
if not os.path.exists(DB_PATH):
    print(f"Database not found at: {DB_PATH}")
    sys.exit(1)

print(f"Examining database at: {DB_PATH}")

# Connect to the database
conn = sqlite3.connect(DB_PATH)

# Get banks information
print("\n--- BANKS INFORMATION ---")
banks_df = pd.read_sql_query("SELECT * FROM banks", conn)
print(banks_df)

# Get report counts by bank and form type
print("\n--- REPORT COUNTS BY BANK AND FORM TYPE ---")
counts_df = pd.read_sql_query("""
    SELECT 
        b.name as bank_name, 
        r.form_type, 
        COUNT(*) as report_count,
        MIN(r.filing_date) as earliest_date,
        MAX(r.filing_date) as latest_date
    FROM reports r
    JOIN banks b ON r.cik = b.cik
    GROUP BY b.name, r.form_type
    ORDER BY b.name, r.form_type
""", conn)
print(counts_df)

# Get download status summary
print("\n--- DOWNLOAD STATUS SUMMARY ---")
download_df = pd.read_sql_query("""
    SELECT 
        b.name as bank_name,
        SUM(CASE WHEN r.downloaded = 1 THEN 1 ELSE 0 END) as downloaded,
        COUNT(*) as total,
        ROUND(SUM(CASE WHEN r.downloaded = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as percent_downloaded
    FROM reports r
    JOIN banks b ON r.cik = b.cik
    GROUP BY b.name
    ORDER BY b.name
""", conn)
print(download_df)

# Get most recent reports
print("\n--- 5 MOST RECENT REPORTS PER BANK ---")
for bank in banks_df['name']:
    print(f"\n{bank}:")
    recent_df = pd.read_sql_query(f"""
        SELECT 
            r.form_type, 
            r.filing_date, 
            r.title,
            r.downloaded,
            r.local_path
        FROM reports r
        JOIN banks b ON r.cik = b.cik
        WHERE b.name = '{bank}'
        ORDER BY r.filing_date DESC
        LIMIT 5
    """, conn)
    print(recent_df)

# Close connection
conn.close()

print("\nVerification complete.") 