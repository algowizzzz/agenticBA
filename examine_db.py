#!/usr/bin/env python3
"""
Examine the structure and contents of the bank reports database
"""

import sqlite3
import os
import sys

# Find the database files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_COLLECTOR_DIR = os.path.join(SCRIPT_DIR, "news_collector")
DB_PATH = os.path.join(NEWS_COLLECTOR_DIR, "data", "db", "bank_reports.db")

# Check if database exists
if not os.path.exists(DB_PATH):
    print(f"Database not found at: {DB_PATH}")
    # Try alternative location
    DB_PATH = os.path.join(SCRIPT_DIR, "data", "bank_reports.db")
    if not os.path.exists(DB_PATH):
        print(f"Database not found at alternative location: {DB_PATH}")
        sys.exit(1)

print(f"Examining database at: {DB_PATH}")

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"\nTables in database: {[table[0] for table in tables]}")

# For each table, show structure and sample data
for table in tables:
    table_name = table[0]
    print(f"\n=== TABLE: {table_name} ===")
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print("Columns:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    row_count = cursor.fetchone()[0]
    print(f"\nTotal rows: {row_count}")
    
    # Get sample data (first 5 rows)
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
    sample_data = cursor.fetchall()
    
    if sample_data:
        print("\nSample data:")
        for row in sample_data:
            print(f"  {row}")

# If reports table exists, get distribution of form types
if any(table[0] == 'reports' for table in tables):
    print("\n=== Form Type Distribution ===")
    cursor.execute("SELECT form_type, COUNT(*) FROM reports GROUP BY form_type ORDER BY COUNT(*) DESC;")
    form_types = cursor.fetchall()
    for form_type in form_types:
        print(f"  {form_type[0]}: {form_type[1]} reports")

# If reports table exists, get date range of filings
if any(table[0] == 'reports' for table in tables):
    print("\n=== Filing Date Range ===")
    cursor.execute("SELECT MIN(filing_date), MAX(filing_date) FROM reports;")
    date_range = cursor.fetchone()
    print(f"  From {date_range[0]} to {date_range[1]}")

# Close the connection
conn.close() 