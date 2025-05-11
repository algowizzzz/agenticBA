#!/usr/bin/env python3
"""
BMO SEC Filing Extractor

This script extracts SEC filings (annual and quarterly reports) for Bank of Montreal (BMO)
from the SEC EDGAR RSS feed. It downloads the filings from the past year and extracts
the Management's Discussion and Analysis (MD&A) section from each report.

Usage:
    python bmo_sec_extractor.py
"""

import os
import re
import sys
import time
import json
import logging
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("bmo_sec_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
SEC_EDGAR_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_EDGAR_BASE_URL = "https://www.sec.gov"
# BMO's CIK (Central Index Key) - used to identify the company in SEC filings
BMO_CIK = "0000927971"  # Bank of Montreal CIK
# Form types we're interested in
FORM_TYPES = ["10-K", "10-Q"]  # Annual and quarterly reports
# Time period: 1 year back from today
ONE_YEAR_AGO = datetime.datetime.now() - datetime.timedelta(days=365)

# Request headers to avoid 403 errors (SEC requires a specific user-agent)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Host": "www.sec.gov",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Mock mode disabled - using real SEC API
MOCK_MODE = False

# Add mock data
MOCK_FILINGS = [
    {
        "title": "10-K - BANK OF MONTREAL /CAN/ (0000927971) (Filer)",
        "link": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000005/0000927971-23-000005-index.htm",
        "updated": "2023-02-28T16:30:01Z",
        "summary": "Form 10-K - Annual Report",
    },
    {
        "title": "10-Q - BANK OF MONTREAL /CAN/ (0000927971) (Filer)",
        "link": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000014/0000927971-23-000014-index.htm",
        "updated": "2023-05-24T20:31:12Z",
        "summary": "Form 10-Q - Quarterly Report",
    },
    {
        "title": "10-Q - BANK OF MONTREAL /CAN/ (0000927971) (Filer)",
        "link": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000018/0000927971-23-000018-index.htm",
        "updated": "2023-08-29T20:06:50Z",
        "summary": "Form 10-Q - Quarterly Report",
    },
    {
        "title": "10-Q - BANK OF MONTREAL /CAN/ (0000927971) (Filer)",
        "link": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000022/0000927971-23-000022-index.htm",
        "updated": "2023-12-01T21:16:54Z",
        "summary": "Form 10-Q - Quarterly Report",
    },
    {
        "title": "10-K - BANK OF MONTREAL /CAN/ (0000927971) (Filer)",
        "link": "https://www.sec.gov/Archives/edgar/data/927971/000092797124000006/0000927971-24-000006-index.htm",
        "updated": "2024-02-27T21:39:10Z", 
        "summary": "Form 10-K - Annual Report",
    }
]

def get_sec_rss_feed(cik):
    """
    Fetch the SEC EDGAR RSS feed for a given CIK.
    
    Args:
        cik: The Central Index Key for the company
        
    Returns:
        A list of feed entries
    """
    logger.info(f"Fetching SEC EDGAR RSS feed for CIK: {cik}")
    
    # Use mock data if in mock mode
    if MOCK_MODE:
        logger.info("Using mock data instead of real SEC API")
        
        # Convert mock data to feedparser-like entries
        class MockEntry:
            pass
            
        entries = []
        for filing in MOCK_FILINGS:
            entry = MockEntry()
            entry.title = filing["title"]
            entry.link = filing["link"]
            entry.updated = filing["updated"]
            entry.summary = filing["summary"]
            entries.append(entry)
            
        return entries
    
    # Real SEC API code continues below
    params = {
        "action": "getcompany",
        "CIK": cik,
        "type": ",".join(FORM_TYPES),
        "output": "atom",
        "count": 100  # Get more than we need to ensure we have a full year
    }
    
    try:
        response = requests.get(SEC_EDGAR_RSS_URL, params=params, headers=HEADERS)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        if not feed.entries:
            logger.warning(f"No entries found in the RSS feed for CIK: {cik}")
            return []
            
        logger.info(f"Successfully fetched {len(feed.entries)} SEC filings")
        return feed.entries
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SEC EDGAR RSS feed: {e}")
        return []

def get_filing_documents_url(filing_url):
    """
    Extract the URL for the filing documents page.
    
    Args:
        filing_url: URL to the filing summary page
        
    Returns:
        URL to the filing documents page
    """
    # Use mock data if in mock mode
    if MOCK_MODE:
        # In mock mode, just return the original URL as we won't actually fetch documents
        return filing_url
        
    # Real code continues below
    try:
        response = requests.get(filing_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the Documents button/link which leads to the filing documents
        for link in soup.find_all('a'):
            if link.text and 'Documents' in link.text:
                return urljoin(SEC_EDGAR_BASE_URL, link['href'])
        
        logger.warning(f"Could not find documents link for filing: {filing_url}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching filing page: {e}")
        return None

def get_filing_document_urls(documents_url):
    """
    Extract URLs for the actual filing documents (HTML, XML, etc.).
    
    Args:
        documents_url: URL to the filing documents page
        
    Returns:
        Dictionary mapping document types to their URLs
    """
    # Use mock data if in mock mode
    if MOCK_MODE:
        # Generate a mock document URL that looks reasonable
        mock_doc_type = "10-K" if "10-K" in documents_url else "10-Q"
        return {
            mock_doc_type: {
                'description': "Complete submission text file",
                'url': documents_url.replace("-index.htm", ".txt")
            }
        }
        
    # Real code continues below
    try:
        response = requests.get(documents_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        document_urls = {}
        
        # Find the table with document information
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Document type (e.g., 10-K, EX-101.INS)
                    doc_type = cells[0].text.strip()
                    # Description is often "Complete submission text file" for the main document
                    description = cells[1].text.strip()
                    # Document URL
                    if cells[2].find('a'):
                        doc_url = urljoin(SEC_EDGAR_BASE_URL, cells[2].find('a')['href'])
                        document_urls[doc_type] = {
                            'description': description,
                            'url': doc_url
                        }
        
        logger.info(f"Found {len(document_urls)} document URLs")
        return document_urls
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching document URLs: {e}")
        return {}

def download_filing(url, output_path):
    """
    Download a filing document and save it to disk.
    
    Args:
        url: URL to the filing document
        output_path: Path to save the document to
        
    Returns:
        The local path if successful, None otherwise
    """
    # Use mock data if in mock mode
    if MOCK_MODE:
        logger.info(f"Mock mode: Creating dummy content for {output_path}")
        
        # Generate some dummy content for the filing based on the filename
        content = f"""
        <html>
        <head><title>Mock SEC Filing</title></head>
        <body>
            <h1>Bank of Montreal</h1>
            <h2>Mock SEC Filing</h2>
            <p>This is a mock filing created for testing purposes.</p>
            
            <h2>Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations</h2>
            <p>This section contains important information on BMO's business strategies, financial performance, and outlook.</p>
            <p>BMO reported strong financial results for the period with growth in key areas and continued momentum across all business segments.</p>
            <p>Revenue increased primarily due to higher net interest income, driven by strong loan growth and improved margins.</p>
            <p>The Bank maintained a strong capital position with a Common Equity Tier 1 ratio of 12.5%.</p>
            
            <h2>Item 3. Quantitative and Qualitative Disclosures About Market Risk</h2>
            <p>This marks the end of the MD&A section.</p>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Created mock filing at {output_path}")
        return output_path
        
    # Real code continues below
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Downloaded filing to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading filing: {e}")
        return None 