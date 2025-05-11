#!/usr/bin/env python3
"""
RBC Report Fetcher
Retrieves SEC reports for Royal Bank of Canada focusing on 40-F and 6-K reports from May 5, 2024 onward.
"""

import os
import requests
import json
import pandas as pd
import time
from bs4 import BeautifulSoup
from datetime import datetime, date
import sqlite3
import logging
import sys
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rbc_report_fetcher.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("rbc_report_fetcher")

# Set up output directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_COLLECTOR_DIR = os.path.join(SCRIPT_DIR, "news_collector")
if os.path.exists(NEWS_COLLECTOR_DIR):
    # Use news_collector structure if available
    DATA_DIR = os.path.join(NEWS_COLLECTOR_DIR, "data")
    REPORTS_DIR = os.path.join(DATA_DIR, "reports")
    DB_DIR = os.path.join(DATA_DIR, "db")
else:
    # Use local structure
    DATA_DIR = os.path.join(SCRIPT_DIR, "data")
    REPORTS_DIR = os.path.join(DATA_DIR, "reports")
    DB_DIR = os.path.join(DATA_DIR, "db")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(os.path.join(REPORTS_DIR, "sec"), exist_ok=True)

# Database path
DB_PATH = os.path.join(DB_DIR, "bank_reports.db")

# Known CIK for Royal Bank of Canada
RBC_CIK = "0000947263"  # Correct Royal Bank of Canada CIK
# The minimum date to include
MIN_DATE = "2024-05-05"

# Contact email for SEC (required by SEC guidelines)
SEC_API_EMAIL = "research@example.com"  # Replace with your email

def initialize_database():
    """Create the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create banks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS banks (
        cik TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        ticker TEXT,
        country TEXT
    )
    ''')
    
    # Create reports table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cik TEXT NOT NULL,
        accession_number TEXT NOT NULL,
        form_type TEXT NOT NULL,
        filing_date TEXT NOT NULL,
        report_url TEXT NOT NULL,
        title TEXT,
        downloaded INTEGER DEFAULT 0,
        local_path TEXT,
        FOREIGN KEY (cik) REFERENCES banks(cik),
        UNIQUE(cik, accession_number)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully.")

def add_rbc_to_database():
    """Add RBC to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO banks (cik, name, ticker, country) VALUES (?, ?, ?, ?)",
        (RBC_CIK, "ROYAL BANK OF CANADA", "RY", "Canada")
    )
    
    conn.commit()
    conn.close()
    
    logger.info("Added RBC to database.")

def fetch_reports_with_retry(cik, max_retries=3, initial_delay=10):
    """
    Fetch reports with retry logic and exponential backoff.
    """
    retries = 0
    delay = initial_delay
    
    while retries < max_retries:
        try:
            reports = fetch_reports_for_cik(cik)
            if reports:  # If we got any reports, consider it successful
                return reports
                
            # If we didn't get reports but also didn't get an exception,
            # increment retry counter and wait
            retries += 1
            logger.warning(f"No reports found for CIK {cik}. Retry {retries}/{max_retries}")
            
            if retries < max_retries:
                # Exponential backoff with jitter
                sleep_time = delay + random.uniform(0, 5)
                logger.info(f"Waiting {sleep_time:.2f} seconds before retrying...")
                time.sleep(sleep_time)
                delay *= 2  # Double the delay for next time
            
        except Exception as e:
            retries += 1
            logger.error(f"Error fetching reports (attempt {retries}/{max_retries}): {e}")
            
            if retries < max_retries:
                # Exponential backoff with jitter
                sleep_time = delay + random.uniform(0, 5)
                logger.info(f"Waiting {sleep_time:.2f} seconds before retrying...")
                time.sleep(sleep_time)
                delay *= 2
    
    logger.error(f"Failed to fetch reports for CIK {cik} after {max_retries} attempts")
    return []

