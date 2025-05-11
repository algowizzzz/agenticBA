#!/usr/bin/env python3
"""
BMO SEC Filing API Extractor

This script extracts SEC filings for Bank of Montreal (BMO) using the official SEC API.
It downloads the filings and extracts the Management's Discussion and Analysis (MD&A) section.

Usage:
    python bmo_rss_extractor.py
"""

import os
import re
import time
import json
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("bmo_sec_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BMO's CIK (Central Index Key) - must be 10 digits with leading zeros
BMO_CIK = "0000927971"  # Bank of Montreal
FORM_TYPES = ["10-K", "10-Q"]  # Annual and quarterly reports

# SEC API endpoint for submissions
SEC_API_URL = f"https://data.sec.gov/submissions/CIK{BMO_CIK}.json"

# Request headers per SEC guidelines
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (Your Organization; your.email@example.com)",
    "Accept": "application/json",
    "Host": "data.sec.gov"
}

def fetch_sec_filings():
    """
    Fetch SEC filings data for BMO using the official SEC API.
    
    Returns:
        List of filing entries from the API
    """
    logger.info(f"Fetching SEC filings from API: {SEC_API_URL}")
    
    try:
        response = requests.get(SEC_API_URL, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract recent filings from the submissions data
        filings = []
        if 'filings' in data and 'recent' in data['filings']:
            recent = data['filings']['recent']
            
            # Get the indices of each column
            form_idx = recent['form'].index if 'form' in recent else []
            filing_date_idx = recent['filingDate'].index if 'filingDate' in recent else []
            accession_number_idx = recent['accessionNumber'].index if 'accessionNumber' in recent else []
            primary_doc_idx = recent['primaryDocument'].index if 'primaryDocument' in recent else []
            
            # Process each filing, creating a unified record
            for i in range(len(recent['form'])):
                if recent['form'][i] in FORM_TYPES:
                    filing = {
                        'form': recent['form'][i],
                        'filingDate': recent['filingDate'][i],
                        'accessionNumber': recent['accessionNumber'][i],
                        'primaryDocument': recent['primaryDocument'][i],
                    }
                    filings.append(filing)
        
        logger.info(f"Successfully fetched {len(filings)} BMO SEC filings of interest")
        return filings
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SEC filings API: {e}")
        return []
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing SEC API response: {e}")
        return []

def construct_filing_url(accession_number, primary_document):
    """
    Construct the URL to download a filing based on its accession number.
    
    Args:
        accession_number: The accession number of the filing
        primary_document: The primary document of the filing
        
    Returns:
        URL to the filing document
    """
    # Format accession number by removing dashes
    acc_no = accession_number.replace('-', '')
    
    # Construct the URL to the filing on EDGAR
    base_url = "https://www.sec.gov/Archives/edgar/data"
    cik_no_leading_zeros = BMO_CIK.lstrip('0')
    
    url = f"{base_url}/{cik_no_leading_zeros}/{acc_no}/{primary_document}"
    return url

def download_filing(url, output_path):
    """
    Download a filing document and save it to disk.
    
    Args:
        url: URL to the filing document
        output_path: Path to save the document to
        
    Returns:
        The local path if successful, None otherwise
    """
    try:
        logger.info(f"Downloading filing from {url}")
        # Use different headers for www.sec.gov versus data.sec.gov
        download_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (Your Organization; your.email@example.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Host": "www.sec.gov"
        }
        
        response = requests.get(url, headers=download_headers)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Downloaded filing to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading filing: {e}")
        return None

def extract_mda_section(html_path):
    """
    Extract the Management's Discussion and Analysis section from an HTML filing.
    
    Args:
        html_path: Path to the HTML filing
        
    Returns:
        Text content of the MD&A section, or None if not found
    """
    try:
        with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Different ways MD&A might be indicated in the document
        mda_indicators = [
            r"management'?s\s+discussion\s+and\s+analysis",
            r"management\s+discussion\s+and\s+analysis",
            r"md&a",
            r"item\s+[27]"  # Item 7 is typically MD&A in 10-K, Item 2 in 10-Q
        ]
        
        # Common section headers for MD&A sections
        section_tags = ['h1', 'h2', 'h3', 'h4', 'div', 'p', 'span']
        
        # Try to find the MD&A section
        mda_section = None
        for tag in section_tags:
            for element in soup.find_all(tag):
                text = element.get_text().lower()
                if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_indicators):
                    mda_section = element
                    break
            if mda_section:
                break
                
        if not mda_section:
            logger.warning(f"Could not find MD&A section in {html_path}")
            return None
            
        # Extract the MD&A section text
        mda_text = mda_section.get_text() + "\n\n"
        
        # Try to find the end of the MD&A section
        mda_end_indicators = [
            r"financial\s+statements",
            r"item\s+8",
            r"item\s+4",
            r"quantitative\s+and\s+qualitative\s+disclosures",
        ]
        
        # Get all content until the next major section
        current = mda_section.next_sibling
        
        while current:
            if hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3']:
                if hasattr(current, 'get_text'):
                    text = current.get_text().lower()
                    if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_end_indicators):
                        break
                    
            if hasattr(current, 'get_text') and current.get_text().strip():
                mda_text += current.get_text().strip() + "\n\n"
                
            current = current.next_sibling
            
        logger.info(f"Extracted MD&A section from {html_path} ({len(mda_text)} characters)")
        return mda_text
        
    except Exception as e:
        logger.error(f"Error extracting MD&A section: {e}")
        return None

