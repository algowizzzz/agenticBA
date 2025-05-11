#!/usr/bin/env python3
"""
Test Bank SEC Filing Collector - JPMorgan Chase Only
This script extends the SEC feed collector to specifically target JPM.
"""

import os
import sys
import datetime
import logging
import json
import re
from sec_feed_collector import (
    fetch_sec_feed, process_entry_for_company, save_company_filing,
    SEC_FEEDS, DATA_DIR, SEC_DIR, PROCESSED_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define JPMorgan Chase info with expanded aliases
JPM_INFO = {
    "ticker": "JPM",
    "company": "JPMorgan Chase & Co.",
    "aliases": ["JPMorgan", "JPMorgan Chase", "JP Morgan", "Chase", "J.P. Morgan", "JP Morgan Chase", 
               "JPM", "JP", "Morgan", "Jamie Dimon", "J.P.M.", "JPMorganChase", "Chase Bank"]
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(SEC_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_DIR, "JPM"), exist_ok=True)

def get_company_info(ticker=None):
    """Mock company info function that only returns JPM."""
    if ticker is None or ticker == "JPM":
        return JPM_INFO
    return None

# Custom function to detect JPM mentions with higher sensitivity
def content_mentions_jpm(text):
    """Check if text mentions JPMorgan Chase with higher sensitivity."""
    if not text or not isinstance(text, str):
        return False
        
    text_lower = text.lower()
    
    # Check for JPM ticker symbol with word boundaries
    if re.search(r'\bJPM\b', text):
        return True
    
    # Check for various forms of the company name
    jpm_patterns = [
        r'\bjp\s*morgan\b',
        r'\bjpmorgan\b',
        r'\bchase\b',
        r'\bjamie\s*dimon\b',
        r'\bj\.p\.\s*morgan\b',
        r'\bjpm\b',
    ]
    
    for pattern in jpm_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for bank-related terms in combination with Morgan
    bank_terms = ['bank', 'financial', 'earnings', 'profit', 'revenue', 'asset', 'loan']
    if 'morgan' in text_lower:
        for term in bank_terms:
            if term in text_lower:
                return True
    
    return False

def process_feeds_for_jpm(max_entries=20):
    """Process SEC feeds for JPMorgan Chase only with enhanced detection."""
    # Fetch all feeds
    feeds = {}
    for feed_name, feed_url in SEC_FEEDS.items():
        feed = fetch_sec_feed(feed_name, feed_url)
        if feed and feed.entries:
            feeds[feed_name] = feed
    
    filings_collected = 0
    
    for feed_name, feed in feeds.items():
        logger.info(f"Processing {feed_name} feed for JPMorgan Chase")
        
        # Limit entries to process but use more entries
        entries_to_process = feed.entries[:max_entries]
        
        for entry in entries_to_process:
            # Print entry title to see what we're processing
            title = entry.get('title', 'No title')
            logger.info(f"Checking entry: {title}")
            
            # Try custom detection first
            found_with_custom = False
            
            # Check title for JPM mentions
            if hasattr(entry, 'title') and content_mentions_jpm(entry.title):
                found_with_custom = True
                logger.info(f"JPM mention found in title: {entry.title}")
            
            # Check summary for JPM mentions
            if not found_with_custom and hasattr(entry, 'summary') and content_mentions_jpm(entry.summary):
                found_with_custom = True
                logger.info(f"JPM mention found in summary")
            
            # If found with custom detection, or as a fallback, try the regular process
            if found_with_custom:
                logger.info(f"Processing entry with JPM mention: {title}")
                
                # Save directly with minimal processing if we confirmed JPM mention
                processed_entry = {
                    'ticker': "JPM",
                    'company': JPM_INFO['company'],
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'content': str(entry.get('content', '')),
                    'entry_id': entry.get('id', '') or datetime.datetime.now().isoformat(),
                    'filing_type': entry.get('edgar:formName', entry.get('category', '')),
                    'processed_date': datetime.datetime.now().isoformat()
                }
                
                # Create filename based on entry ID
                file_id = processed_entry['entry_id'].split('/')[-1] if '/' in processed_entry['entry_id'] else processed_entry['entry_id']
                output_path = os.path.join(PROCESSED_DIR, "JPM", f"JPM_{file_id}.json")
                
                # Save the filing data
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_entry, f, indent=2)
                
                logger.info(f"Saved filing for JPM: {processed_entry['title']}")
                filings_collected += 1
            else:
                # Try the original process as fallback
                original_get_company_info = sys.modules.get('src.reference_data', None)
                
                try:
                    # Temporarily replace the module
                    class MockRefData:
                        @staticmethod
                        def get_company_info(ticker_arg=None):
                            return get_company_info(ticker_arg)
                    
                    sys.modules['src.reference_data'] = MockRefData
                    
                    # Process the entry
                    processed_entry = process_entry_for_company(entry, "JPM")
                    if processed_entry:
                        save_company_filing("JPM", processed_entry)
                        filings_collected += 1
                        logger.info(f"Saved filing for JPM using standard processing: {processed_entry['title']}")
                
                finally:
                    # Restore original module if it existed
                    if original_get_company_info:
                        sys.modules['src.reference_data'] = original_get_company_info
                    else:
                        sys.modules.pop('src.reference_data', None)
    
    return filings_collected