def fetch_reports_for_cik(cik):
    """
    Fetch available SEC reports for a given CIK number.
    
    Args:
        cik: CIK number as string
    
    Returns:
        List of report data dictionaries
    """
    # Use the SEC.gov EDGAR API
    edgar_api_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    headers = {
        "User-Agent": f"BussGPT Research/1.0 {SEC_API_EMAIL}",
        "Accept": "application/json",
        "Host": "data.sec.gov"
    }
    
    reports = []
    
    try:
        logger.info(f"Fetching reports for RBC (CIK: {cik}) using SEC API...")
        response = requests.get(edgar_api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract recent filings
            if 'filings' in data and 'recent' in data['filings']:
                filings = data['filings']['recent']
                
                # Check if we have the expected data structure
                if 'accessionNumber' in filings and 'form' in filings and 'filingDate' in filings:
                    for i in range(len(filings['accessionNumber'])):
                        # Extract core filing data
                        accession_number = filings['accessionNumber'][i]
                        form_type = filings['form'][i]
                        filing_date = filings['filingDate'][i]
                        
                        # Skip non-annual/quarterly reports and filings before MIN_DATE
                        if form_type not in ['40-F', '6-K']:
                            continue
                            
                        # Check if the filing date is after or equal to our minimum date
                        if filing_date < MIN_DATE:
                            continue
                        
                        # Extract optional title if available
                        title = filings.get('reportUrl', [None] * len(filings['accessionNumber']))[i]
                        if not title:
                            title = filings.get('primaryDocument', [None] * len(filings['accessionNumber']))[i]
                        
                        # Build report URL
                        # Format: https://www.sec.gov/Archives/edgar/data/CIK/ACCESSION.txt
                        # Remove dashes from accession number for URL
                        clean_accession = accession_number.replace('-', '')
                        report_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{clean_accession}/{accession_number}-index.htm"
                        
                        reports.append({
                            'cik': cik,
                            'accession_number': accession_number,
                            'form_type': form_type,
                            'filing_date': filing_date,
                            'report_url': report_url,
                            'title': title
                        })
            
            logger.info(f"Found {len(reports)} relevant RBC reports since {MIN_DATE}")
        else:
            logger.error(f"Error fetching reports for CIK {cik}: HTTP {response.status_code}")
            logger.error(f"Response: {response.text[:500]}...")
    
    except Exception as e:
        logger.error(f"Error fetching reports for CIK {cik}: {e}")
    
    # Add a delay to avoid rate limiting (SEC.gov requires this)
    time.sleep(random.uniform(1, 2))
    
    return reports

def store_reports_in_database(reports):
    """
    Store report data in the database.
    
    Args:
        reports: List of report data dictionaries
    """
    if not reports:
        logger.info("No reports to store.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    added_count = 0
    
    for report in reports:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO reports (cik, accession_number, form_type, filing_date, report_url, title) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    report['cik'],
                    report['accession_number'],
                    report['form_type'],
                    report['filing_date'],
                    report['report_url'],
                    report['title']
                )
            )
            
            if cursor.rowcount > 0:
                added_count += 1
        
        except Exception as e:
            logger.error(f"Error storing report {report['accession_number']}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Added {added_count} new RBC reports to database.")

def download_report_content(report):
    """
    Download the content of a report and save it locally.
    
    Args:
        report: Report data dictionary
    
    Returns:
        Local file path if successful, None otherwise
    """
    headers = {
        "User-Agent": f"BussGPT Research/1.0 {SEC_API_EMAIL}",
        "Accept": "text/html,application/xhtml+xml,application/xml",
    }
    
    try:
        # Create directory for CIK if it doesn't exist
        cik_dir = os.path.join(REPORTS_DIR, "sec", report['cik'])
        os.makedirs(cik_dir, exist_ok=True)
        
        # Create file name with form type and accession number
        form_type = report['form_type'].replace('/', '-')
        try:
            date_str = datetime.strptime(report['filing_date'], '%Y-%m-%d').strftime('%Y%m%d')
        except ValueError:
            try:
                date_str = datetime.strptime(report['filing_date'], '%m/%d/%Y').strftime('%Y%m%d')
            except ValueError:
                # Fallback if date format is unexpected
                date_str = report['filing_date'].replace('/', '').replace('-', '')
        
        file_name = f"{date_str}_{form_type}_{report['accession_number'].replace('-', '_')}.html"
        file_path = os.path.join(cik_dir, file_name)
        
        # Skip if already downloaded
        if os.path.exists(file_path):
            logger.info(f"Report already downloaded: {file_path}")
            return file_path
        
        # Fetch report content
        logger.info(f"Downloading report: {report['report_url']}")
        response = requests.get(report['report_url'], headers=headers)
        
        if response.status_code == 200:
            # Save the filing page first
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Parse to find actual document content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for table with document links
            table = soup.find('table', {'summary': 'Document Format Files'})
            
            if table:
                # Look for main document (usually the report itself)
                rows = table.find_all('tr')[1:]  # Skip header
                main_doc_url = None
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:  # Make sure we have enough cells
                        doc_type = cells[3].text.strip() if len(cells) > 3 else ""
                        if doc_type == report['form_type']:
                            doc_link = cells[2].find('a') if len(cells) > 2 else None
                            if doc_link and 'href' in doc_link.attrs:
                                main_doc_url = f"https://www.sec.gov{doc_link['href']}"
                                break
                
                # If no exact match, get the first document
                if not main_doc_url and rows:
                    cells = rows[0].find_all('td')
                    if len(cells) >= 3:
                        doc_link = cells[2].find('a')
                        if doc_link and 'href' in doc_link.attrs:
                            main_doc_url = f"https://www.sec.gov{doc_link['href']}"
                
                # Fetch and save document content
                if main_doc_url:
                    logger.info(f"Fetching main document: {main_doc_url}")
                    time.sleep(random.uniform(1, 2))  # Delay to avoid rate limiting
                    doc_response = requests.get(main_doc_url, headers=headers)
                    
                    if doc_response.status_code == 200:
                        # Create a directory for the specific filing
                        report_dir = os.path.join(cik_dir, date_str + "_" + form_type)
                        os.makedirs(report_dir, exist_ok=True)
                        
                        # Save the main document
                        main_doc_path = os.path.join(report_dir, "main_document.html")
                        with open(main_doc_path, 'wb') as f:
                            f.write(doc_response.content)
                        logger.info(f"Saved main document to: {main_doc_path}")
                        
                        # Create a simple metadata file
                        meta_path = os.path.join(report_dir, "metadata.json")
                        metadata = {
                            "cik": report['cik'],
                            "company_name": "ROYAL BANK OF CANADA",
                            "ticker": "RY",
                            "form_type": report['form_type'],
                            "filing_date": report['filing_date'],
                            "accession_number": report['accession_number'],
                            "title": report['title'],
                            "url": report['report_url'],
                            "document_url": main_doc_url
                        }
                        
                        with open(meta_path, 'w') as f:
                            json.dump(metadata, f, indent=2)
                        
                        # Return the path to the filing index
                        return file_path
                    else:
                        logger.error(f"Error fetching document: HTTP {doc_response.status_code}")
            
            # If we couldn't find and fetch the specific document, report that we at least saved the index
            logger.info(f"Saved filing index page to: {file_path}")
            return file_path
        else:
            logger.error(f"Error fetching report: HTTP {response.status_code}")
            if response.status_code == 403:
                # If we're getting rate limited, wait longer
                logger.warning("Rate limit may have been exceeded. Waiting...")
                time.sleep(random.uniform(5, 10))
    
    except Exception as e:
        logger.error(f"Error downloading report {report['accession_number']}: {e}")
    
    # Add a delay to avoid rate limiting
    time.sleep(random.uniform(2, 3))
    
    return None