def main():
    """Main function to extract BMO filings from SEC API."""
    logger.info("Starting BMO SEC filing extraction using SEC API")
    
    # Fetch the SEC filings data for BMO
    filings = fetch_sec_filings()
    if not filings:
        logger.error("No filings found through the SEC API, exiting")
        return
    
    # Process each BMO filing
    processed_filings = []
    
    for filing in filings:
        form_type = filing.get('form')
        filing_date = filing.get('filingDate')
        accession_number = filing.get('accessionNumber')
        primary_document = filing.get('primaryDocument')
        
        if not all([form_type, filing_date, accession_number, primary_document]):
            logger.warning(f"Missing required info for filing {filing}, skipping")
            continue
            
        # Construct the URL to the filing document
        doc_url = construct_filing_url(accession_number, primary_document)
        
        # Create a filename for the HTML file
        html_filename = f"BMO_{form_type}_{filing_date.replace('-', '')}.html"
        html_path = os.path.join(OUTPUT_DIR, html_filename)
        
        # Download the HTML filing
        html_path = download_filing(doc_url, html_path)
        if not html_path:
            logger.warning(f"Failed to download HTML filing for {doc_url}, skipping")
            continue
            
        # Extract the MD&A section
        mda_content = extract_mda_section(html_path)
        mda_path = None
        
        if mda_content:
            # Create a filename for the MD&A text file
            mda_filename = f"BMO_{form_type}_{filing_date.replace('-', '')}_MDA.txt"
            mda_path = os.path.join(OUTPUT_DIR, mda_filename)
            
            # Save the MD&A content to a text file
            try:
                with open(mda_path, 'w', encoding='utf-8') as f:
                    f.write(mda_content)
                    
                logger.info(f"Saved MD&A section to {mda_path}")
                
            except Exception as e:
                logger.error(f"Error saving MD&A content: {e}")
                mda_path = None
        
        # Add filing information to the list
        filing_info = {
            "company": "Bank of Montreal",
            "cik": BMO_CIK,
            "form_type": form_type,
            "filing_date": filing_date,
            "accession_number": accession_number,
            "html_path": html_path,
            "mda_path": mda_path
        }
        processed_filings.append(filing_info)
        
        # Add a delay to avoid overloading the SEC server
        time.sleep(2)
    
    # Save the filing information to a JSON file
    json_path = os.path.join(OUTPUT_DIR, "bmo_filings.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(processed_filings, f, indent=2)
            
        logger.info(f"Saved filing information to {json_path}")
        
    except Exception as e:
        logger.error(f"Error saving filing information: {e}")
    
    # Print a summary
    annual_reports = sum(1 for filing in processed_filings if filing['form_type'] == '10-K')
    quarterly_reports = sum(1 for filing in processed_filings if filing['form_type'] == '10-Q')
    mda_sections = sum(1 for filing in processed_filings if filing.get('mda_path'))
    
    logger.info("=" * 50)
    logger.info(f"BMO SEC Filing Extraction Summary:")
    logger.info(f"  - Total filings processed: {len(processed_filings)}")
    logger.info(f"  - Annual reports (10-K): {annual_reports}")
    logger.info(f"  - Quarterly reports (10-Q): {quarterly_reports}")
    logger.info(f"  - MD&A sections extracted: {mda_sections}")
    logger.info("=" * 50)
    
    logger.info("BMO SEC filing extraction completed")

if __name__ == "__main__":
    main() 