#!/usr/bin/env python3
"""
BMO Report Filter Script
Retains only annual reports (40-F) and quarterly reports (6-K) for Bank of Montreal,
deleting all other filing types (prospectuses, etc.)
"""

import os
import sqlite3
import pandas as pd
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_DIR = os.path.join(DATA_DIR, "db")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
DB_PATH = os.path.join(DB_DIR, "bank_reports.db")
CSV_PATH = os.path.join(DATA_DIR, "bank_reports.csv")

# Form types to keep
KEEP_FORM_TYPES = ['40-F', '6-K']

def backup_database():
    """Create a backup of the database before modifying."""
    backup_path = DB_PATH + ".reports_backup"
    try:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False

def filter_database():
    """Filter database to keep only annual and quarterly reports."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get counts before filtering
    cursor.execute("SELECT COUNT(*) FROM reports")
    before_count = cursor.fetchone()[0]
    
    # Get counts by form type before filtering
    cursor.execute("SELECT form_type, COUNT(*) FROM reports GROUP BY form_type")
    form_counts = cursor.fetchall()
    logger.info("Form type counts before filtering:")
    for form_type, count in form_counts:
        logger.info(f"  {form_type}: {count} filings")
    
    # Get list of reports to delete (not in KEEP_FORM_TYPES)
    cursor.execute(
        "SELECT id, cik, accession_number, form_type, local_path FROM reports WHERE form_type NOT IN ({})".format(
            ','.join(['?'] * len(KEEP_FORM_TYPES))
        ),
        KEEP_FORM_TYPES
    )
    to_delete = cursor.fetchall()
    logger.info(f"Found {len(to_delete)} reports to delete (not 40-F or 6-K)")
    
    # Delete records not in KEEP_FORM_TYPES
    cursor.execute(
        "DELETE FROM reports WHERE form_type NOT IN ({})".format(
            ','.join(['?'] * len(KEEP_FORM_TYPES))
        ),
        KEEP_FORM_TYPES
    )
    
    # Get count after filtering
    cursor.execute("SELECT COUNT(*) FROM reports")
    after_count = cursor.fetchone()[0]
    
    # Get counts by form type after filtering
    cursor.execute("SELECT form_type, COUNT(*) FROM reports GROUP BY form_type")
    form_counts_after = cursor.fetchall()
    logger.info("Form type counts after filtering:")
    for form_type, count in form_counts_after:
        logger.info(f"  {form_type}: {count} filings")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    deleted_count = before_count - after_count
    logger.info(f"Removed {deleted_count} records from database")
    logger.info(f"Retained {after_count} reports (40-F and 6-K filings)")
    
    return to_delete, deleted_count, after_count

def delete_unwanted_files(to_delete):
    """Delete files for reports that were removed from the database."""
    deleted_files = 0
    kept_directories = set()
    
    # First, delete the specific files
    for _, cik, accession_number, form_type, local_path in to_delete:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                deleted_files += 1
                
                # Get parent directory (for the specific report)
                parent_dir = os.path.dirname(local_path)
                if parent_dir.endswith(form_type.replace('/', '-')):
                    # This is a report-specific directory, might need to delete it if empty
                    if os.path.exists(parent_dir) and os.path.isdir(parent_dir):
                        # Check if it's empty after deleting the file
                        if not os.listdir(parent_dir):
                            try:
                                os.rmdir(parent_dir)
                                logger.info(f"Removed empty directory: {parent_dir}")
                            except Exception as e:
                                logger.error(f"Failed to remove directory {parent_dir}: {e}")
            except Exception as e:
                logger.error(f"Failed to delete {local_path}: {e}")
    
    # Now, for each CIK directory, scan and delete orphaned subdirectories
    for cik in ["0000009622", "0000927971"]:  # BMO CIK numbers
        cik_dir = os.path.join(REPORTS_DIR, cik)
        if not os.path.exists(cik_dir) or not os.path.isdir(cik_dir):
            continue
            
        # Get all subdirectories (date_formtype format)
        for item in os.listdir(cik_dir):
            item_path = os.path.join(cik_dir, item)
            
            # Skip files and directories to keep
            if not os.path.isdir(item_path):
                continue
                
            # Check if directory name contains a form type we want to delete
            is_kept_dir = False
            for form_type in KEEP_FORM_TYPES:
                if form_type.replace('/', '-') in item:
                    is_kept_dir = True
                    kept_directories.add(item_path)
                    break
            
            # If not a kept directory, delete it and its contents
            if not is_kept_dir:
                try:
                    shutil.rmtree(item_path)
                    deleted_files += 1
                    logger.info(f"Removed directory: {item_path}")
                except Exception as e:
                    logger.error(f"Failed to remove directory {item_path}: {e}")
    
    logger.info(f"Removed {deleted_files} files and directories")
    logger.info(f"Kept {len(kept_directories)} report directories")
    return deleted_files

def update_csv_export():
    """Update the CSV export to match the database."""
    conn = sqlite3.connect(DB_PATH)
    
    # Query to get all reports data joined with banks
    query = """
    SELECT r.cik, b.name, b.ticker, b.country, r.accession_number, 
           r.form_type, r.filing_date, r.title, r.report_url, 
           r.downloaded, r.local_path
    FROM reports r
    JOIN banks b ON r.cik = b.cik
    ORDER BY r.filing_date DESC
    """
    
    # Export to CSV
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Save to CSV
    df.to_csv(CSV_PATH, index=False)
    
    logger.info(f"Updated CSV export with {len(df)} records")
    return len(df)

def main():
    """Main function to filter BMO data to keep only annual and quarterly reports."""
    logger.info(f"Starting BMO data filtering, keeping only annual (40-F) and quarterly (6-K) reports")
    
    # Create backup first
    if not backup_database():
        logger.error("Aborting filtering due to backup failure")
        return
    
    # Filter database
    to_delete, deleted_records, kept_records = filter_database()
    
    # Delete unwanted files
    deleted_files = delete_unwanted_files(to_delete)
    
    # Update CSV export
    exported_records = update_csv_export()
    
    logger.info(f"BMO data filtering complete:")
    logger.info(f"  - Deleted records: {deleted_records}")
    logger.info(f"  - Deleted files: {deleted_files}")
    logger.info(f"  - Retained records: {kept_records}")
    logger.info(f"  - Exported records: {exported_records}")
    logger.info(f"  - Kept form types: {', '.join(KEEP_FORM_TYPES)}")

if __name__ == "__main__":
    main() 