#!/usr/bin/env python3
"""
BMO Data Cleanup Script
Retains only one year of data for Bank of Montreal (BMO) and deletes the rest.
"""

import os
import sqlite3
import pandas as pd
import shutil
from datetime import datetime, timedelta
import logging

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

# Date cutoff (keep only data from this date forward)
CUTOFF_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def backup_database():
    """Create a backup of the database before modifying."""
    backup_path = DB_PATH + ".backup"
    try:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False

def cleanup_database():
    """Remove old records from database, keeping only recent year."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get count before deletion
    cursor.execute("SELECT COUNT(*) FROM reports")
    before_count = cursor.fetchone()[0]
    
    # Delete records older than cutoff date
    cursor.execute(
        "DELETE FROM reports WHERE filing_date < ?",
        (CUTOFF_DATE,)
    )
    
    # Get count after deletion
    cursor.execute("SELECT COUNT(*) FROM reports")
    after_count = cursor.fetchone()[0]
    
    # Commit changes
    conn.commit()
    conn.close()
    
    deleted_count = before_count - after_count
    logger.info(f"Removed {deleted_count} records from database")
    logger.info(f"Retained {after_count} records from {CUTOFF_DATE} onwards")
    
    return deleted_count, after_count

def cleanup_filesystem():
    """Remove physical files for deleted records."""
    # Get list of files to keep from database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all local paths that should be kept
    cursor.execute("SELECT local_path FROM reports WHERE local_path IS NOT NULL")
    keep_paths = set([row[0] for row in cursor.fetchall()])
    conn.close()
    
    # Count files deleted
    deleted_files = 0
    
    # For each CIK directory
    for cik in os.listdir(REPORTS_DIR):
        cik_dir = os.path.join(REPORTS_DIR, cik)
        
        # Skip if not a directory or not a BMO CIK
        if not os.path.isdir(cik_dir) or cik not in ["0000009622", "0000927971"]:
            continue
            
        # Check each file in the directory
        for root, dirs, files in os.walk(cik_dir, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                
                # If file not in keep_paths, delete it
                if file_path not in keep_paths and not file.endswith("metadata.json"):
                    try:
                        os.remove(file_path)
                        deleted_files += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
            
            # Check if directory is empty and remove if it is
            if not os.listdir(root) and root != cik_dir:
                try:
                    os.rmdir(root)
                    logger.info(f"Removed empty directory: {root}")
                except Exception as e:
                    logger.error(f"Failed to remove directory {root}: {e}")
    
    logger.info(f"Removed {deleted_files} files from filesystem")
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
    """Main function to clean up BMO data."""
    logger.info(f"Starting BMO data cleanup, keeping data from {CUTOFF_DATE} onwards")
    
    # Create backup first
    if not backup_database():
        logger.error("Aborting cleanup due to backup failure")
        return
    
    # Clean up database
    deleted_records, kept_records = cleanup_database()
    
    # Clean up filesystem
    deleted_files = cleanup_filesystem()
    
    # Update CSV export
    exported_records = update_csv_export()
    
    logger.info(f"BMO data cleanup complete:")
    logger.info(f"  - Deleted records: {deleted_records}")
    logger.info(f"  - Deleted files: {deleted_files}")
    logger.info(f"  - Retained records: {kept_records}")
    logger.info(f"  - Exported records: {exported_records}")
    logger.info(f"  - Cutoff date: {CUTOFF_DATE}")

if __name__ == "__main__":
    main() 