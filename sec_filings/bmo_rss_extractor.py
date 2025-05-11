#!/usr/bin/env python3
"""
BMO SEC Filing RSS Extractor

This script extracts SEC filings for Bank of Montreal (BMO) using public RSS feeds
provided by the SEC. It downloads the filings and extracts the Management's Discussion
and Analysis (MD&A) section from each report.

Usage:
    python bmo_rss_extractor.py
"""

import os
import re
import time
import json
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("bmo_rss_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# SEC RSS feed URLs
SEC_RSS_FEED_URL = "https://www.sec.gov/Archives/edgar/xbrlrss.all.xml"  # All recent EDGAR submissions
# Alternative feeds:
# SEC_RSS_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"

# BMO's CIK (Central Index Key)
BMO_CIK = "0000927971"  # Bank of Montreal
FORM_TYPES = ["10-K", "10-Q"]  # Annual and quarterly reports

# Request headers to avoid 403 errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "From": "your-email@domain.com"  # Add a contact email as recommended by SEC
}

def fetch_sec_rss_feed():
    """
    Fetch the SEC EDGAR RSS feed.
    
    Returns:
        List of feed entries
    """
    logger.info(f"Fetching SEC EDGAR RSS feed from {SEC_RSS_FEED_URL}")
    
    try:
        response = requests.get(SEC_RSS_FEED_URL, headers=HEADERS)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            logger.warning("No entries found in the RSS feed")
            return []
            
        logger.info(f"Successfully fetched {len(feed.entries)} SEC filings from RSS feed")
        return feed.entries
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SEC EDGAR RSS feed: {e}")
        return []

def filter_bmo_filings(entries):
    """
    Filter entries to include only BMO filings.
    
    Args:
        entries: List of RSS feed entries
        
    Returns:
        Filtered list of entries for BMO
    """
    bmo_entries = []
    
    for entry in entries:
        # Check for BMO's CIK in the entry
        if BMO_CIK in entry.link:
            # Check if the form type is one we're interested in
            form_type_match = False
            for form_type in FORM_TYPES:
                if form_type in entry.title:
                    form_type_match = True
                    break
                    
            if form_type_match:
                bmo_entries.append(entry)
    
    logger.info(f"Found {len(bmo_entries)} BMO filings in the RSS feed")
    return bmo_entries

def extract_filing_details(entry):
    """
    Extract important details from a filing entry.
    
    Args:
        entry: RSS feed entry
        
    Returns:
        Dictionary with filing details
    """
    filing_details = {
        "company": "Bank of Montreal",
        "cik": BMO_CIK,
        "title": entry.title,
        "link": entry.link,
        "form_type": None,
        "filing_date": None,
        "description": entry.summary if hasattr(entry, 'summary') else ""
    }
    
    # Extract form type from the title
    for form_type in FORM_TYPES:
        if form_type in entry.title:
            filing_details["form_type"] = form_type
            break
    
    # Extract filing date if available
    if hasattr(entry, 'published'):
        try:
            filing_date = datetime.strptime(entry.published, "%Y-%m-%dT%H:%M:%S%z")
            filing_details["filing_date"] = filing_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass
    
    return filing_details

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
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Downloaded filing to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading filing: {e}")
        return None

def find_document_url(entry_url):
    """
    Find the actual document URL from the filing entry page.
    
    Args:
        entry_url: URL to the filing entry page
        
    Returns:
        URL to the actual document
    """
    try:
        logger.info(f"Finding document URL from {entry_url}")
        response = requests.get(entry_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the table of contents
        table = soup.find('table', {'summary': 'Document Format Files'})
        if not table:
            logger.warning(f"Could not find document table in {entry_url}")
            return None
            
        # Look for the main document in the table (usually has the form type in the description)
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                doc_type = cells[0].text.strip()
                if doc_type in FORM_TYPES:
                    # Get the link to the document
                    link = cells[2].find('a')
                    if link and link.get('href'):
                        doc_url = urljoin("https://www.sec.gov", link['href'])
                        logger.info(f"Found document URL: {doc_url}")
                        return doc_url
        
        logger.warning(f"Could not find document URL in {entry_url}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error finding document URL: {e}")
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
            if current.name in ['h1', 'h2', 'h3']:
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
    """Main function to extract BMO filings from SEC EDGAR RSS feed."""
    logger.info("Starting BMO SEC filing extraction using RSS feed")
    
    # Fetch the SEC EDGAR RSS feed
    entries = fetch_sec_rss_feed()
    if not entries:
        logger.error("No entries found in the SEC EDGAR RSS feed, exiting")
        return
        
    # Filter to include only BMO filings
    bmo_entries = filter_bmo_filings(entries)
    if not bmo_entries:
        logger.warning("No BMO filings found in the SEC EDGAR RSS feed, exiting")
        return
        
    # Process each BMO filing
    filings = []
    
    for entry in bmo_entries:
        # Extract filing details
        filing_details = extract_filing_details(entry)
        form_type = filing_details["form_type"]
        filing_date = filing_details["filing_date"]
        
        if not form_type or not filing_date:
            logger.warning(f"Missing form type or filing date for {entry.link}, skipping")
            continue
            
        # Find the document URL
        doc_url = find_document_url(entry.link)
        if not doc_url:
            logger.warning(f"Could not find document URL for {entry.link}, skipping")
            continue
            
        # Create a filename for the HTML file
        html_filename = f"BMO_{form_type}_{filing_date.replace('-', '')}.html"
        html_path = os.path.join(OUTPUT_DIR, html_filename)
        
        # Download the HTML filing
        html_path = download_filing(doc_url, html_path)
        if not html_path:
            logger.warning(f"Failed to download HTML filing for {entry.link}, skipping")
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
        filing_details["html_path"] = html_path
        filing_details["mda_path"] = mda_path
        filings.append(filing_details)
        
        # Add a delay to avoid overloading the SEC server
        time.sleep(2)
    
    # Save the filing information to a JSON file
    json_path = os.path.join(OUTPUT_DIR, "bmo_filings.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(filings, f, indent=2)
            
        logger.info(f"Saved filing information to {json_path}")
        
    except Exception as e:
        logger.error(f"Error saving filing information: {e}")
    
    # Print a summary
    annual_reports = sum(1 for filing in filings if filing['form_type'] == '10-K')
    quarterly_reports = sum(1 for filing in filings if filing['form_type'] == '10-Q')
    mda_sections = sum(1 for filing in filings if filing.get('mda_path'))
    
    logger.info("=" * 50)
    logger.info(f"BMO SEC Filing Extraction Summary:")
    logger.info(f"  - Total filings processed: {len(filings)}")
    logger.info(f"  - Annual reports (10-K): {annual_reports}")
    logger.info(f"  - Quarterly reports (10-Q): {quarterly_reports}")
    logger.info(f"  - MD&A sections extracted: {mda_sections}")
    logger.info("=" * 50)
    
    logger.info("BMO SEC filing extraction completed")

if __name__ == "__main__":
    main() 