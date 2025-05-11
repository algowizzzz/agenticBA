#!/usr/bin/env python3
"""
Cleanup Bank Data
Clean up duplicate bank entries and download missing BMO report files
"""

import sqlite3
import os
import pandas as pd
import requests
import time
import logging
import sys
import re
from bs4 import BeautifulSoup
import random
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bank_data_cleanup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bank_data_cleanup")

# Find the database file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_COLLECTOR_DIR = os.path.join(SCRIPT_DIR, "news_collector")
DB_PATH = os.path.join(NEWS_COLLECTOR_DIR, "data", "db", "bank_reports.db")
REPORTS_DIR = os.path.join(NEWS_COLLECTOR_DIR, "data", "reports", "sec")

# Check if database exists
if not os.path.exists(DB_PATH):
    logger.error(f"Database not found at: {DB_PATH}")
    sys.exit(1)

logger.info(f"Starting database cleanup for: {DB_PATH}")

# Contact email for SEC (required by SEC guidelines)
SEC_API_EMAIL = "research@example.com"  # Replace with your email

def cleanup_duplicate_banks():
    """Clean up duplicate bank entries."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch all banks
    cursor.execute("SELECT cik, name, ticker, country FROM banks")
    banks = cursor.fetchall()
    
    # Group by name
    bank_groups = {}
    for bank in banks:
        cik, name, ticker, country = bank
        if name not in bank_groups:
            bank_groups[name] = []
        bank_groups[name].append((cik, name, ticker, country))
    
    # Identify duplicates
    duplicates = {name: entries for name, entries in bank_groups.items() if len(entries) > 1}
    
    if not duplicates:
        logger.info("No duplicate banks found.")
        conn.close()
        return
    
    # Process duplicates
    for name, entries in duplicates.items():
        logger.info(f"Found {len(entries)} duplicate entries for {name}")
        
        # Choose the best CIK (preferably the one with reports)
        cursor.execute("""
            SELECT b.cik, COUNT(r.id) as report_count
            FROM banks b
            LEFT JOIN reports r ON b.cik = r.cik
            WHERE b.name = ?
            GROUP BY b.cik
            ORDER BY report_count DESC
        """, (name,))
        cik_counts = cursor.fetchall()
        
        if not cik_counts:
            logger.warning(f"No CIK found for {name}, skipping")
            continue
            
        best_cik = cik_counts[0][0]
        logger.info(f"Keeping CIK {best_cik} for {name} with {cik_counts[0][1]} reports")
        
        # Update reports for other CIKs to use the best CIK
        for cik, _ in cik_counts[1:]:
            cursor.execute("""
                UPDATE reports
                SET cik = ?
                WHERE cik = ?
            """, (best_cik, cik))
            
            # Delete the duplicate bank entry
            cursor.execute("DELETE FROM banks WHERE cik = ?", (cik,))
            logger.info(f"Deleted duplicate bank entry with CIK {cik} for {name}")
    
    conn.commit()
    conn.close()
    logger.info("Duplicate bank cleanup completed")

def download_bmo_reports():
    """Download missing BMO reports."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get BMO CIK
    cursor.execute("""
        SELECT cik FROM banks 
        WHERE name = 'BANK OF MONTREAL' 
        LIMIT 1
    """)
    result = cursor.fetchone()
    
    if not result:
        logger.error("BMO not found in database.")
        conn.close()
        return
        
    bmo_cik = result[0]
    logger.info(f"Found BMO with CIK: {bmo_cik}")
    
    # Get reports that haven't been downloaded
    cursor.execute("""
        SELECT id, accession_number, form_type, filing_date, report_url, title 
        FROM reports 
        WHERE cik = ? AND downloaded = 0
    """, (bmo_cik,))
    reports = cursor.fetchall()
    
    logger.info(f"Found {len(reports)} BMO reports to download")
    
    headers = {
        "User-Agent": f"BussGPT Research/1.0 {SEC_API_EMAIL}",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Host": "www.sec.gov"
    }
    
    # Download each report
    for report in reports:
        report_id, accession_number, form_type, filing_date, report_url, title = report
        
        logger.info(f"Downloading report: {report_url}")
        
        try:
            # Create folders
            report_dir = os.path.join(REPORTS_DIR, bmo_cik.lstrip('0'), f"{filing_date.replace('-', '')}_{form_type}")
            os.makedirs(report_dir, exist_ok=True)
            
            # Download index page
            response = requests.get(report_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to download index page: HTTP {response.status_code}")
                continue
                
            # Parse the index page to find the main document
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the main document
            main_doc_url = None
            
            # First try to find the table with the main form
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        description = cells[1].get_text(strip=True)
                        if form_type in description and ('Document' in description or '.htm' in description):
                            links = cells[2].find_all('a')
                            for link in links:
                                href = link.get('href')
                                if href and (href.endswith('.htm') or href.endswith('.html')):
                                    # Make absolute URL
                                    if href.startswith('http'):
                                        main_doc_url = href
                                    else:
                                        base_url = re.match(r'(https://www.sec.gov/Archives/edgar/data/[^/]+/[^/]+)/', report_url).group(1)
                                        main_doc_url = f"{base_url}/{href}"
                                    break
                                    
            if not main_doc_url:
                # Alternative method: find all .htm links and take the one that seems to be the main document
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and (href.endswith('.htm') or href.endswith('.html')):
                        if re.search(r'\d+[a-z]*\.htm', href, re.IGNORECASE):
                            # Make absolute URL
                            if href.startswith('http'):
                                main_doc_url = href
                            else:
                                base_url = re.match(r'(https://www.sec.gov/Archives/edgar/data/[^/]+/[^/]+)/', report_url).group(1)
                                main_doc_url = f"{base_url}/{href}"
                            break
             
            if not main_doc_url:
                logger.error(f"Could not find main document URL for {accession_number}")
                continue
                
            logger.info(f"Fetching main document: {main_doc_url}")
            
            # Wait to avoid rate limiting
            time.sleep(random.uniform(1, 2))
            
            # Download main document
            doc_response = requests.get(main_doc_url, headers=headers)
            
            if doc_response.status_code != 200:
                logger.error(f"Failed to download main document: HTTP {doc_response.status_code}")
                continue
                
            # Save main document
            output_path = os.path.join(report_dir, "main_document.html")
            with open(output_path, 'wb') as f:
                f.write(doc_response.content)
                
            logger.info(f"Saved main document to: {output_path}")
            
            # Update database
            cursor.execute("""
                UPDATE reports
                SET downloaded = 1, local_path = ?
                WHERE id = ?
            """, (output_path, report_id))
            
            conn.commit()
            logger.info(f"Updated download status for {accession_number}")
            
            # Wait before next download to avoid rate limiting
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            logger.error(f"Error downloading report {accession_number}: {e}")
            
    conn.close()
    logger.info("BMO report download completed")

def main():
    logger.info("Starting bank data cleanup process")
    
    # Step 1: Clean up duplicate banks
    cleanup_duplicate_banks()
    
    # Step 2: Download missing BMO reports
    download_bmo_reports()
    
    # Export to CSV for convenience
    conn = sqlite3.connect(DB_PATH)
    reports_df = pd.read_sql_query("""
        SELECT 
            b.name as bank_name,
            b.ticker,
            r.form_type,
            r.filing_date,
            r.accession_number,
            r.report_url,
            r.downloaded,
            r.local_path
        FROM reports r
        JOIN banks b ON r.cik = b.cik
        ORDER BY b.name, r.filing_date DESC
    """, conn)
    
    csv_path = os.path.join(NEWS_COLLECTOR_DIR, "data", "bank_reports.csv")
    reports_df.to_csv(csv_path, index=False)
    logger.info(f"Exported reports data to: {csv_path}")
    
    conn.close()
    logger.info("Bank data cleanup process completed successfully")

if __name__ == "__main__":
    main() 