def update_report_download_status(accession_number, file_path):
    """
    Update the download status and local path for a report in the database.
    
    Args:
        accession_number: Report accession number
        file_path: Local file path where the report is saved
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE reports SET downloaded = 1, local_path = ? WHERE accession_number = ?",
        (file_path, accession_number)
    )
    
    conn.commit()
    conn.close()

def download_rbc_reports():
    """Download RBC reports that haven't been downloaded yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reports WHERE downloaded = 0 AND cik = ?", (RBC_CIK,))
    reports = cursor.fetchall()
    
    conn.close()
    
    if not reports:
        logger.info("No new RBC reports to download.")
        return
    
    logger.info(f"Found {len(reports)} RBC reports to download.")
    
    for report in reports:
        # Convert to dictionary for easier handling
        report_dict = {
            'cik': report[1],
            'accession_number': report[2],
            'form_type': report[3],
            'filing_date': report[4],
            'report_url': report[5],
            'title': report[6]
        }
        
        file_path = download_report_content(report_dict)
        
        if file_path:
            update_report_download_status(report_dict['accession_number'], file_path)
            logger.info(f"Updated download status for {report_dict['accession_number']}")
            
            # Delay to avoid rate limiting
            time.sleep(random.uniform(2, 3))

def export_reports_to_csv():
    """Export all reports data to a CSV file."""
    export_path = os.path.join(DATA_DIR, "bank_reports.csv")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Join banks and reports tables
    query = """
    SELECT r.cik, b.name, b.ticker, b.country, r.accession_number, r.form_type, 
           r.filing_date, r.title, r.report_url, r.downloaded, r.local_path
    FROM reports r
    JOIN banks b ON r.cik = b.cik
    ORDER BY r.cik, r.filing_date DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df.to_csv(export_path, index=False)
    logger.info(f"Exported reports data to: {export_path}")
    
    return export_path

def main():
    """Main function to fetch and store RBC reports."""
    logger.info("Starting RBC Report Fetcher...")
    
    # Initialize database and add RBC
    initialize_database()
    add_rbc_to_database()
    
    # Fetch and store RBC reports
    reports = fetch_reports_with_retry(RBC_CIK)
    store_reports_in_database(reports)
    
    # Download report content
    download_rbc_reports()
    
    # Export data to CSV
    csv_path = export_reports_to_csv()
    
    # Print summary information
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get count of RBC reports
    cursor.execute("SELECT COUNT(*) FROM reports WHERE cik = ?", (RBC_CIK,))
    rbc_count = cursor.fetchone()[0]
    
    # Get count of BMO reports
    cursor.execute("SELECT COUNT(*) FROM reports WHERE cik = ?", ('0000927971',))
    bmo_count = cursor.fetchone()[0]
    
    # Get filing type distribution for RBC
    cursor.execute("SELECT form_type, COUNT(*) FROM reports WHERE cik = ? GROUP BY form_type", (RBC_CIK,))
    form_types = cursor.fetchall()
    
    conn.close()
    
    logger.info("RBC Report Fetcher completed successfully.")
    logger.info(f"Added {len(reports)} RBC reports from {MIN_DATE} onward.")
    logger.info(f"Total RBC reports in database: {rbc_count}")
    logger.info(f"Total BMO reports in database: {bmo_count}")
    logger.info("RBC filing type distribution:")
    for form_type in form_types:
        logger.info(f"  {form_type[0]}: {form_type[1]} reports")
    logger.info(f"Final report saved to: {csv_path}")

if __name__ == "__main__":
    main() 