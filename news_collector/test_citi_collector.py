#!/usr/bin/env python3
"""
Citigroup SEC Filing Collector
This script targets specifically Citigroup filings from SEC.gov RSS feeds.
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

# Define Citigroup info with expanded aliases
CITI_INFO = {
    "ticker": "C",
    "company": "Citigroup Inc.",
    "aliases": [
        "Citigroup", "Citi", "Citibank", "Citicorp", "CitiFinancial", 
        "Citigroup Inc", "Citigroup Inc.", "Citi Group", "Citi Bank",
        "Citigroup Global Markets", "Citigroup Capital Markets",
        "Jane Fraser", # CEO
        "C.", "C "  # Ticker variations
    ]
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(SEC_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_DIR, "C"), exist_ok=True)

def get_company_info(ticker=None):
    """Mock company info function that only returns Citigroup."""
    if ticker is None or ticker == "C":
        return CITI_INFO
    return None

# Custom function to detect Citigroup mentions with higher sensitivity
def content_mentions_citi(text):
    """Check if text mentions Citigroup with higher sensitivity."""
    if not text or not isinstance(text, str):
        return False
        
    text_lower = text.lower()
    
    # Check for ticker symbol with word boundaries
    if re.search(r'\bC\b', text):
        # Verify it's not just a single C in another context
        surrounding_context = 30  # characters
        matches = list(re.finditer(r'\bC\b', text))
        for match in matches:
            start = max(0, match.start() - surrounding_context)
            end = min(len(text), match.end() + surrounding_context)
            context = text[start:end].lower()
            # Check if ticker-related words are nearby
            ticker_context = ["ticker", "symbol", "stock", "nyse", "bank", "financial"]
            if any(word in context for word in ticker_context):
                return True
    
    # Check for various forms of the company name
    citi_patterns = [
        r'\bciti(?:group|bank|corp|financial)\b',
        r'\bciti\b',
        r'\bcitigroup\b',
        r'\bcitibank\b',
        r'\bjane\s*fraser\b',
    ]
    
    for pattern in citi_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for financial context with Citi mentions
    bank_terms = ['bank', 'financial', 'earnings', 'profit', 'revenue', 'asset', 'loan', 'credit']
    if any(term in text_lower for term in bank_terms) and ('citi' in text_lower):
        return True
    
    return False

def process_feeds_for_citi(max_entries=40):
    """Process SEC feeds for Citigroup only with enhanced detection."""
    # Fetch all feeds
    feeds = {}
    for feed_name, feed_url in SEC_FEEDS.items():
        feed = fetch_sec_feed(feed_name, feed_url)
        if feed and feed.entries:
            feeds[feed_name] = feed
    
    filings_collected = 0
    
    for feed_name, feed in feeds.items():
        logger.info(f"Processing {feed_name} feed for Citigroup")
        
        # Limit entries to process but use more entries
        entries_to_process = feed.entries[:max_entries]
        
        for entry in entries_to_process:
            # Print entry title to see what we're processing
            title = entry.get('title', 'No title')
            logger.info(f"Checking entry: {title}")
            
            # Try custom detection first
            found_with_custom = False
            
            # Check title for Citi mentions
            if hasattr(entry, 'title') and content_mentions_citi(entry.title):
                found_with_custom = True
                logger.info(f"Citigroup mention found in title: {entry.title}")
            
            # Check summary for Citi mentions
            if not found_with_custom and hasattr(entry, 'summary') and content_mentions_citi(entry.summary):
                found_with_custom = True
                logger.info(f"Citigroup mention found in summary")
            
            # If found with custom detection, save directly
            if found_with_custom:
                logger.info(f"Processing entry with Citigroup mention: {title}")
                
                # Save directly with minimal processing if we confirmed Citigroup mention
                processed_entry = {
                    'ticker': "C",
                    'company': CITI_INFO['company'],
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
                output_path = os.path.join(PROCESSED_DIR, "C", f"C_{file_id}.json")
                
                # Save the filing data
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_entry, f, indent=2)
                
                logger.info(f"Saved filing for Citigroup: {processed_entry['title']}")
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
                    processed_entry = process_entry_for_company(entry, "C")
                    if processed_entry:
                        save_company_filing("C", processed_entry)
                        filings_collected += 1
                        logger.info(f"Saved filing for Citigroup using standard processing: {processed_entry['title']}")
                
                finally:
                    # Restore original module if it existed
                    if original_get_company_info:
                        sys.modules['src.reference_data'] = original_get_company_info
                    else:
                        sys.modules.pop('src.reference_data', None)
    
    return filings_collected

def manual_add_placeholder():
    """Add a placeholder filing if no real ones were found."""
    # This will only be used if no real filings are found
    placeholder_filing = {
        'ticker': "C",
        'company': "Citigroup Inc.",
        'title': "NOTE: No Citigroup filings found in current SEC RSS feeds",
        'link': "https://www.sec.gov/",
        'published': datetime.datetime.now().isoformat(),
        'summary': "This is a placeholder entry. No actual Citigroup filings were found in the current SEC RSS feeds.",
        'content': """
            This is a placeholder filing created because no actual Citigroup (C) filings were found
            in the currently available SEC RSS feeds.
            
            To find actual Citigroup filings, you could:
            1. Try again later when new SEC feeds are available
            2. Use the SEC EDGAR database directly: https://www.sec.gov/edgar/searchedgar/companysearch
            3. Increase the search depth by modifying the 'max_entries' parameter
            
            This placeholder is for demonstration purposes only.
        """,
        'entry_id': f"placeholder-citi-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        'filing_type': "NOTE",
        'processed_date': datetime.datetime.now().isoformat()
    }
    
    # Save placeholder filing
    output_path = os.path.join(PROCESSED_DIR, "C", f"C_placeholder.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(placeholder_filing, f, indent=2)
    
    logger.info("Added placeholder for Citigroup as no actual filings were found")
    return 1

def search_for_financial_terms(entry):
    """
    Check if the entry contains financial terms that might be relevant
    even if they don't explicitly mention Citigroup.
    """
    if not entry:
        return False
    
    financial_terms = [
        'banking sector', 'financial services', 'major banks', 
        'banking industry', 'investment banking', 'bank stocks',
        'financial institutions', 'big banks', 'banking news'
    ]
    
    # Check title
    if hasattr(entry, 'title') and isinstance(entry.title, str):
        for term in financial_terms:
            if term.lower() in entry.title.lower():
                return True
    
    # Check summary
    if hasattr(entry, 'summary') and isinstance(entry.summary, str):
        for term in financial_terms:
            if term.lower() in entry.summary.lower():
                return True
                
    return False

def main():
    """Main function to collect Citigroup SEC filings."""
    logger.info("Starting Citigroup SEC filing collection")
    
    # Create directories
    ensure_directories()
    
    # Process feeds for Citigroup
    filings_collected = process_feeds_for_citi(max_entries=40)
    
    # If no filings were found, add a placeholder
    if filings_collected == 0:
        logger.info("No Citigroup filings found, adding placeholder")
        filings_collected += manual_add_placeholder()
    
    # Print summary
    print("\n--- Citigroup Filing Collection Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total filings collected: {filings_collected}")
    
    # List the files saved
    citi_dir = os.path.join(PROCESSED_DIR, "C")
    if os.path.exists(citi_dir):
        files = os.listdir(citi_dir)
        if files:
            print("\nCollected filings:")
            for file in files:
                if file.endswith('.json'):
                    print(f"  - {file}")
    
    return True

if __name__ == "__main__":
    main() 