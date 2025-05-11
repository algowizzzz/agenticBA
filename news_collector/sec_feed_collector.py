#!/usr/bin/env python3
"""
SEC Feed Collector for Company Filings and Press Releases.
This script fetches RSS feeds from SEC.gov, filters for target companies,
and saves the relevant filings to company-specific directories.
"""

import os
import sys
import datetime
import logging
import json
import feedparser
import requests
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Add src directory to path to import reference_data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.reference_data import get_company_info

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SEC_DIR = os.path.join(DATA_DIR, "raw", "sec")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "sec")

# SEC RSS Feed URLs
SEC_FEEDS = {
    "latest_filings": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom",
    "press_releases": "https://www.sec.gov/news/pressreleases.rss",
    "company_announcements": "https://www.sec.gov/cgi-bin/browse-edgar?type=8-K&action=getcurrent&output=atom",
    "quarterly_reports": "https://www.sec.gov/cgi-bin/browse-edgar?type=10-Q&action=getcurrent&output=atom",
    "annual_reports": "https://www.sec.gov/cgi-bin/browse-edgar?type=10-K&action=getcurrent&output=atom",
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(SEC_DIR, exist_ok=True)
    
    # Create company-specific directories
    for ticker in get_company_info():
        os.makedirs(os.path.join(PROCESSED_DIR, ticker), exist_ok=True)

def fetch_sec_feed(feed_name, feed_url):
    """
    Fetch and parse an SEC RSS feed.
    
    Args:
        feed_name: Name of the feed
        feed_url: URL of the RSS feed
        
    Returns:
        Parsed feed data
    """
    logger.info(f"Fetching SEC feed: {feed_name}")
    
    try:
        # Set a proper user agent to avoid being blocked
        headers = {
            'User-Agent': 'Financial Data Research Project (edu.research.project@example.edu)'
        }
        
        # Parse the feed
        feed = feedparser.parse(feed_url, request_headers=headers)
        
        if feed.bozo:
            logger.warning(f"Feed parsing error: {feed.bozo_exception}")
        
        entries_count = len(feed.entries)
        logger.info(f"Retrieved {entries_count} entries from {feed_name}")
        
        # Save raw feed for reference
        raw_file = os.path.join(SEC_DIR, f"{feed_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            # Convert feed entries to a serializable format
            feed_data = {
                'feed_info': feed.feed,
                'entries': [dict(entry) for entry in feed.entries]
            }
            json.dump(feed_data, f, default=str, indent=2)
        
        return feed
        
    except Exception as e:
        logger.error(f"Error fetching SEC feed {feed_name}: {e}")
        return None

def extract_cik_from_entry(entry):
    """
    Extract the CIK (Central Index Key) from an entry if available.
    
    Args:
        entry: Feed entry
        
    Returns:
        CIK string or None
    """
    # Look for CIK in various places
    if 'edgar:cikNumber' in entry:
        return entry['edgar:cikNumber']
    
    # Check link URLs
    if 'link' in entry:
        match = re.search(r'CIK=(\d+)', entry.link)
        if match:
            return match.group(1)
    
    # Look in summary or content
    for field in ['summary', 'content', 'title']:
        if field in entry:
            content = entry[field]
            if isinstance(content, list) and len(content) > 0 and 'value' in content[0]:
                content = content[0]['value']
            
            if isinstance(content, str):
                match = re.search(r'CIK:?\s*(\d+)', content)
                if match:
                    return match.group(1)
    
    return None

def company_mentioned_in_text(text, company_info):
    """
    Check if a company is mentioned in the text.
    
    Args:
        text: Text to search in
        company_info: Company information dictionary
        
    Returns:
        True if company is mentioned, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
        
    text_lower = text.lower()
    
    # Check company name
    if company_info['company'].lower() in text_lower:
        return True
    
    # Check ticker
    ticker_pattern = r'\b' + re.escape(company_info['ticker']) + r'\b'
    if re.search(ticker_pattern, text):
        return True
    
    # Check aliases
    for alias in company_info['aliases']:
        if alias.lower() in text_lower:
            return True
    
    return False

def entry_mentions_company(entry, company_info):
    """
    Check if an entry mentions a specific company.
    
    Args:
        entry: Feed entry
        company_info: Company information dictionary
        
    Returns:
        True if company is mentioned, False otherwise
    """
    # Check title
    if 'title' in entry and company_mentioned_in_text(entry.title, company_info):
        return True
    
    # Check summary
    if 'summary' in entry and company_mentioned_in_text(entry.summary, company_info):
        return True
    
    # Check content
    if 'content' in entry and len(entry.content) > 0:
        if company_mentioned_in_text(entry.content[0].value, company_info):
            return True
    
    # TODO: Could add fetching the actual filing for more complete checking
    
    return False

def fetch_filing_content(entry):
    """
    Fetch the actual content of a filing from its URL.
    
    Args:
        entry: Feed entry
        
    Returns:
        Content text or None
    """
    if 'link' not in entry:
        return None
    
    try:
        # Set a proper user agent to avoid being blocked
        headers = {
            'User-Agent': 'Financial Data Research Project (edu.research.project@example.edu)'
        }
        
        # Get the filing page
        response = requests.get(entry.link, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # For EDGAR filings, the content is usually in specific elements
        # This is a simplification - actual parsing may need to be more sophisticated
        content = ""
        
        # Try to find the filing text
        filing_div = soup.find('div', {'id': 'filing-content'})
        if filing_div:
            content = filing_div.get_text(separator="\n")
        else:
            # Fallback to getting main text
            text_blocks = soup.find_all(['p', 'div', 'td'])
            content = "\n".join(block.get_text() for block in text_blocks if len(block.get_text()) > 50)
        
        return content
        
    except Exception as e:
        logger.warning(f"Error fetching filing content: {e}")
        return None

def process_entry_for_company(entry, ticker):
    """
    Process a feed entry for a specific company.
    
    Args:
        entry: Feed entry
        ticker: Company ticker symbol
        
    Returns:
        Processed entry data if relevant to company, None otherwise
    """
    company_info = get_company_info(ticker)
    if not company_info:
        return None
    
    # Check if entry mentions company
    if not entry_mentions_company(entry, company_info):
        return None
    
    # Get filing content if available
    content = fetch_filing_content(entry)
    
    # Create processed entry data
    processed_entry = {
        'ticker': ticker,
        'company': company_info['company'],
        'title': entry.get('title', ''),
        'link': entry.get('link', ''),
        'published': entry.get('published', ''),
        'summary': entry.get('summary', ''),
        'content': content,
        'entry_id': entry.get('id', ''),
        'filing_type': entry.get('edgar:formName', entry.get('category', '')),
        'cik': extract_cik_from_entry(entry),
        'processed_date': datetime.datetime.now().isoformat()
    }
    
    return processed_entry

def save_company_filing(ticker, filing_data):
    """
    Save a filing to the company's directory.
    
    Args:
        ticker: Company ticker symbol
        filing_data: Filing data dictionary
    """
    # Create a filename based on the entry ID or published date
    if 'entry_id' in filing_data and filing_data['entry_id']:
        # Extract unique identifier from entry ID
        id_match = re.search(r'([^/]+)$', filing_data['entry_id'])
        file_id = id_match.group(1) if id_match else 'unknown'
    else:
        # Use timestamp if no ID
        file_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Add filing type if available
    if 'filing_type' in filing_data and filing_data['filing_type']:
        filing_type = re.sub(r'[^a-zA-Z0-9]', '', filing_data['filing_type'])
        file_id = f"{filing_type}_{file_id}"
    
    # Create output path
    output_path = os.path.join(PROCESSED_DIR, ticker, f"{ticker}_{file_id}.json")
    
    # Save the filing data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filing_data, f, indent=2)
    
    logger.info(f"Saved filing for {ticker}: {filing_data['title']}")

def process_feeds_for_companies():
    """
    Process all SEC feeds for all target companies.
    """
    # Fetch all feeds
    feeds = {}
    for feed_name, feed_url in SEC_FEEDS.items():
        feed = fetch_sec_feed(feed_name, feed_url)
        if feed and feed.entries:
            feeds[feed_name] = feed
    
    # Process feeds for each company
    results = {ticker: 0 for ticker in get_company_info()}
    
    for feed_name, feed in feeds.items():
        logger.info(f"Processing {feed_name} feed for target companies")
        
        for entry in feed.entries:
            for ticker in get_company_info():
                processed_entry = process_entry_for_company(entry, ticker)
                if processed_entry:
                    save_company_filing(ticker, processed_entry)
                    results[ticker] += 1
    
    # Log results
    logger.info("Filing collection completed")
    for ticker, count in results.items():
        if count > 0:
            logger.info(f"  {ticker}: {count} filings collected")
    
    return results

def main():
    """Main function to run the SEC feed collector."""
    logger.info("Starting SEC Feed Collector...")
    
    # Create directories
    ensure_directories()
    
    # Process feeds
    results = process_feeds_for_companies()
    
    # Create summary file
    summary = {
        'collection_date': datetime.datetime.now().isoformat(),
        'companies': [
            {
                'ticker': ticker,
                'company': get_company_info(ticker)['company'],
                'filings_collected': count
            }
            for ticker, count in results.items()
        ]
    }
    
    summary_path = os.path.join(SEC_DIR, f"collection_summary_{datetime.datetime.now().strftime('%Y%m%d')}.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Collection summary saved to {summary_path}")
    
    # Print summary
    print("\n--- SEC Filing Collection Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total filings collected: {sum(results.values())}")
    print("\nFilings by company:")
    for ticker, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            company = get_company_info(ticker)['company']
            print(f"  {ticker} ({company}): {count} filings")
    
    return True

if __name__ == "__main__":
    main() 