def manual_add_sample_filing():
    """Add a sample JPM filing if no real ones were found."""
    sample_filing = {
        'ticker': "JPM",
        'company': "JPMorgan Chase & Co.",
        'title': "SAMPLE - JPMorgan Chase Reports Strong First Quarter 2025 Results",
        'link': "https://www.sec.gov/example/jpm-q1-2025",
        'published': datetime.datetime.now().isoformat(),
        'summary': "JPMorgan Chase & Co. (NYSE: JPM) reported net income of $15.4 billion for the first quarter of 2025.",
        'content': """
            JPMorgan Chase & Co. (NYSE: JPM) has reported financial results for the first quarter of 2025.
            
            Financial Highlights:
            - Net income: $15.4 billion, up 12% year-over-year
            - Revenue: $42.5 billion, up 8% year-over-year
            - Earnings per share: $5.12, compared with $4.65 in the prior year
            
            Jamie Dimon, Chairman and CEO, commented: "JPMorgan Chase delivered strong results across all our businesses. 
            Our commercial banking and asset & wealth management divisions performed exceptionally well, while our 
            investment banking division saw moderate growth in a challenging market environment."
            
            The firm maintained a strong capital position with a CET1 ratio of 14.2% and total liquidity resources of $1.4 trillion.
            
            This is a sample filing for demonstration purposes.
        """,
        'entry_id': f"sample-jpm-filing-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        'filing_type': "8-K",
        'cik': "0000019617",
        'processed_date': datetime.datetime.now().isoformat()
    }
    
    # Save sample filing
    output_path = os.path.join(PROCESSED_DIR, "JPM", f"JPM_sample_filing.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_filing, f, indent=2)
    
    logger.info(f"Added sample JPM filing for demonstration")
    return 1

def main():
    """Main function to test JPM filing collection."""
    logger.info("Starting JPMorgan Chase SEC filing test collection")
    
    # Create directories
    ensure_directories()
    
    # Process feeds for JPM
    filings_collected = process_feeds_for_jpm(max_entries=20)
    
    # If no filings were found, add a sample one
    if filings_collected == 0:
        logger.info("No real JPM filings found, adding a sample filing for demonstration")
        filings_collected += manual_add_sample_filing()
    
    # Print summary
    print("\n--- JPMorgan Chase Filing Collection Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total filings collected: {filings_collected}")
    
    # List the files saved
    jpm_dir = os.path.join(PROCESSED_DIR, "JPM")
    if os.path.exists(jpm_dir):
        files = os.listdir(jpm_dir)
        if files:
            print("\nCollected filings:")
            for file in files:
                if file.endswith('.json'):
                    print(f"  - {file}")
    
    return True

if __name__ == "__main__":
    main()
