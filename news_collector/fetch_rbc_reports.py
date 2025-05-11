#!/usr/bin/env python3
"""
RBC Report Fetcher
Retrieves SEC annual and quarterly reports for Royal Bank of Canada (RBC) and adds them to the database.
"""

import os
import sqlite3
import pandas as pd
import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
import logging
import sys
import shutil

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
REF_DIR = os.path.join(DATA_DIR, "reference")
DB_PATH = os.path.join(DB_DIR, "bank_reports.db")
CSV_PATH = os.path.join(DATA_DIR, "bank_reports.csv")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(REF_DIR, exist_ok=True)

# Royal Bank of Canada (RBC) CIK and details
# Will be overwritten if found in SEC database
RBC_CIKS = {
    "0000001045653": {"name": "ROYAL BANK OF CANADA", "ticker": "RY", "country": "Canada"}
}

# Form types to keep (annual and quarterly reports only)
KEEP_FORM_TYPES = ['40-F', '6-K']

# Contact email for SEC (required by SEC guidelines)
SEC_API_EMAIL = "REPLACE_WITH_YOUR_EMAIL@example.com"  # Replace with a valid email

def backup_database():
    """Create a backup of the database before modifying."""
    backup_path = DB_PATH + ".rbc_backup"
    try:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False

def download_cik_lookup():
    """
    Download the company tickers list from SEC and find RBC's CIK.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": f"BussGPT Research/1.0 {SEC_API_EMAIL}",
    }
    
    output_file = os.path.join(REF_DIR, "company_tickers.csv")
    
    try:
        logger.info("Downloading SEC company tickers list...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Convert JSON to DataFrame
            data = response.json()
            companies = []
            
            for _, company in data.items():
                # Format CIK with leading zeros (10 digits)
                cik = str(company['cik_str']).zfill(10)
                companies.append({
                    'cik': cik,
                    'ticker': company['ticker'],
                    'name': company['title']
                })
            
            df = pd.DataFrame(companies)
            
            # Check if we already have the file
            if not os.path.exists(output_file):
                df.to_csv(output_file, index=False)
                logger.info(f"CIK lookup file created: {output_file}")
            
            # Find RBC CIK
            rbc_info = df[df['ticker'] == 'RY']
            if not rbc_info.empty:
                cik = rbc_info.iloc[0]['cik']
                logger.info(f"Found RBC in SEC database: CIK {cik}")
                # Update our RBC CIKs dictionary
                RBC_CIKS[cik] = {"name": "ROYAL BANK OF CANADA", "ticker": "RY", "country": "Canada"}
                
            return len(companies)
        else:
            logger.error(f"Failed to download CIK list: HTTP {response.status_code}")
            return 0
    
    except Exception as e:
        logger.error(f"Error downloading CIK lookup: {e}")
        return 0

def add_rbc_to_database():
    """Add RBC to the banks table in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for cik, bank_info in RBC_CIKS.items():
        cursor.execute(
            "INSERT OR REPLACE INTO banks (cik, name, ticker, country) VALUES (?, ?, ?, ?)",
            (cik, bank_info["name"], bank_info["ticker"], bank_info["country"])
        )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Added {len(RBC_CIKS)} RBC entries to database")

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
                # Filter for only 40-F and 6-K reports
                filtered_reports = [r for r in reports if r['form_type'] in KEEP_FORM_TYPES]
                logger.info(f"Filtered reports: keeping {len(filtered_reports)} out of {len(reports)} total reports")
                return filtered_reports
                
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
        logger.info(f"Fetching reports for CIK: {cik} using SEC API...")
        response = requests.get(edgar_api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract recent filings from last year
            cutoff_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            if 'filings' in data and 'recent' in data['filings']:
                filings = data['filings']['recent']
                
                # Check if we have the expected data structure
                if 'accessionNumber' in filings and 'form' in filings and 'filingDate' in filings:
                    for i in range(len(filings['accessionNumber'])):
                        # Extract core filing data
                        accession_number = filings['accessionNumber'][i]
                        form_type = filings['form'][i]
                        filing_date = filings['filingDate'][i]
                        
                        # Skip if older than cutoff date
                        if filing_date < cutoff_date:
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
            
            logger.info(f"Found {len(reports)} reports for CIK: {cik}")
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
    
    logger.info(f"Added {added_count} new reports to database")

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
        cik_dir = os.path.join(REPORTS_DIR, report['cik'])
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
                # Look for main document (usually 40-F, 6-K document itself)
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
                            "company_name": RBC_CIKS.get(report['cik'], {}).get("name", "Unknown"),
                            "ticker": RBC_CIKS.get(report['cik'], {}).get("ticker", "Unknown"),
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

def download_all_reports():
    """Download all reports that haven't been downloaded yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Select only RBC reports that haven't been downloaded
    cursor.execute(
        "SELECT * FROM reports WHERE downloaded = 0 AND cik IN ({})".format(
            ','.join(['?'] * len(RBC_CIKS))
        ),
        list(RBC_CIKS.keys())
    )
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
    ORDER BY r.cik, r.filing_date DESC
    """
    
    # Export to CSV
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Save to CSV
    df.to_csv(CSV_PATH, index=False)
    
    logger.info(f"Updated CSV export with {len(df)} records")
    return len(df)

def main():
    """Main function to fetch and store RBC reports."""
    logger.info("Starting RBC Report Fetcher...")
    
    # Create backup of database
    if not backup_database():
        logger.error("Aborting due to backup failure")
        return
    
    # Download CIK lookup reference (and update RBC_CIKS if found)
    cik_count = download_cik_lookup()
    logger.info(f"Processed reference with {cik_count} company CIKs")
    
    # Add RBC to database
    add_rbc_to_database()
    
    # Process each RBC CIK
    for cik in RBC_CIKS.keys():
        reports = fetch_reports_with_retry(cik)
        store_reports_in_database(reports)
    
    # Download report content
    download_all_reports()
    
    # Update CSV export
    csv_path = update_csv_export()
    
    logger.info("RBC Report Fetcher completed successfully.")
    
    # Count how many of each RBC report type we collected
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT form_type, COUNT(*) FROM reports WHERE cik IN ({}) GROUP BY form_type".format(
            ','.join(['?'] * len(RBC_CIKS))
        ),
        list(RBC_CIKS.keys())
    )
    form_counts = cursor.fetchall()
    
    logger.info("RBC report counts by type:")
    for form_type, count in form_counts:
        logger.info(f"  {form_type}: {count} filings")
    
    conn.close()

if __name__ == "__main__":
    main() 